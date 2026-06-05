

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.logistics import OrderVehicleAssignment, Vehicle
from app.models.order import CargoType, Order, OrderStatus
from app.models.payment import PaymentStatus
from app.models.user import User, UserRole
from app.services.logistics import (
    build_vehicle_label,
    ensure_payment_for_order,
    estimate_order,
    get_order_assignment,
    get_payment,
)

router = APIRouter()


class OrderCreate(BaseModel):
    origin_city: str
    origin_address: str
    destination_city: str
    destination_address: str
    cargo_name: str
    cargo_type: CargoType = CargoType.GENERAL
    weight_kg: float
    volume_m3: float | None = None
    description: str | None = None
    budget: Decimal | None = None
    pickup_date: datetime | None = None


class OrderResponse(BaseModel):
    id: int
    origin_city: str
    origin_address: str
    destination_city: str
    destination_address: str
    cargo_name: str
    cargo_type: str
    weight_kg: float
    volume_m3: float | None = None
    description: str | None = None
    budget: Decimal | None = None
    final_price: Decimal | None = None
    distance_km: float | None = None
    status: str
    pickup_date: datetime | None = None
    delivery_date: datetime | None = None
    created_at: datetime
    client_id: int
    carrier_id: int | None = None
    client_name: str | None = None
    carrier_name: str | None = None
    payment_status: str | None = None
    payment_amount: Decimal | None = None
    vehicle_id: int | None = None
    vehicle_label: str | None = None


class PaginatedOrders(BaseModel):
    items: list[OrderResponse]
    total: int
    page: int
    per_page: int
    pages: int


async def _serialize_order(db: AsyncSession, order: Order) -> OrderResponse:
    payment = await get_payment(db, order.id)
    assignment = await get_order_assignment(db, order.id)
    vehicle_label = None
    vehicle_id = None

    if assignment:
        vehicle = await db.scalar(
            select(Vehicle)
            .options(selectinload(Vehicle.vehicle_type))
            .where(Vehicle.id == assignment.vehicle_id)
        )
        if vehicle:
            vehicle_id = vehicle.id
            vehicle_label = build_vehicle_label(vehicle)

    client_name = None
    carrier_name = None

    if order.client_id:
        client = await db.get(User, order.client_id)
        client_name = client.full_name if client else None
    if order.carrier_id:
        carrier = await db.get(User, order.carrier_id)
        carrier_name = carrier.full_name if carrier else None

    return OrderResponse(
        id=order.id,
        origin_city=order.origin_city,
        origin_address=order.origin_address,
        destination_city=order.destination_city,
        destination_address=order.destination_address,
        cargo_name=order.cargo_name,
        cargo_type=order.cargo_type.value,
        weight_kg=order.weight_kg,
        volume_m3=order.volume_m3,
        description=order.description,
        budget=order.budget,
        final_price=order.final_price,
        distance_km=order.distance_km,
        status=order.status.value,
        pickup_date=order.pickup_date,
        delivery_date=order.delivery_date,
        created_at=order.created_at,
        client_id=order.client_id,
        carrier_id=order.carrier_id,
        client_name=client_name,
        carrier_name=carrier_name,
        payment_status=payment.status.value if payment else None,
        payment_amount=payment.amount if payment else None,
        vehicle_id=vehicle_id,
        vehicle_label=vehicle_label,
    )


async def _get_order_or_404(db: AsyncSession, order_id: int) -> Order:
    order = await db.scalar(select(Order).where(Order.id == order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return order


@router.get("/", response_model=PaginatedOrders)
async def list_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    status_filter: str | None = Query(None, alias="status"),
    city: str | None = None,
    origin_city: str | None = None,
    destination_city: str | None = None,
    cargo_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Order)

    if status_filter:
        query = query.where(Order.status == status_filter)
    else:
        query = query.where(Order.status == OrderStatus.PUBLISHED)

    if city:
        query = query.where(
            or_(
                Order.origin_city.ilike(f"%{city}%"),
                Order.destination_city.ilike(f"%{city}%"),
            )
        )
    if origin_city:
        query = query.where(Order.origin_city.ilike(f"%{origin_city}%"))
    if destination_city:
        query = query.where(Order.destination_city.ilike(f"%{destination_city}%"))
    if cargo_type:
        query = query.where(Order.cargo_type == cargo_type)

    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    offset = (page - 1) * per_page
    result = await db.execute(
        query.order_by(Order.created_at.desc()).offset(offset).limit(per_page)
    )
    orders = result.scalars().all()

    return PaginatedOrders(
        items=[await _serialize_order(db, order) for order in orders],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total else 0,
    )


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in (UserRole.CLIENT, UserRole.ADMIN):
        raise HTTPException(
            status_code=403,
            detail="Только грузовладелец или администратор может создать заявку",
        )

    estimate = await estimate_order(
        db,
        origin_city=data.origin_city,
        destination_city=data.destination_city,
        weight_kg=data.weight_kg,
        volume_m3=data.volume_m3,
    )

    order = Order(
        client_id=current_user.id,
        status=OrderStatus.DRAFT,
        distance_km=estimate.distance_km,
        final_price=estimate.final_price,
        **data.model_dump(),
    )
    db.add(order)
    await db.flush()
    await ensure_payment_for_order(db, order=order, requester_id=current_user.id)
    await db.refresh(order)
    return await _serialize_order(db, order)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    return await _serialize_order(db, await _get_order_or_404(db, order_id))


@router.patch("/{order_id}/take")
async def take_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in (UserRole.CARRIER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Только перевозчик может взять заявку")

    order = await _get_order_or_404(db, order_id)
    if order.status != OrderStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Заявка недоступна для взятия в работу")

    order.carrier_id = current_user.id
    order.status = OrderStatus.IN_PROGRESS
    return {"message": "Заявка взята в работу", "order_id": order_id}


@router.patch("/{order_id}/complete")
async def complete_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await _get_order_or_404(db, order_id)
    if order.status != OrderStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Заявку можно завершить только со статусом 'В работе'")

    allowed = {order.client_id}

    if order.carrier_id:
        allowed.add(order.carrier_id)
    if current_user.role != UserRole.ADMIN and current_user.id not in allowed:
        raise HTTPException(status_code=403, detail="Нет прав на завершение заявки")

    order.status = OrderStatus.COMPLETED

    assignment = await get_order_assignment(db, order_id)
    if assignment:
        vehicle = await db.get(Vehicle, assignment.vehicle_id)
        if vehicle:
            vehicle.is_available = True

    if order.carrier_id:
        carrier = await db.get(User, order.carrier_id)
        if carrier:
            carrier.total_orders += 1

    client = await db.get(User, order.client_id)
    if client:
        client.total_orders += 1

    return {"message": "Заявка завершена", "order_id": order_id}
