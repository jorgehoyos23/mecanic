"""Microservicio de Órdenes de Trabajo y Reparaciones.

Es el orquestador del flujo principal:

    SOLICITADA → EN_DIAGNOSTICO → COTIZADA → APROBADA → EN_REPARACION → FINALIZADA → ENTREGADA
                                     └→ RECHAZADA (puede volver a cotizarse)
    (CANCELADA desde cualquier estado anterior a FINALIZADA)
"""
import os
from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from common.app import create_app
from common.clients import call, notify
from common.db import cop, get_db, utcnow
from common.security import (ROLE_ADMIN, ROLE_CLIENTE, ROLE_MECANICO, CurrentUser, get_current_user,
                             internal_only, require_roles)

from .models import OrderEvent, WorkOrder

app = create_app("Órdenes de Trabajo y Reparaciones",
                 "Solicitudes de servicio, diagnóstico, seguimiento de estado y bitácora de reparaciones.")

# ---------------------------------------------------------------- horario de atención
TZ = ZoneInfo(os.getenv("TALLER_TZ", "America/Bogota"))
OPEN_HOUR = int(os.getenv("HORA_APERTURA", "7"))    # 7:00 a. m.
CLOSE_HOUR = int(os.getenv("HORA_CIERRE", "22"))    # 10:00 p. m.


def _hour_label(h: int) -> str:
    return f"{(h - 1) % 12 + 1}:00 {'a. m.' if h < 12 else 'p. m.'}"


def schedule_status(now: datetime | None = None) -> dict:
    """Indica si el taller está recibiendo servicios y cuándo cambia el estado."""
    forced = os.getenv("HORARIO_FORZAR", "").lower()  # 'abierto' | 'cerrado' (solo para pruebas)
    now = now or datetime.now(TZ)
    is_open = forced == "abierto" or (forced != "cerrado" and OPEN_HOUR <= now.hour < CLOSE_HOUR)
    if is_open:
        change = now.replace(hour=CLOSE_HOUR, minute=0, second=0, microsecond=0)
        message = f"Estamos atendiendo. Recibimos solicitudes hasta las {_hour_label(CLOSE_HOUR)}"
    else:
        change = now.replace(hour=OPEN_HOUR, minute=0, second=0, microsecond=0)
        if now.hour >= CLOSE_HOUR:
            change += timedelta(days=1)
        message = (f"El taller está cerrado: no hay servicios disponibles entre las {_hour_label(CLOSE_HOUR)} "
                   f"y las {_hour_label(OPEN_HOUR)}; vuelve a partir de las {_hour_label(OPEN_HOUR)}")
    return {"open": is_open, "message": message, "now": now.isoformat(), "next_change": change.isoformat(),
            "open_hour": OPEN_HOUR, "close_hour": CLOSE_HOUR, "timezone": str(TZ),
            "hours_label": f"{_hour_label(OPEN_HOUR)} – {_hour_label(CLOSE_HOUR)}"}


@app.get("/schedule", tags=["horario"])
def get_schedule():
    """Horario de atención (público)."""
    return schedule_status()


STATUS_LABELS = {
    "SOLICITADA": "Solicitada",
    "EN_DIAGNOSTICO": "En diagnóstico",
    "COTIZADA": "Cotizada",
    "APROBADA": "Aprobada",
    "RECHAZADA": "Cotización rechazada",
    "EN_REPARACION": "En reparación",
    "FINALIZADA": "Finalizada",
    "ENTREGADA": "Entregada",
    "CANCELADA": "Cancelada",
}
# estados en los que los repuestos ya fueron descontados del inventario
STOCK_CONSUMED = {"APROBADA", "EN_REPARACION"}
CLIENT_CANCELLABLE = {"SOLICITADA", "EN_DIAGNOSTICO", "COTIZADA", "RECHAZADA"}
ADMIN_CANCELLABLE = CLIENT_CANCELLABLE | STOCK_CONSUMED


