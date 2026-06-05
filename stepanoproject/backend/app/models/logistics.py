

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    region: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    vehicles: Mapped[list["Vehicle"]] = relationship("Vehicle", back_populates="city") 


class VehicleType(Base):
    __tablename__ = "vehicle_types"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    payload_kg: Mapped[float] = mapped_column(Float, nullable=False)
    volume_m3: Mapped[float | None] = mapped_column(Float)
    base_rate_per_km: Mapped[float] = mapped_column(Float, nullable=False)
    min_price: Mapped[float] = mapped_column(Float, default=3500, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    vehicles: Mapped[list["Vehicle"]] = relationship("Vehicle", back_populates="vehicle_type")  # noqa: F821


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (UniqueConstraint("plate_number", name="uq_vehicles_plate_number"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), index=True)
    vehicle_type_id: Mapped[int] = mapped_column(ForeignKey("vehicle_types.id"), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    plate_number: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_kg: Mapped[float] = mapped_column(Float, nullable=False)
    volume_m3: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User | None"] = relationship("User")  
    city: Mapped["City | None"] = relationship("City", back_populates="vehicles")  
    vehicle_type: Mapped["VehicleType"] = relationship("VehicleType", back_populates="vehicles")  


class OrderVehicleAssignment(Base):
    __tablename__ = "order_vehicle_assignments"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_order_vehicle_assignments_order_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    assigned_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order: Mapped["Order"] = relationship("Order")  
    vehicle: Mapped["Vehicle"] = relationship("Vehicle")  
    assigned_by: Mapped["User"] = relationship("User")  
