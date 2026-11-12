from datetime import datetime

from sqlalchemy import DateTime, Double, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db import Base, utcnow


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, index=True, default="")
    order_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    order_code: Mapped[str] = mapped_column(String(20))
    customer_id: Mapped[int] = mapped_column(Integer, index=True)
    client_user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    client_name: Mapped[str] = mapped_column(String(120), default="")
    vehicle_label: Mapped[str] = mapped_column(String(160), default="")
    client_email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    client_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    client_document: Mapped[str | None] = mapped_column(String(30), nullable=True)
    client_address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mechanic_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    service_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtotal: Mapped[float] = mapped_column(Double, default=0)
    tax_rate: Mapped[float] = mapped_column(Double, default=0.19)
    tax: Mapped[float] = mapped_column(Double, default=0)
    total: Mapped[float] = mapped_column(Double, default=0)
    status: Mapped[str] = mapped_column(String(20), default="PENDIENTE")  # PENDIENTE | PAGADA | ANULADA
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["InvoiceItem"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    description: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[float] = mapped_column(Double)
    unit_price: Mapped[float] = mapped_column(Double)
    subtotal: Mapped[float] = mapped_column(Double)

    invoice: Mapped[Invoice] = relationship(back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount: Mapped[float] = mapped_column(Double)
    method: Mapped[str] = mapped_column(String(20))  # EFECTIVO | TARJETA | TRANSFERENCIA
    reference: Mapped[str] = mapped_column(String(60))
    paid_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    invoice: Mapped[Invoice] = relationship(back_populates="payments")