# ---------------------------------------------------------------- esquemas
class OrderIn(BaseModel):
    vehicle_id: int
    service_id: int | None = None
    kind: Literal["MANTENIMIENTO", "REPARACION"] = "MANTENIMIENTO"
    description: str = Field(min_length=5, description="Descripción del problema o del servicio solicitado")
    mileage: int | None = Field(default=None, ge=0)


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    note: str
    author_name: str
    author_role: str
    created_at: datetime


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    customer_id: int
    client_user_id: int | None
    client_name: str
    vehicle_id: int
    vehicle_label: str
    service_id: int | None
    service_name: str | None
    mechanic_id: int | None
    mechanic_name: str | None
    quote_id: int | None
    quote_total: float | None
    invoice_id: int | None
    kind: str
    description: str
    status: str
    status_label: str = ""
    diagnosis: str | None
    estimated_delivery: date | None
    mileage: int | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class OrderDetail(OrderOut):
    events: list[EventOut]
    quote: dict | None = None
    invoice: dict | None = None


class AssignIn(BaseModel):
    mechanic_id: int
    notes: str | None = None


class QuoteItemIn(BaseModel):
    kind: Literal["MANO_OBRA", "REPUESTO", "SERVICIO"]
    description: str | None = None
    part_id: int | None = None
    quantity: float = Field(default=1, gt=0)
    unit_price: float | None = Field(default=None, ge=0)


class DiagnosisIn(BaseModel):
    diagnosis: str = Field(min_length=5)
    estimated_delivery: date | None = None
    quote_notes: str | None = None
    items: list[QuoteItemIn] = Field(min_length=1, description="Ítems de la cotización")


class DecisionIn(BaseModel):
    approved: bool
    comment: str | None = None


class StatusIn(BaseModel):
    status: Literal["EN_REPARACION", "FINALIZADA", "ENTREGADA", "CANCELADA"]
    note: str | None = None


class NoteIn(BaseModel):
    note: str = Field(min_length=3)


# ---------------------------------------------------------------- utilidades
def _out(o: WorkOrder) -> OrderOut:
    data = OrderOut.model_validate(o)
    data.status_label = STATUS_LABELS.get(o.status, o.status)
    return data


def _detail(o: WorkOrder, quote: dict | None, invoice: dict | None) -> OrderDetail:
    return OrderDetail(**_out(o).model_dump(), events=[EventOut.model_validate(e) for e in o.events],
                       quote=quote, invoice=invoice)


def _event(o: WorkOrder, status: str, note: str, user: CurrentUser):
    o.events.append(OrderEvent(status=status, note=note, author_name=user.name, author_role=user.role))


def _set_status(o: WorkOrder, status: str, note: str, user: CurrentUser):
    o.status = status
    o.updated_at = utcnow()
    _event(o, status, note, user)


def _get_order(db: Session, order_id: int, user: CurrentUser) -> WorkOrder:
    o = db.get(WorkOrder, order_id)
    if not o:
        raise HTTPException(404, "Orden no encontrada")
    if user.role == ROLE_CLIENTE and o.client_user_id != user.id:
        raise HTTPException(403, "Esta orden no te pertenece")
    if user.role == ROLE_MECANICO and o.mechanic_user_id != user.id:
        raise HTTPException(403, "Esta orden no está asignada a ti")
    return o


def _require_status(o: WorkOrder, *allowed: str):
    if o.status not in allowed:
        raise HTTPException(409, f"La orden está en estado '{STATUS_LABELS[o.status]}' y no permite esta acción")


def _notify_client(o: WorkOrder, title: str, message: str, type: str = "info"):
    notify(f"{o.code}: {title}", message, user_id=o.client_user_id, type=type, order_id=o.id)


# ---------------------------------------------------------------- consultas
@app.get("/orders", response_model=list[OrderOut], tags=["órdenes"])
def list_orders(status: str | None = None, vehicle_id: int | None = None, db: Session = Depends(get_db),
                user: CurrentUser = Depends(get_current_user)):
    """El cliente ve sus órdenes, el mecánico las asignadas y el administrador todas."""
    stmt = select(WorkOrder).order_by(WorkOrder.id.desc())
    if user.role == ROLE_CLIENTE:
        stmt = stmt.where(WorkOrder.client_user_id == user.id)
    elif user.role == ROLE_MECANICO:
        stmt = stmt.where(WorkOrder.mechanic_user_id == user.id)
    if status:
        stmt = stmt.where(WorkOrder.status.in_(status.split(",")))
    if vehicle_id:
        stmt = stmt.where(WorkOrder.vehicle_id == vehicle_id)
    return [_out(o) for o in db.scalars(stmt)]


