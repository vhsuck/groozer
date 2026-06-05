

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import require_roles
from app.models.logistics import OrderVehicleAssignment, Vehicle
from app.models.order import Order, OrderStatus
from app.models.payment import PaymentStatus, PaymentTransaction
from app.models.user import User, UserRole
from app.services.logistics import build_vehicle_label

router = APIRouter()


class DashboardStats(BaseModel):
    users_total: int
    carriers_total: int
    orders_total: int
    orders_published: int
    orders_in_progress: int
    payments_pending: int
    payments_paid: int
    revenue_paid: Decimal
    vehicles_total: int
    vehicles_available: int


class AdminUserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    is_verified: bool | None = None
    rating: float | None = None


class AdminOrderUpdate(BaseModel):
    status: OrderStatus


class AssignVehicleRequest(BaseModel):
    vehicle_id: int


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    users_total = await db.scalar(select(func.count()).select_from(User)) or 0
    carriers_total = await db.scalar(
        select(func.count()).select_from(select(User).where(User.role == UserRole.CARRIER).subquery())
    ) or 0
    orders_total = await db.scalar(select(func.count()).select_from(Order)) or 0
    orders_published = await db.scalar(
        select(func.count()).select_from(select(Order).where(Order.status == OrderStatus.PUBLISHED).subquery())
    ) or 0
    orders_in_progress = await db.scalar(
        select(func.count()).select_from(select(Order).where(Order.status == OrderStatus.IN_PROGRESS).subquery())
    ) or 0
    payments_pending = await db.scalar(
        select(func.count()).select_from(
            select(PaymentTransaction).where(PaymentTransaction.status == PaymentStatus.PENDING).subquery()
        )
    ) or 0
    payments_paid = await db.scalar(
        select(func.count()).select_from(
            select(PaymentTransaction).where(PaymentTransaction.status == PaymentStatus.PAID).subquery()
        )
    ) or 0
    revenue_paid = await db.scalar(
        select(func.coalesce(func.sum(PaymentTransaction.amount), 0)).where(
            PaymentTransaction.status == PaymentStatus.PAID
        )
    ) or Decimal("0.00")
    vehicles_total = await db.scalar(select(func.count()).select_from(Vehicle)) or 0
    vehicles_available = await db.scalar(
        select(func.count()).select_from(
            select(Vehicle).where(Vehicle.is_available == True, Vehicle.is_active == True).subquery()  # noqa: E712
        )
    ) or 0

    return DashboardStats(
        users_total=users_total,
        carriers_total=carriers_total,
        orders_total=orders_total,
        orders_published=orders_published,
        orders_in_progress=orders_in_progress,
        payments_pending=payments_pending,
        payments_paid=payments_paid,
        revenue_paid=revenue_paid,
        vehicles_total=vehicles_total,
        vehicles_available=vehicles_available,
    )


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(per_page)
    )
    users = result.scalars().all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "rating": user.rating,
            "total_orders": user.total_orders,
            "created_at": user.created_at.isoformat(),
        }
        for user in users
    ]


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    data: AdminUserUpdate,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(user, key, value)

    return {
        "id": user.id,
        "role": user.role.value,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "rating": user.rating,
    }


@router.get("/orders")
async def list_all_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Order).order_by(Order.created_at.desc()).offset(offset).limit(per_page)
    )
    orders = result.scalars().all()
    items = []
    for order in orders:
        assignment = await db.scalar(
            select(OrderVehicleAssignment).where(OrderVehicleAssignment.order_id == order.id)
        )
        vehicle_label = None
        if assignment:
            vehicle = await db.scalar(
                select(Vehicle)
                .options(selectinload(Vehicle.vehicle_type))
                .where(Vehicle.id == assignment.vehicle_id)
            )
            if vehicle:
                vehicle_label = build_vehicle_label(vehicle)
        items.append(
            {
                "id": order.id,
                "route": f"{order.origin_city} → {order.destination_city}",
                "cargo_name": order.cargo_name,
                "weight_kg": order.weight_kg,
                "status": order.status.value,
                "client_id": order.client_id,
                "carrier_id": order.carrier_id,
                "distance_km": order.distance_km,
                "final_price": str(order.final_price) if order.final_price is not None else None,
                "vehicle_label": vehicle_label,
                "created_at": order.created_at.isoformat(),
            }
        )
    return items


@router.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    data: AdminOrderUpdate,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    order.status = data.status
    return {"id": order.id, "status": order.status.value}


@router.post("/orders/{order_id}/assign-vehicle")
async def assign_vehicle(
    order_id: int,
    data: AssignVehicleRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    vehicle = await db.scalar(
        select(Vehicle)
        .options(selectinload(Vehicle.vehicle_type))
        .where(Vehicle.id == data.vehicle_id)
    )
    if not vehicle:
        raise HTTPException(status_code=404, detail="Транспорт не найден")
    if not vehicle.is_active or not vehicle.is_available:
        raise HTTPException(status_code=400, detail="Транспорт недоступен")
    if vehicle.payload_kg < order.weight_kg:
        raise HTTPException(status_code=400, detail="Транспорт не подходит по грузоподъемности")
    if order.volume_m3 and vehicle.volume_m3 and vehicle.volume_m3 < order.volume_m3:
        raise HTTPException(status_code=400, detail="Транспорт не подходит по объему")

    existing = await db.scalar(
        select(OrderVehicleAssignment).where(OrderVehicleAssignment.order_id == order_id)
    )
    if existing:
        previous_vehicle = await db.get(Vehicle, existing.vehicle_id)
        if previous_vehicle:
            previous_vehicle.is_available = True
        existing.vehicle_id = vehicle.id
        existing.assigned_by_id = current_user.id
    else:
        db.add(
            OrderVehicleAssignment(
                order_id=order.id,
                vehicle_id=vehicle.id,
                assigned_by_id=current_user.id,
            )
        )

    vehicle.is_available = False
    if order.status == OrderStatus.PUBLISHED:
        order.status = OrderStatus.IN_PROGRESS

    return {
        "order_id": order.id,
        "vehicle_id": vehicle.id,
        "vehicle_label": build_vehicle_label(vehicle),
        "status": order.status.value,
    }


@router.get("/payments")
async def list_payments(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PaymentTransaction).order_by(PaymentTransaction.requested_at.desc())
    )
    payments = result.scalars().all()
    return [
        {
            "id": payment.id,
            "order_id": payment.order_id,
            "requester_id": payment.requester_id,
            "amount": str(payment.amount),
            "provider": payment.provider,
            "reference": payment.reference,
            "status": payment.status.value,
            "requested_at": payment.requested_at.isoformat(),
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        }
        for payment in payments
    ]
