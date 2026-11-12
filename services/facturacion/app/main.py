"""Microservicio de Facturación y Pagos."""
import os
import secrets
from datetime import datetime
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from common.app import create_app
from common.clients import call, notify
from common.db import cop, get_db, utcnow
from common.security import (ROLE_ADMIN, ROLE_CLIENTE, CurrentUser, get_current_user, internal_only,
                             require_roles)

from .models import Invoice, InvoiceItem, Payment

TAX_RATE = float(os.getenv("TAX_RATE", "0.19"))

app = create_app("Facturación y Pagos", "Generación de facturas de órdenes finalizadas y registro de pagos.")


# ---------------------------------------------------------------- esquemas
class ItemIn(BaseModel):
    description: str
    kind: str
    quantity: float
    unit_price: float


class InvoiceIn(BaseModel):
    order_id: int
    order_code: str
    customer_id: int
    client_user_id: int | None = None
    client_name: str = ""
    vehicle_label: str = ""
    mechanic_name: str | None = None
    service_name: str | None = None
    diagnosis: str | None = None
    items: list[ItemIn] = Field(min_length=1)


class ItemOut(ItemIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subtotal: float


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    amount: float
    method: str
    reference: str
    paid_by: str
    created_at: datetime


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: str
    order_id: int
    order_code: str
    customer_id: int
    client_user_id: int | None
    client_name: str
    vehicle_label: str
    client_email: str | None = None
    client_phone: str | None = None
    client_document: str | None = None
    client_address: str | None = None
    mechanic_name: str | None = None
    service_name: str | None = None
    diagnosis: str | None = None
    subtotal: float
    tax_rate: float
    tax: float
    total: float
    status: str
    issued_at: datetime
    paid_at: datetime | None
    items: list[ItemOut]
    payments: list[PaymentOut]


class PayIn(BaseModel):
    method: Literal["EFECTIVO", "TARJETA", "TRANSFERENCIA"]
    reference: str | None = None


def _get_invoice(db: Session, invoice_id: int, user: CurrentUser) -> Invoice:
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Factura no encontrada")
    if user.role == ROLE_CLIENTE and inv.client_user_id != user.id:
        raise HTTPException(403, "Esta factura no te pertenece")
    return inv


# ---------------------------------------------------------------- endpoints
@app.post("/internal/invoices", response_model=InvoiceOut, status_code=201, tags=["interno"])
def create_invoice(data: InvoiceIn, db: Session = Depends(get_db), _=Depends(internal_only)):
    """Genera la factura de una orden finalizada (idempotente por orden)."""
    existing = db.scalar(select(Invoice).where(Invoice.order_id == data.order_id))
    if existing:
        return existing
    inv = Invoice(**data.model_dump(exclude={"items"}), tax_rate=TAX_RATE)
    try:  # datos del cliente para la factura (si el servicio de clientes no responde, se factura igual)
        customer = call("clientes", "GET", f"/customers/{data.customer_id}")
        inv.client_email, inv.client_phone = customer.get("email"), customer.get("phone")
        inv.client_document, inv.client_address = customer.get("document"), customer.get("address")
    except HTTPException:
        pass
    subtotal = 0.0
    for it in data.items:
        line = round(it.quantity * it.unit_price, 2)
        subtotal += line
        inv.items.append(InvoiceItem(**it.model_dump(), subtotal=line))
    inv.subtotal = round(subtotal, 2)
    inv.tax = round(subtotal * TAX_RATE, 2)
    inv.total = round(inv.subtotal + inv.tax, 2)
    db.add(inv)
    db.flush()
    inv.number = f"FV-{inv.id:06d}"
    db.commit()
    db.refresh(inv)
    return inv


@app.get("/invoices", response_model=list[InvoiceOut], tags=["facturas"])
def list_invoices(status: str | None = None, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(require_roles(ROLE_CLIENTE, ROLE_ADMIN))):
    stmt = select(Invoice).order_by(Invoice.id.desc())
    if user.role == ROLE_CLIENTE:
        stmt = stmt.where(Invoice.client_user_id == user.id)
    if status:
        stmt = stmt.where(Invoice.status == status)
    return db.scalars(stmt).all()


@app.get("/invoices/{invoice_id}", response_model=InvoiceOut, tags=["facturas"])
def get_invoice(invoice_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    return _get_invoice(db, invoice_id, user)


@app.post("/invoices/{invoice_id}/pay", response_model=InvoiceOut, tags=["pagos"])
def pay_invoice(invoice_id: int, data: PayIn, db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_roles(ROLE_CLIENTE, ROLE_ADMIN))):
    """Registra el pago total de la factura (pasarela simulada)."""
    inv = _get_invoice(db, invoice_id, user)
    if inv.status != "PENDIENTE":
        raise HTTPException(409, f"La factura está {inv.status.lower()}")
    reference = data.reference or f"PAY-{secrets.token_hex(4).upper()}"
    inv.payments.append(Payment(amount=inv.total, method=data.method, reference=reference, paid_by=user.name))
    inv.status = "PAGADA"
    inv.paid_at = utcnow()
    db.commit()
    db.refresh(inv)

    note = f"Pago registrado: factura {inv.number} por {cop(inv.total)} ({data.method}, ref. {reference})"
    try:
        call("ordenes", "POST", f"/internal/orders/{inv.order_id}/payment", json={"note": note})
    except HTTPException:
        pass  # el pago ya quedó registrado; la bitácora es informativa
    notify(f"{inv.order_code}: pago recibido", note, user_id=inv.client_user_id, type="exito", order_id=inv.order_id)
    notify(f"{inv.order_code}: pago recibido", f"{inv.client_name} · {note}", role=ROLE_ADMIN,
           type="exito", order_id=inv.order_id)
    return inv


@app.post("/invoices/{invoice_id}/void", response_model=InvoiceOut, tags=["facturas"])
def void_invoice(invoice_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(require_roles(ROLE_ADMIN))):
    inv = _get_invoice(db, invoice_id, user)
    if inv.status != "PENDIENTE":
        raise HTTPException(409, "Solo se pueden anular facturas pendientes")
    inv.status = "ANULADA"
    db.commit()
    return inv
