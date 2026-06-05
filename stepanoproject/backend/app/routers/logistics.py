

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import require_roles
from app.models.logistics import City, Vehicle, VehicleType
from app.models.user import User, UserRole
from app.services.logistics import build_vehicle_label, find_matching_vehicles

router = APIRouter()


class CityCreate(BaseModel):
    name: str
    region: str | None = None
    latitude: float
    longitude: float
    is_active: bool = True


class VehicleTypeCreate(BaseModel):
    name: str
    payload_kg: float
    volume_m3: float | None = None
    base_rate_per_km: float
    min_price: float = 3500
    description: str | None = None
    is_active: bool = True


class VehicleCreate(BaseModel):
    model: str
    plate_number: str
    vehicle_type_id: int
    city_id: int | None = None
    owner_id: int | None = None
    payload_kg: float
    volume_m3: float | None = None
    notes: str | None = None
    is_active: bool = True
    is_available: bool = True


class VehicleUpdate(BaseModel):
    city_id: int | None = None
    owner_id: int | None = None
    payload_kg: float | None = None
    volume_m3: float | None = None
    notes: str | None = None
    is_active: bool | None = None
    is_available: bool | None = None


class CityResponse(BaseModel):
    id: int
    name: str
    region: str | None
    latitude: float
    longitude: float
    is_active: bool


class VehicleTypeResponse(BaseModel):
    id: int
    name: str
    payload_kg: float
    volume_m3: float | None
    base_rate_per_km: float
    min_price: float
    description: str | None
    is_active: bool


class VehicleResponse(BaseModel):
    id: int
    model: str
    plate_number: str
    payload_kg: float
    volume_m3: float | None
    notes: str | None
    is_active: bool
    is_available: bool
    city_id: int | None
    city_name: str | None
    owner_id: int | None
    owner_name: str | None
    vehicle_type_id: int
    vehicle_type_name: str
    label: str
    created_at: datetime


def _vehicle_to_response(vehicle: Vehicle) -> VehicleResponse:
    owner_name = vehicle.owner.full_name if vehicle.owner else None
    city_name = vehicle.city.name if vehicle.city else None
    return VehicleResponse(
        id=vehicle.id,
        model=vehicle.model,
        plate_number=vehicle.plate_number,
        payload_kg=vehicle.payload_kg,
        volume_m3=vehicle.volume_m3,
        notes=vehicle.notes,
        is_active=vehicle.is_active,
        is_available=vehicle.is_available,
        city_id=vehicle.city_id,
        city_name=city_name,
        owner_id=vehicle.owner_id,
        owner_name=owner_name,
        vehicle_type_id=vehicle.vehicle_type_id,
        vehicle_type_name=vehicle.vehicle_type.name,
        label=build_vehicle_label(vehicle),
        created_at=vehicle.created_at,
    )


@router.get("/cities", response_model=list[CityResponse])
async def list_cities(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
):
    query = select(City).order_by(City.name.asc())
    if not include_inactive:
        query = query.where(City.is_active == True)  
    result = await db.execute(query)
    return [
        CityResponse(
            id=city.id,
            name=city.name,
            region=city.region,
            latitude=city.latitude,
            longitude=city.longitude,
            is_active=city.is_active,
        )
        for city in result.scalars().all()
    ]


