"""Модель заявки на перевозку."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Text, Numeric, DateTime, Enum as SAEnum, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"           
    PUBLISHED = "published"   
    IN_PROGRESS = "in_progress"  
    COMPLETED = "completed"   
    CANCELLED = "cancelled"  
    DISPUTED = "disputed"     


class CargoType(str, enum.Enum):
    GENERAL = "general"       
    FRAGILE = "fragile"       
    PERISHABLE = "perishable" 
    OVERSIZED = "oversized"   
    HAZARDOUS = "hazardous"   
    LIQUID = "liquid"         


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    carrier_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    origin_city: Mapped[str] = mapped_column(String(255), nullable=False)
    origin_address: Mapped[str] = mapped_column(String(500), nullable=False)
    destination_city: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_address: Mapped[str] = mapped_column(String(500), nullable=False)
    distance_km: Mapped[float | None] = mapped_column(Float)

    cargo_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cargo_type: Mapped[CargoType] = mapped_column(
        SAEnum(CargoType), default=CargoType.GENERAL
    )
    weight_kg: Mapped[float] = mapped_column(nullable=False)
    volume_m3: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(Text)

    budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    final_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus), default=OrderStatus.DRAFT, index=True
    )
    pickup_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["User"] = relationship( 
        "User", back_populates="client_orders", foreign_keys=[client_id]
    )
    carrier: Mapped["User | None"] = relationship( 
        "User", back_populates="carrier_orders", foreign_keys=[carrier_id]
    )
    cargo_docs: Mapped[list["CargoDocument"]] = relationship( 
        "CargoDocument", back_populates="order"
    )

    def __repr__(self) -> str:
        return f"<Order #{self.id} {self.origin_city}→{self.destination_city} [{self.status}]>"
