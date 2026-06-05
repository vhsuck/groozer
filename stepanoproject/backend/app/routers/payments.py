

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.order import Order, OrderStatus
from app.models.payment import PaymentStatus
from app.models.user import User, UserRole
from app.services.logistics import ensure_payment_for_order, get_payment

router = APIRouter()


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    amount: Decimal
    provider: str
    reference: str
    status: str
    requested_at: datetime
    paid_at: datetime | None = None


def _serialize(payment) -> PaymentResponse:
    return PaymentResponse(
        id=payment.id,
        order_id=payment.order_id,
        amount=payment.amount,
        provider=payment.provider,
        reference=payment.reference,
        status=payment.status.value,
        requested_at=payment.requested_at,
        paid_at=payment.paid_at,
    )


@router.get("/orders/{order_id}", response_model=PaymentResponse)
async def get_order_payment(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if current_user.role != UserRole.ADMIN and current_user.id not in {
        order.client_id,
        order.carrier_id,
    }:
        raise HTTPException(status_code=403, detail="Нет доступа к платежу")

    payment = await get_payment(db, order_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Платеж не найден")
    return _serialize(payment)


@router.post("/orders/{order_id}/pay", response_model=PaymentResponse)
async def pay_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if current_user.role != UserRole.ADMIN and current_user.id != order.client_id:
        raise HTTPException(status_code=403, detail="Оплатить заявку может только заказчик")

    payment = await ensure_payment_for_order(db, order=order, requester_id=current_user.id)
    payment.status = PaymentStatus.PAID
    payment.paid_at = datetime.now(timezone.utc)

    if order.status == OrderStatus.DRAFT:
        order.status = OrderStatus.PUBLISHED

    return _serialize(payment)


@router.post("/orders/{order_id}/cancel", response_model=PaymentResponse)
async def cancel_payment(
    order_id: int,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    payment = await get_payment(db, order_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Платеж не найден")

    payment.status = PaymentStatus.CANCELLED
    return _serialize(payment)
