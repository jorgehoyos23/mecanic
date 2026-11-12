"""Microservicio de Servicios y Cotizaciones."""
from datetime import datetime
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from common.app import create_app
from common.clients import call
from common.db import get_db, utcnow
from common.security import ROLE_ADMIN, STAFF, CurrentUser, internal_only, require_roles

from .models import Quote, QuoteItem, ServiceCatalog

Category = Literal["MANTENIMIENTO", "REPARACION", "DIAGNOSTICO"]

DEMO_CATALOG = [
    ("Cambio de aceite y filtro", "Cambio de aceite de motor y filtro de aceite.", "MANTENIMIENTO", 120000, 1),
    ("Mantenimiento preventivo 10.000 km", "Revisión de niveles, filtros, frenos, luces y suspensión.", "MANTENIMIENTO", 280000, 3),
    ("Alineación y balanceo", "Alineación de dirección y balanceo de las cuatro llantas.", "MANTENIMIENTO", 90000, 1.5),
    ("Revisión y cambio de frenos", "Inspección de pastillas, discos y líquido de frenos.", "REPARACION", 150000, 2),
    ("Reparación de motor", "Diagnóstico y reparación de fallas mecánicas del motor.", "REPARACION", 450000, 8),
    ("Sistema eléctrico y batería", "Revisión de alternador, batería, arranque y cableado.", "REPARACION", 110000, 2),
    ("Diagnóstico general por escáner", "Lectura de códigos de falla y revisión general del vehículo.", "DIAGNOSTICO", 70000, 1),
]


def seed(db: Session):
    if not db.scalar(select(func.count(ServiceCatalog.id))):
        for name, desc, cat, price, hours in DEMO_CATALOG:
            db.add(ServiceCatalog(name=name, description=desc, category=cat, base_price=price, estimated_hours=hours))
        db.commit()


app = create_app("Servicios y Cotizaciones", "Catálogo de servicios del taller y cotizaciones de las órdenes.", seed=seed)


# ---------------------------------------------------------------- esquemas
class CatalogIn(BaseModel):
    name: str = Field(min_length=3)
    description: str = ""
    category: Category = "MANTENIMIENTO"
    base_price: float = Field(ge=0)
    estimated_hours: float = Field(default=1, gt=0)
    active: bool = True


