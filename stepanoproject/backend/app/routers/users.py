

from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, EmailStr

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.logistics import OrderVehicleAssignment, Vehicle
from app.models.order import Order
from app.models.user import User, UserRole
from app.services.logistics import build_vehicle_label, get_payment

router = APIRouter()

AVATAR_DIR = Path("static/uploads/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    company_name: str | None = None


@router.get("/carriers")
async def list_carriers(
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(User)
        .where(User.role == UserRole.CARRIER, User.is_active == True)  # noqa: E712
        .order_by(User.rating.desc())
        .offset(offset)
        .limit(per_page)
    )
    carriers = result.scalars().all()
    return [
        {
            "id": carrier.id,
            "username": carrier.username,
            "full_name": carrier.full_name,
            "company_name": carrier.company_name,
            "rating": carrier.rating,
            "total_orders": carrier.total_orders,
            "avatar_url": carrier.avatar_url,
            "is_verified": carrier.is_verified,
        }
        for carrier in carriers
    ]


@router.get("/me")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "company_name": current_user.company_name,
        "role": current_user.role.value,
        "rating": current_user.rating,
        "total_orders": current_user.total_orders,
        "avatar_url": current_user.avatar_url,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat(),
    }


@router.patch("/me")
async def update_my_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = data.model_dump(exclude_unset=True)

    if "email" in payload:
        existing = await db.scalar(
            select(User).where(User.email == payload["email"], User.id != current_user.id)
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email уже занят")

    for key, value in payload.items():
        setattr(current_user, key, value)

    await db.flush()
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "company_name": current_user.company_name,
        "avatar_url": current_user.avatar_url,
    }


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    allowed = {"jpg", "jpeg", "png", "webp"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Допустимы только изображения jpg, png, webp")

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="Файл слишком большой")

    avatar_name = f"{uuid.uuid4().hex}.{ext}"
    avatar_path = AVATAR_DIR / avatar_name
    avatar_path.write_bytes(content)
    current_user.avatar_url = f"/static/uploads/avatars/{avatar_name}"
    await db.flush()
    return {"avatar_url": current_user.avatar_url}


@router.get("/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role.value,
        "rating": user.rating,
        "total_orders": user.total_orders,
        "avatar_url": user.avatar_url,
        "company_name": user.company_name,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat(),
    }


@router.get("/me/orders")
async def my_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Order).order_by(Order.created_at.desc())
    if current_user.role == UserRole.CARRIER:
        query = query.where(Order.carrier_id == current_user.id)
    else:
        query = query.where(Order.client_id == current_user.id)

    result = await db.execute(query)
    orders = result.scalars().all()
    items = []
    for order in orders:
        payment = await get_payment(db, order.id)
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
                "origin_city": order.origin_city,
                "destination_city": order.destination_city,
                "cargo_name": order.cargo_name,
                "cargo_type": order.cargo_type.value,
                "weight_kg": order.weight_kg,
                "volume_m3": order.volume_m3,
                "budget": str(order.budget) if order.budget is not None else None,
                "final_price": str(order.final_price) if order.final_price is not None else None,
                "distance_km": order.distance_km,
                "status": order.status.value,
                "pickup_date": order.pickup_date.isoformat() if order.pickup_date else None,
                "created_at": order.created_at.isoformat(),
                "payment_status": payment.status.value if payment else None,
                "payment_amount": str(payment.amount) if payment else None,
                "vehicle_label": vehicle_label,
            }
        )
    return items
