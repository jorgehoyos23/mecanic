from datetime import datetime

from sqlalchemy import Boolean, DateTime, Double, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db import Base, utcnow


class ServiceCatalog(Base):
    """Servicios que ofrece el taller (mantenimiento, reparación, diagnóstico)."""
    __tablename__ = "service_catalog"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(20), default="MANTENIMIENTO")
    base_price: Mapped[float] = mapped_column(Double, default=0)
    estimated_hours: Mapped[float] = mapped_column(Double, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Quote(Base):
    """Cotización generada a partir del diagnóstico de una orden de trabajo."""
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    labor_total: Mapped[float] = mapped_column(Double, default=0)
    parts_total: Mapped[float] = mapped_column(Double, default=0)
    total: Mapped[float] = mapped_column(Double, default=0)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["QuoteItem"]] = relationship(back_populates="quote", cascade="all, delete-orphan")


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # MANO_OBRA | REPUESTO | SERVICIO
    description: Mapped[str] = mapped_column(String(200))
    part_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quantity: Mapped[float] = mapped_column(Double, default=1)
    unit_price: Mapped[float] = mapped_column(Double, default=0)
    subtotal: Mapped[float] = mapped_column(Double, default=0)

    quote: Mapped[Quote] = relationship(back_populates="items")