class CatalogOut(CatalogIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class QuoteItemIn(BaseModel):
    kind: Literal["MANO_OBRA", "REPUESTO", "SERVICIO"]
    description: str | None = None
    part_id: int | None = None
    quantity: float = Field(default=1, gt=0)
    unit_price: float | None = Field(default=None, ge=0)


class QuoteIn(BaseModel):
    order_id: int
    notes: str | None = None
    items: list[QuoteItemIn] = Field(min_length=1)


class QuoteItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    description: str
    part_id: int | None
    quantity: float
    unit_price: float
    subtotal: float


class QuoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_id: int
    status: str
    notes: str | None
    labor_total: float
    parts_total: float
    total: float
    created_by: str
    created_at: datetime
    decided_at: datetime | None
    items: list[QuoteItemOut]


class DecisionIn(BaseModel):
    approved: bool


# ---------------------------------------------------------------- catálogo
@app.get("/catalog", response_model=list[CatalogOut], tags=["catálogo"])
def list_catalog(category: Category | None = None, include_inactive: bool = False, db: Session = Depends(get_db)):
    """Catálogo público de servicios del taller."""
    stmt = select(ServiceCatalog).order_by(ServiceCatalog.category, ServiceCatalog.name)
    if category:
        stmt = stmt.where(ServiceCatalog.category == category)
    if not include_inactive:
        stmt = stmt.where(ServiceCatalog.active.is_(True))
    return db.scalars(stmt).all()


@app.get("/catalog/{service_id}", response_model=CatalogOut, tags=["catálogo"])
def get_service(service_id: int, db: Session = Depends(get_db)):
    s = db.get(ServiceCatalog, service_id)
    if not s:
        raise HTTPException(404, "Servicio no encontrado")
    return s


@app.post("/catalog", response_model=CatalogOut, status_code=201, tags=["catálogo"])
def create_service(data: CatalogIn, db: Session = Depends(get_db), _=Depends(require_roles(ROLE_ADMIN))):
    s = ServiceCatalog(**data.model_dump())
    db.add(s)
    db.commit()
    return s


@app.put("/catalog/{service_id}", response_model=CatalogOut, tags=["catálogo"])
def update_service(service_id: int, data: CatalogIn, db: Session = Depends(get_db),
                   _=Depends(require_roles(ROLE_ADMIN))):
    s = db.get(ServiceCatalog, service_id)
    if not s:
        raise HTTPException(404, "Servicio no encontrado")
    for k, v in data.model_dump().items():
        setattr(s, k, v)
    db.commit()
    return s


# ---------------------------------------------------------------- cotizaciones
@app.post("/quotes", response_model=QuoteOut, status_code=201, tags=["cotizaciones"])
def create_quote(data: QuoteIn, db: Session = Depends(get_db), user: CurrentUser = Depends(require_roles(*STAFF))):
    """Crea la cotización de una orden. Los repuestos toman nombre y precio del inventario.

    Si la orden ya tenía una cotización pendiente, esta queda como REEMPLAZADA.
    """
    quote = Quote(order_id=data.order_id, notes=data.notes, created_by=user.name)
    labor = parts = 0.0
    for it in data.items:
        description, price = it.description, it.unit_price
        if it.kind == "REPUESTO":
            if not it.part_id:
                raise HTTPException(422, "Los ítems de tipo REPUESTO requieren part_id")
            part = call("inventario", "GET", f"/parts/{it.part_id}")
            description = description or f"{part['name']} ({part['sku']})"
            price = part["unit_price"] if price is None else price
        if not description:
            raise HTTPException(422, "Cada ítem necesita una descripción")
        price = price or 0.0
        subtotal = round(price * it.quantity, 2)
        if it.kind == "REPUESTO":
            parts += subtotal
        else:
            labor += subtotal
        quote.items.append(QuoteItem(kind=it.kind, description=description, part_id=it.part_id,
                                     quantity=it.quantity, unit_price=price, subtotal=subtotal))
    quote.labor_total, quote.parts_total, quote.total = round(labor, 2), round(parts, 2), round(labor + parts, 2)

    db.execute(update(Quote).where(Quote.order_id == data.order_id, Quote.status == "PENDIENTE")
               .values(status="REEMPLAZADA"))
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote


@app.get("/quotes", response_model=list[QuoteOut], tags=["cotizaciones"])
def list_quotes(order_id: int | None = None, status: str | None = None, db: Session = Depends(get_db),
                _=Depends(require_roles(*STAFF))):
    stmt = select(Quote).order_by(Quote.created_at.desc())
    if order_id:
        stmt = stmt.where(Quote.order_id == order_id)
    if status:
        stmt = stmt.where(Quote.status == status)
    return db.scalars(stmt).all()


@app.get("/quotes/{quote_id}", response_model=QuoteOut, tags=["cotizaciones"])
def get_quote(quote_id: int, db: Session = Depends(get_db), _=Depends(require_roles(*STAFF))):
    q = db.get(Quote, quote_id)
    if not q:
        raise HTTPException(404, "Cotización no encontrada")
    return q


@app.post("/internal/quotes/{quote_id}/decision", response_model=QuoteOut, tags=["interno"])
def decide_quote(quote_id: int, data: DecisionIn, db: Session = Depends(get_db), _=Depends(internal_only)):
    """Registra la aprobación o rechazo del cliente (lo invoca el servicio de Órdenes)."""
    q = db.get(Quote, quote_id)
    if not q:
        raise HTTPException(404, "Cotización no encontrada")
    if q.status != "PENDIENTE":
        raise HTTPException(409, f"La cotización ya está en estado {q.status}")
    q.status = "APROBADA" if data.approved else "RECHAZADA"
    q.decided_at = utcnow()
    db.commit()
    return q