@router.post("/cities", response_model=CityResponse, status_code=status.HTTP_201_CREATED)
async def create_city(
    data: CityCreate,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(select(City).where(City.name == data.name))
    if existing:
        raise HTTPException(status_code=400, detail="Город уже существует")

    city = City(**data.model_dump())
    db.add(city)
    await db.flush()
    return CityResponse(
        id=city.id,
        name=city.name,
        region=city.region,
        latitude=city.latitude,
        longitude=city.longitude,
        is_active=city.is_active,
    )


@router.get("/vehicle-types", response_model=list[VehicleTypeResponse])
async def list_vehicle_types(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
):
    query = select(VehicleType).order_by(VehicleType.payload_kg.asc())
    if not include_inactive:
        query = query.where(VehicleType.is_active == True) 
    result = await db.execute(query)
    return [
        VehicleTypeResponse(
            id=item.id,
            name=item.name,
            payload_kg=item.payload_kg,
            volume_m3=item.volume_m3,
            base_rate_per_km=item.base_rate_per_km,
            min_price=item.min_price,
            description=item.description,
            is_active=item.is_active,
        )
        for item in result.scalars().all()
    ]


@router.post("/vehicle-types", response_model=VehicleTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle_type(
    data: VehicleTypeCreate,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(select(VehicleType).where(VehicleType.name == data.name))
    if existing:
        raise HTTPException(status_code=400, detail="Тип транспорта уже существует")

    vehicle_type = VehicleType(**data.model_dump())
    db.add(vehicle_type)
    await db.flush()
    return VehicleTypeResponse(
        id=vehicle_type.id,
        name=vehicle_type.name,
        payload_kg=vehicle_type.payload_kg,
        volume_m3=vehicle_type.volume_m3,
        base_rate_per_km=vehicle_type.base_rate_per_km,
        min_price=vehicle_type.min_price,
        description=vehicle_type.description,
        is_active=vehicle_type.is_active,
    )


@router.get("/vehicles", response_model=list[VehicleResponse])
async def list_vehicles(
    city_id: int | None = None,
    vehicle_type_id: int | None = None,
    available_only: bool = Query(False, alias="available"),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Vehicle)
        .options(
            selectinload(Vehicle.city),
            selectinload(Vehicle.owner),
            selectinload(Vehicle.vehicle_type),
        )
        .order_by(Vehicle.created_at.desc())
    )
    if city_id:
        query = query.where(Vehicle.city_id == city_id)
    if vehicle_type_id:
        query = query.where(Vehicle.vehicle_type_id == vehicle_type_id)
    if available_only:
        query = query.where(Vehicle.is_available == True, Vehicle.is_active == True)  

    result = await db.execute(query)
    return [_vehicle_to_response(vehicle) for vehicle in result.scalars().all()]


@router.post("/vehicles", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    data: VehicleCreate,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    if await db.scalar(select(Vehicle).where(Vehicle.plate_number == data.plate_number)):
        raise HTTPException(status_code=400, detail="ТС с таким номером уже существует")

    vehicle_type = await db.get(VehicleType, data.vehicle_type_id)
    if not vehicle_type:
        raise HTTPException(status_code=404, detail="Тип транспорта не найден")
    if data.city_id and not await db.get(City, data.city_id):
        raise HTTPException(status_code=404, detail="Город не найден")
    if data.owner_id and not await db.get(User, data.owner_id):
        raise HTTPException(status_code=404, detail="Пользователь-владелец не найден")

    vehicle = Vehicle(**data.model_dump())
    db.add(vehicle)
    await db.flush()
    vehicle = await db.scalar(
        select(Vehicle)
        .options(
            selectinload(Vehicle.city),
            selectinload(Vehicle.owner),
            selectinload(Vehicle.vehicle_type),
        )
        .where(Vehicle.id == vehicle.id)
    )
    return _vehicle_to_response(vehicle)


@router.patch("/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: int,
    data: VehicleUpdate,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    vehicle = await db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Транспорт не найден")

    payload = data.model_dump(exclude_unset=True)
    if "city_id" in payload and payload["city_id"] and not await db.get(City, payload["city_id"]):
        raise HTTPException(status_code=404, detail="Город не найден")
    if "owner_id" in payload and payload["owner_id"] and not await db.get(User, payload["owner_id"]):
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    for key, value in payload.items():
        setattr(vehicle, key, value)

    await db.flush()
    vehicle = await db.scalar(
        select(Vehicle)
        .options(
            selectinload(Vehicle.city),
            selectinload(Vehicle.owner),
            selectinload(Vehicle.vehicle_type),
        )
        .where(Vehicle.id == vehicle.id)
    )
    return _vehicle_to_response(vehicle)


@router.get("/orders/{order_id}/matches", response_model=list[VehicleResponse])
async def list_matching_vehicles(
    order_id: int,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    from app.models.order import Order

    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    vehicles = await find_matching_vehicles(db, order)
    ids = [vehicle.id for vehicle in vehicles]
    if not ids:
        return []
    result = await db.execute(
        select(Vehicle)
        .options(
            selectinload(Vehicle.city),
            selectinload(Vehicle.owner),
            selectinload(Vehicle.vehicle_type),
        )
        .where(Vehicle.id.in_(ids))
    )
    return [_vehicle_to_response(vehicle) for vehicle in result.scalars().all()]
