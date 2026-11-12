from datetime import date, datetime

from sqlalchemy import Date, DateTime, Double, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db import Base, utcnow


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, default="")
    # referencias a otros microservicios (sin llaves foráneas: cada servicio tiene su BD)
    customer_id: Mapped[int] = mapped_column(Integer, index=True)
    client_user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    client_name: Mapped[str] = mapped_column(String(120), default="")
    vehicle_id: Mapped[int] = mapped_column(Integer, index=True)
    vehicle_label: Mapped[str] = mapped_column(String(160), default="")
    service_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    service_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    mechanic_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mechanic_user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    mechanic_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    quote_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quote_total: Mapped[float | None] = mapped_column(Double, nullable=True)
    invoice_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # datos propios de la orden
    kind: Mapped[str] = mapped_column(String(20), default="MANTENIMIENTO")
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="SOLICITADA", index=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_delivery: Mapped[date | None] = mapped_column(Date, nullable=True)
    mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["OrderEvent"]] = relationship(back_populates="order", order_by="OrderEvent.id",
                                                      cascade="all, delete-orphan")


class OrderEvent(Base):
    """Bitácora de la orden: cambios de estado y avances reportados."""
    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text, default="")
    author_name: Mapped[str] = mapped_column(String(120), default="")
    author_role: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    order: Mapped[WorkOrder] = relationship(back_populates="events")
