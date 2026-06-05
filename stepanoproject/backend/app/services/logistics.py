"""Сидинг и вспомогательные функции для логистики."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import math
import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.logistics import City, OrderVehicleAssignment, Vehicle, VehicleType
from app.models.order import Order, OrderStatus
from app.models.payment import PaymentStatus, PaymentTransaction
from app.models.user import User, UserRole


DEFAULT_CITIES = [
    {"name": "Москва", "region": "Москва", "latitude": 55.7558, "longitude": 37.6176},
    {"name": "Санкт-Петербург", "region": "СЗФО", "latitude": 59.9343, "longitude": 30.3351},
    {"name": "Казань", "region": "Татарстан", "latitude": 55.7961, "longitude": 49.1064},
    {"name": "Уфа", "region": "Башкортостан", "latitude": 54.7388, "longitude": 55.9721},
    {"name": "Новосибирск", "region": "Новосибирская область", "latitude": 55.0084, "longitude": 82.9357},
    {"name": "Томск", "region": "Томская область", "latitude": 56.4846, "longitude": 84.9480},
    {"name": "Ростов-на-Дону", "region": "Ростовская область", "latitude": 47.2357, "longitude": 39.7015},
    {"name": "Краснодар", "region": "Краснодарский край", "latitude": 45.0355, "longitude": 38.9753},
    {"name": "Екатеринбург", "region": "Свердловская область", "latitude": 56.8389, "longitude": 60.6057},
    {"name": "Челябинск", "region": "Челябинская область", "latitude": 55.1644, "longitude": 61.4368},
    {"name": "Самара", "region": "Самарская область", "latitude": 53.1959, "longitude": 50.1008},
    {"name": "Тольятти", "region": "Самарская область", "latitude": 53.5078, "longitude": 49.4204},
    {"name": "Владивосток", "region": "Приморский край", "latitude": 43.1155, "longitude": 131.8855},
    {"name": "Хабаровск", "region": "Хабаровский край", "latitude": 48.4802, "longitude": 135.0719},
    {"name": "Воронеж", "region": "Воронежская область", "latitude": 51.6755, "longitude": 39.2089},
    {"name": "Белгород", "region": "Белгородская область", "latitude": 50.5954, "longitude": 36.5879},
    {"name": "Пермь", "region": "Пермский край", "latitude": 58.0105, "longitude": 56.2502},
    {"name": "Ижевск", "region": "Удмуртия", "latitude": 56.8528, "longitude": 53.2115},
    {"name": "Красноярск", "region": "Красноярский край", "latitude": 56.0153, "longitude": 92.8932},
    {"name": "Иркутск", "region": "Иркутская область", "latitude": 52.2864, "longitude": 104.3050},
    {"name": "Тюмень", "region": "Тюменская область", "latitude": 57.1530, "longitude": 65.5343},
    {"name": "Омск", "region": "Омская область", "latitude": 54.9885, "longitude": 73.3242},
    {"name": "Волгоград", "region": "Волгоградская область", "latitude": 48.7080, "longitude": 44.5133},
    {"name": "Астрахань", "region": "Астраханская область", "latitude": 46.3497, "longitude": 48.0408},
]

DEFAULT_VEHICLE_TYPES = [
    {
        "name": "Газель",
        "payload_kg": 1500,
        "volume_m3": 12,
        "base_rate_per_km": 24,
        "min_price": 3500,
        "description": "Подходит для квартирных переездов и малого бизнеса.",
    },
    {
        "name": "Фургон 5т",
        "payload_kg": 5000,
        "volume_m3": 35,
        "base_rate_per_km": 38,
        "min_price": 7000,
        "description": "Универсальный междугородний транспорт.",
    },
    {
        "name": "Рефрижератор",
        "payload_kg": 7000,
        "volume_m3": 40,
        "base_rate_per_km": 46,
        "min_price": 9500,
        "description": "Для скоропортящихся грузов.",
    },
    {
        "name": "Трал / негабарит",
        "payload_kg": 20000,
        "volume_m3": 65,
        "base_rate_per_km": 62,
        "min_price": 18000,
        "description": "Для тяжёлых и негабаритных грузов.",
    },
    {
        "name": "Цистерна",
        "payload_kg": 12000,
        "volume_m3": 45,
        "base_rate_per_km": 55,
        "min_price": 14000,
        "description": "Для жидкостей и наливных грузов.",
    },
]

DEFAULT_VEHICLES = [
    {"model": "ГАЗ Next", "plate_number": "A101AA777", "type_name": "Газель", "city_name": "Москва", "payload_kg": 1500, "volume_m3": 12},
    {"model": "Ford Transit", "plate_number": "B202BB116", "type_name": "Газель", "city_name": "Казань", "payload_kg": 1400, "volume_m3": 11},
    {"model": "MAN TGS", "plate_number": "C303CC163", "type_name": "Фургон 5т", "city_name": "Самара", "payload_kg": 5000, "volume_m3": 36},
    {"model": "Volvo FH", "plate_number": "E404EE66", "type_name": "Фургон 5т", "city_name": "Екатеринбург", "payload_kg": 5500, "volume_m3": 38},
    {"model": "Schmitz SKO", "plate_number": "K505KK54", "type_name": "Рефрижератор", "city_name": "Новосибирск", "payload_kg": 7000, "volume_m3": 40},
    {"model": "Krone Cool Liner", "plate_number": "M606MM23", "type_name": "Рефрижератор", "city_name": "Краснодар", "payload_kg": 6800, "volume_m3": 39},
    {"model": "Kassbohrer Lowbed", "plate_number": "O707OO25", "type_name": "Трал / негабарит", "city_name": "Владивосток", "payload_kg": 22000, "volume_m3": 70},
    {"model": "Bonum Tank", "plate_number": "P808PP34", "type_name": "Цистерна", "city_name": "Волгоград", "payload_kg": 12000, "volume_m3": 45},
]


@dataclass(slots=True)
class EstimateResult:
    distance_km: float | None
    vehicle_type: VehicleType | None
    final_price: Decimal | None


def _normalize_city_name(value: str) -> str:
    return value.strip().casefold()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


async def bootstrap_reference_data(
    db: AsyncSession,
    *,
    admin_email: str,
    admin_username: str,
    admin_password: str,
) -> None:
    """Создаёт стартовые справочники и администратора при пустой БД."""

    existing_admin = await db.scalar(
        select(User).where(User.role == UserRole.ADMIN).limit(1)
    )
    if not existing_admin:
        db.add(
            User(
                email=admin_email,
                username=admin_username,
                full_name="Системный администратор",
                hashed_password=hash_password(admin_password),
                role=UserRole.ADMIN,
                is_verified=True,
            )
        )

    if not await db.scalar(select(City.id).limit(1)):
        db.add_all(City(**payload) for payload in DEFAULT_CITIES)

    if not await db.scalar(select(VehicleType.id).limit(1)):
        db.add_all(VehicleType(**payload) for payload in DEFAULT_VEHICLE_TYPES)
        await db.flush()

    if not await db.scalar(select(Vehicle.id).limit(1)):
        city_map = await _city_map(db)
        type_map = await _vehicle_type_map(db)
        vehicles = []
        for payload in DEFAULT_VEHICLES:
            vehicles.append(
                Vehicle(
                    model=payload["model"],
                    plate_number=payload["plate_number"],
                    payload_kg=payload["payload_kg"],
                    volume_m3=payload["volume_m3"],
                    city_id=city_map[payload["city_name"]].id,
                    vehicle_type_id=type_map[payload["type_name"]].id,
                    is_available=True,
                    is_active=True,
                )
            )
        db.add_all(vehicles)


async def _city_map(db: AsyncSession) -> dict[str, City]:
    result = await db.execute(select(City))
    return {city.name: city for city in result.scalars().all()}


async def _vehicle_type_map(db: AsyncSession) -> dict[str, VehicleType]:
    result = await db.execute(select(VehicleType))
    return {vehicle_type.name: vehicle_type for vehicle_type in result.scalars().all()}


async def find_city_by_name(db: AsyncSession, name: str) -> City | None:
    if not name.strip():
        return None

    result = await db.execute(select(City).where(City.is_active == True))  # noqa: E712
    normalized = _normalize_city_name(name)
    for city in result.scalars().all():
        if _normalize_city_name(city.name) == normalized:
            return city
    return None


async def match_vehicle_types(
    db: AsyncSession, *, weight_kg: float, volume_m3: float | None = None
) -> list[VehicleType]:
    query: Select[tuple[VehicleType]] = select(VehicleType).where(VehicleType.is_active == True)  # noqa: E712
    result = await db.execute(query.order_by(VehicleType.payload_kg.asc()))
    items = []
    for vehicle_type in result.scalars().all():
        if vehicle_type.payload_kg < weight_kg:
            continue
        if volume_m3 and vehicle_type.volume_m3 and vehicle_type.volume_m3 < volume_m3:
            continue
        items.append(vehicle_type)
    return items


def calculate_price(
    *,
    distance_km: float | None,
    weight_kg: float,
    vehicle_type: VehicleType | None,
) -> Decimal | None:
    if not distance_km or not vehicle_type:
        return None

    base = Decimal(str(vehicle_type.base_rate_per_km)) * Decimal(str(distance_km))
    weight_markup = Decimal(str(max(weight_kg, 0))) * Decimal("0.55")
    result = base + weight_markup
    minimum = Decimal(str(vehicle_type.min_price))
    return result.quantize(Decimal("0.01")) if result > minimum else minimum.quantize(Decimal("0.01"))


async def estimate_order(
    db: AsyncSession,
    *,
    origin_city: str,
    destination_city: str,
    weight_kg: float,
    volume_m3: float | None = None,
) -> EstimateResult:
    origin = await find_city_by_name(db, origin_city)
    destination = await find_city_by_name(db, destination_city)
    if not origin or not destination:
        return EstimateResult(distance_km=None, vehicle_type=None, final_price=None)

    distance = round(
        _haversine_km(origin.latitude, origin.longitude, destination.latitude, destination.longitude),
        1,
    )
    types = await match_vehicle_types(db, weight_kg=weight_kg, volume_m3=volume_m3)
    best = types[0] if types else None
    return EstimateResult(
        distance_km=distance,
        vehicle_type=best,
        final_price=calculate_price(distance_km=distance, weight_kg=weight_kg, vehicle_type=best),
    )


async def find_matching_vehicles(db: AsyncSession, order: Order) -> list[Vehicle]:
    query = select(Vehicle).where(
        Vehicle.is_active == True,  
        Vehicle.is_available == True,  
        Vehicle.payload_kg >= order.weight_kg,
    )
    result = await db.execute(query)
    items = []
    for vehicle in result.scalars().all():
        if order.volume_m3 and vehicle.volume_m3 and vehicle.volume_m3 < order.volume_m3:
            continue
        items.append(vehicle)
    return items


async def get_order_assignment(db: AsyncSession, order_id: int) -> OrderVehicleAssignment | None:
    return await db.scalar(
        select(OrderVehicleAssignment).where(OrderVehicleAssignment.order_id == order_id)
    )


async def get_payment(db: AsyncSession, order_id: int) -> PaymentTransaction | None:
    return await db.scalar(
        select(PaymentTransaction).where(PaymentTransaction.order_id == order_id)
    )


async def ensure_payment_for_order(
    db: AsyncSession, *, order: Order, requester_id: int
) -> PaymentTransaction:
    payment = await get_payment(db, order.id)
    amount = order.final_price or order.budget or Decimal("0.00")
    if payment:
        payment.amount = amount
        if payment.status == PaymentStatus.CANCELLED:
            payment.status = PaymentStatus.PENDING
        return payment

    payment = PaymentTransaction(
        order_id=order.id,
        requester_id=requester_id,
        amount=amount,
        reference=uuid.uuid4().hex,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    await db.flush()
    return payment


def build_vehicle_label(vehicle: Vehicle) -> str:
    type_name = vehicle.vehicle_type.name if vehicle.vehicle_type else "Транспорт"
    return f"{type_name}: {vehicle.model} ({vehicle.plate_number})"


def is_order_visible(order: Order) -> bool:
    return order.status in {OrderStatus.PUBLISHED, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED}
