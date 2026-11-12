from datetime import datetime

from sqlalchemy import Boolean, DateTime, Double, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db import Base, utcnow


class Part(Base):
    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    brand: Mapped[str | None] = mapped_column(String(60), nullable=True)
    category: Mapped[str] = mapped_column(String(60), default="General")
    unit_price: Mapped[float] = mapped_column(Double, default=0)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    min_stock: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    movements: Mapped[list["StockMovement"]] = relationship(back_populates="part")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id"), index=True)
    type: Mapped[str] = mapped_column(String(20))  # ENTRADA | SALIDA | DEVOLUCION | AJUSTE
    quantity: Mapped[int] = mapped_column(Integer)  # positivo suma stock, negativo resta
    order_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    part: Mapped[Part] = relationship(back_populates="movements")