@app.get("/orders/stats", tags=["órdenes"])
def stats(db: Session = Depends(get_db), _=Depends(require_roles(ROLE_ADMIN))):
    rows = db.execute(select(WorkOrder.status, func.count(WorkOrder.id)).group_by(WorkOrder.status)).all()
    by_status = {s: 0 for s in STATUS_LABELS}
    by_status.update(dict(rows))
    return {"total": sum(by_status.values()), "by_status": by_status, "labels": STATUS_LABELS}


@app.get("/orders/{order_id}", response_model=OrderDetail, tags=["órdenes"])
def get_order(order_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    """Detalle con bitácora, diagnóstico, cotización y factura (consultadas a sus microservicios)."""
    o = _get_order(db, order_id, user)
    quote = invoice = None
    if o.quote_id:
        try:
            quote = call("servicios", "GET", f"/quotes/{o.quote_id}")
        except HTTPException:
            quote = None
    if o.invoice_id:
        try:
            invoice = call("facturacion", "GET", f"/invoices/{o.invoice_id}")
        except HTTPException:
            invoice = None
    return _detail(o, quote, invoice)


# ---------------------------------------------------------------- flujo
@app.post("/orders", response_model=OrderOut, status_code=201, tags=["flujo"])
def create_order(data: OrderIn, db: Session = Depends(get_db),
                 user: CurrentUser = Depends(require_roles(ROLE_CLIENTE, ROLE_ADMIN))):
    """El cliente solicita un servicio de mantenimiento o reparación para uno de sus vehículos.

    Solo se reciben solicitudes dentro del horario de atención del taller.
    """
    horario = schedule_status()
    if not horario["open"]:
        raise HTTPException(409, horario["message"])
    vehicle = call("clientes", "GET", f"/vehicles/{data.vehicle_id}")
    if user.role == ROLE_CLIENTE and vehicle["owner_user_id"] != user.id:
        raise HTTPException(403, "El vehículo no te pertenece")
    service = call("servicios", "GET", f"/catalog/{data.service_id}") if data.service_id else None

    o = WorkOrder(
        customer_id=vehicle["customer_id"], client_user_id=vehicle["owner_user_id"],
        client_name=vehicle.get("owner_name") or "",
        vehicle_id=vehicle["id"],
        vehicle_label=f"{vehicle['brand']} {vehicle['model']} {vehicle['year']} · {vehicle['plate']}",
        service_id=service["id"] if service else None, service_name=service["name"] if service else None,
        kind=data.kind if not service or service["category"] == "DIAGNOSTICO" else service["category"],
        description=data.description, mileage=data.mileage,
    )
    db.add(o)
    db.flush()
    o.code = f"OT-{utcnow():%Y}-{o.id:05d}"
    _event(o, "SOLICITADA", "Solicitud de servicio registrada", user)
    db.commit()

    _notify_client(o, "Solicitud recibida",
                   f"Recibimos tu solicitud para {o.vehicle_label}. Pronto asignaremos un mecánico.", "exito")
    notify("Nueva solicitud de servicio", f"{o.code} · {o.client_name} · {o.vehicle_label}",
           role=ROLE_ADMIN, order_id=o.id)
    return _out(o)


@app.post("/orders/{order_id}/assign", response_model=OrderOut, tags=["flujo"])
def assign_mechanic(order_id: int, data: AssignIn, db: Session = Depends(get_db),
                    user: CurrentUser = Depends(require_roles(ROLE_ADMIN))):
    """Asigna (o reasigna) el mecánico responsable. Una orden SOLICITADA pasa a EN_DIAGNOSTICO."""
    o = _get_order(db, order_id, user)
    _require_status(o, "SOLICITADA", "EN_DIAGNOSTICO", "COTIZADA", "RECHAZADA", "APROBADA", "EN_REPARACION")
    a = call("mecanicos", "POST", "/assignments", json={"order_id": o.id, "mechanic_id": data.mechanic_id,
                                                        "notes": data.notes})
    o.mechanic_id, o.mechanic_user_id, o.mechanic_name = a["mechanic_id"], a["mechanic_user_id"], a["mechanic_name"]
    if o.status == "SOLICITADA":
        _set_status(o, "EN_DIAGNOSTICO", f"Asignado a {o.mechanic_name}. Inicia el diagnóstico.", user)
    else:
        _event(o, o.status, f"Orden reasignada a {o.mechanic_name}", user)
    db.commit()

    _notify_client(o, "Mecánico asignado", f"{o.mechanic_name} está revisando tu vehículo.")
    notify("Nueva orden asignada", f"{o.code} · {o.vehicle_label}: {o.description}",
           user_id=o.mechanic_user_id, order_id=o.id)
    return _out(o)


@app.post("/orders/{order_id}/diagnosis", response_model=OrderDetail, tags=["flujo"])
def register_diagnosis(order_id: int, data: DiagnosisIn, db: Session = Depends(get_db),
                       user: CurrentUser = Depends(require_roles(ROLE_MECANICO, ROLE_ADMIN))):
    """El mecánico registra el diagnóstico y se genera la cotización en el servicio de Cotizaciones."""
    o = _get_order(db, order_id, user)
    _require_status(o, "EN_DIAGNOSTICO", "RECHAZADA", "COTIZADA")
    quote = call("servicios", "POST", "/quotes", json={
        "order_id": o.id, "notes": data.quote_notes, "items": [i.model_dump() for i in data.items]})
    o.diagnosis = data.diagnosis
    o.estimated_delivery = data.estimated_delivery
    o.quote_id, o.quote_total = quote["id"], quote["total"]
    _set_status(o, "COTIZADA", f"Diagnóstico: {data.diagnosis}", user)
    db.commit()

    _notify_client(o, "Diagnóstico y cotización disponibles",
                   f"Total cotizado: {cop(quote['total'])}. Revisa y aprueba la cotización para continuar.", "alerta")
    return get_order(order_id, db, user)


@app.post("/orders/{order_id}/quote-decision", response_model=OrderDetail, tags=["flujo"])
def quote_decision(order_id: int, data: DecisionIn, db: Session = Depends(get_db),
                   user: CurrentUser = Depends(require_roles(ROLE_CLIENTE, ROLE_ADMIN))):
    """El cliente aprueba o rechaza la cotización. Al aprobar se descuentan los repuestos del inventario."""
    o = _get_order(db, order_id, user)
    _require_status(o, "COTIZADA")
    if data.approved:
        quote = call("servicios", "GET", f"/quotes/{o.quote_id}")
        parts = [{"part_id": i["part_id"], "quantity": max(1, round(i["quantity"]))}
                 for i in quote["items"] if i["kind"] == "REPUESTO" and i["part_id"]]
        if parts:
            call("inventario", "POST", "/internal/consume", json={"order_id": o.id, "items": parts})
        try:
            call("servicios", "POST", f"/internal/quotes/{o.quote_id}/decision", json={"approved": True})
        except HTTPException:
            if parts:  # compensación (patrón saga): devolver el stock
                call("inventario", "POST", "/internal/release", json={"order_id": o.id})
            raise
        _set_status(o, "APROBADA", data.comment or "El cliente aprobó la cotización", user)
        msg_title, msg_type = "Cotización aprobada", "exito"
    else:
        call("servicios", "POST", f"/internal/quotes/{o.quote_id}/decision", json={"approved": False})
        _set_status(o, "RECHAZADA", data.comment or "El cliente rechazó la cotización", user)
        msg_title, msg_type = "Cotización rechazada", "alerta"
    db.commit()

    _notify_client(o, msg_title, "Registramos tu decisión sobre la cotización.", msg_type)
    notify(f"{o.code}: {msg_title}", data.comment or o.vehicle_label, user_id=o.mechanic_user_id,
           type=msg_type, order_id=o.id)
    notify(f"{o.code}: {msg_title}", f"{o.client_name} · {o.vehicle_label}", role=ROLE_ADMIN,
           type=msg_type, order_id=o.id)
    return get_order(order_id, db, user)


@app.post("/orders/{order_id}/status", response_model=OrderDetail, tags=["flujo"])
def change_status(order_id: int, data: StatusIn, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(get_current_user)):
    """Avanza la orden: EN_REPARACION, FINALIZADA (genera factura), ENTREGADA (requiere pago) o CANCELADA."""
    o = _get_order(db, order_id, user)
    target, note = data.status, data.note

    if target == "EN_REPARACION":
        if user.role not in (ROLE_MECANICO, ROLE_ADMIN):
            raise HTTPException(403, "Solo el mecánico o el administrador pueden iniciar la reparación")
        _require_status(o, "APROBADA")
        _set_status(o, target, note or "Inició la reparación", user)
        db.commit()
        _notify_client(o, "Reparación iniciada", note or f"{o.mechanic_name} comenzó a trabajar en tu vehículo.")

    elif target == "FINALIZADA":
        if user.role not in (ROLE_MECANICO, ROLE_ADMIN):
            raise HTTPException(403, "Solo el mecánico o el administrador pueden finalizar la orden")
        _require_status(o, "EN_REPARACION")
        quote = call("servicios", "GET", f"/quotes/{o.quote_id}")
        invoice = call("facturacion", "POST", "/internal/invoices", json={
            "order_id": o.id, "order_code": o.code, "customer_id": o.customer_id,
            "client_user_id": o.client_user_id, "client_name": o.client_name, "vehicle_label": o.vehicle_label,
            "mechanic_name": o.mechanic_name, "service_name": o.service_name, "diagnosis": o.diagnosis,
            "items": [{"description": i["description"], "kind": i["kind"], "quantity": i["quantity"],
                       "unit_price": i["unit_price"]} for i in quote["items"]]})
        o.invoice_id = invoice["id"]
        o.completed_at = utcnow()
        _set_status(o, target, note or "Trabajo terminado. Vehículo listo para entrega.", user)
        db.commit()
        call("mecanicos", "POST", f"/internal/orders/{o.id}/release")
        _notify_client(o, "¡Tu vehículo está listo!",
                       f"El servicio finalizó. Se generó la factura {invoice['number']} por {cop(invoice['total'])}.", "exito")
        notify(f"{o.code}: servicio finalizado", f"Factura {invoice['number']} generada.", role=ROLE_ADMIN,
               order_id=o.id)

    elif target == "ENTREGADA":
        if user.role != ROLE_ADMIN:
            raise HTTPException(403, "Solo el administrador registra la entrega")
        _require_status(o, "FINALIZADA")
        invoice = call("facturacion", "GET", f"/invoices/{o.invoice_id}")
        if invoice["status"] != "PAGADA":
            raise HTTPException(409, "La factura debe estar pagada antes de entregar el vehículo")
        _set_status(o, target, note or "Vehículo entregado al cliente", user)
        db.commit()
        _notify_client(o, "Vehículo entregado", "¡Gracias por confiar en nuestro taller!", "exito")

    elif target == "CANCELADA":
        if user.role == ROLE_CLIENTE:
            _require_status(o, *CLIENT_CANCELLABLE)
        elif user.role == ROLE_ADMIN:
            _require_status(o, *ADMIN_CANCELLABLE)
        else:
            raise HTTPException(403, "No puedes cancelar órdenes")
        if o.status in STOCK_CONSUMED:
            call("inventario", "POST", "/internal/release", json={"order_id": o.id})
        _set_status(o, target, note or "Orden cancelada", user)
        db.commit()
        if o.mechanic_id:
            call("mecanicos", "POST", f"/internal/orders/{o.id}/release")
            notify(f"{o.code}: orden cancelada", note or o.vehicle_label, user_id=o.mechanic_user_id,
                   type="alerta", order_id=o.id)
        _notify_client(o, "Orden cancelada", note or "La orden de trabajo fue cancelada.", "alerta")

    return get_order(order_id, db, user)


@app.post("/orders/{order_id}/notes", response_model=OrderDetail, tags=["flujo"])
def add_progress_note(order_id: int, data: NoteIn, db: Session = Depends(get_db),
                      user: CurrentUser = Depends(require_roles(ROLE_MECANICO, ROLE_ADMIN))):
    """Registra un avance en la bitácora y notifica al cliente."""
    o = _get_order(db, order_id, user)
    _require_status(o, "EN_DIAGNOSTICO", "COTIZADA", "APROBADA", "EN_REPARACION", "RECHAZADA")
    _event(o, o.status, data.note, user)
    o.updated_at = utcnow()
    db.commit()
    _notify_client(o, "Nuevo avance en tu orden", data.note)
    return get_order(order_id, db, user)


@app.post("/internal/orders/{order_id}/payment", tags=["interno"])
def payment_registered(order_id: int, data: NoteIn, db: Session = Depends(get_db),
                       user: CurrentUser = Depends(internal_only)):
    """Facturación avisa que la factura de la orden fue pagada (se registra en la bitácora)."""
    o = db.get(WorkOrder, order_id)
    if not o:
        raise HTTPException(404, "Orden no encontrada")
    _event(o, o.status, data.note, user)
    db.commit()
    return {"ok": True}
