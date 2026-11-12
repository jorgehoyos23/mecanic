"""Microservicio de Inventario de Repuestos."""
from datetime import datetime
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from common.app import create_app
from common.clients import notify
from common.db import get_db
from common.security import ROLE_ADMIN, STAFF, internal_only, require_roles

from .fotos import ANTERIORES, FOTOS
from .models import Part, StockMovement

DEMO_PARTS = [
    ("ACE-5W30-1L", "Aceite sintético 5W-30 (1 L)", "Mobil", "Lubricantes", 38000, 40, 10),
    ("FIL-ACE-001", "Filtro de aceite", "Bosch", "Filtros", 25000, 25, 5),
    ("FIL-AIR-001", "Filtro de aire", "Mann", "Filtros", 42000, 15, 4),
    ("PAS-DEL-001", "Pastillas de freno delanteras", "Brembo", "Frenos", 135000, 12, 4),
    ("DIS-DEL-001", "Disco de freno delantero", "Brembo", "Frenos", 210000, 6, 2),
    ("LIQ-FRE-DOT4", "Líquido de frenos DOT4 (500 ml)", "Bosch", "Frenos", 28000, 20, 5),
    ("BAT-12V-60A", "Batería 12V 60Ah", "MAC", "Eléctrico", 420000, 5, 2),
    ("BUJ-IRI-001", "Bujía de iridio", "NGK", "Encendido", 48000, 32, 8),
    ("COR-DIS-001", "Correa de distribución", "Gates", "Motor", 185000, 4, 2),
    ("AMO-DEL-001", "Amortiguador delantero", "Monroe", "Suspensión", 260000, 3, 2),
]


def seed(db: Session):
    if not db.scalar(select(func.count(Part.id))):
        for sku, name, brand, cat, price, stock, min_stock in DEMO_PARTS:
            p = Part(sku=sku, name=name, brand=brand, category=cat, unit_price=price, stock=stock, min_stock=min_stock)
            p.movements.append(StockMovement(type="ENTRADA", quantity=stock, note="Inventario inicial"))
            db.add(p)
        db.commit()
    # fotos reales para los repuestos de demostración que aún no tienen imagen
    for p in db.scalars(select(Part).where(or_(Part.image_url.is_(None), Part.image_url.in_(ANTERIORES)),
                                          Part.sku.in_(FOTOS))):
        p.image_url, p.image_credit, p.image_source = FOTOS[p.sku]
    db.commit()


app = create_app("Inventario de Repuestos", "Catálogo de repuestos, existencias y movimientos de stock.", seed=seed)


# ---------------------------------------------------------------- esquemas
class PartIn(BaseModel):
    sku: str = Field(min_length=2)
    name: str = Field(min_length=2)
    brand: str | None = None
    category: str = "General"
    unit_price: float = Field(ge=0)
    stock: int = Field(default=0, ge=0)
    min_stock: int = Field(default=0, ge=0)
    image_url: str | None = None
    image_credit: str | None = None
    image_source: str | None = None


class PartUpdate(BaseModel):
    name: str | None = None
    brand: str | None = None
    category: str | None = None
    unit_price: float | None = Field(default=None, ge=0)
    min_stock: int | None = Field(default=None, ge=0)
    active: bool | None = None
    image_url: str | None = None
    image_credit: str | None = None
    image_source: str | None = None


class PartOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    name: str
    brand: str | None
    category: str
    unit_price: float
    stock: int
    min_stock: int
    active: bool
    image_url: str | None = None
    image_credit: str | None = None
    image_source: str | None = None
    low_stock: bool = False


class StockIn(BaseModel):
    type: Literal["ENTRADA", "AJUSTE"] = "ENTRADA"
    quantity: int = Field(description="ENTRADA: cantidad positiva. AJUSTE: puede ser negativa.")
    note: str | None = None


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    part_id: int
    type: str
    quantity: int
    order_id: int | None
    note: str | None
    created_at: datetime


class ConsumeItem(BaseModel):
    part_id: int
    quantity: int = Field(gt=0)


class ConsumeIn(BaseModel):
    order_id: int
    items: list[ConsumeItem]


class OrderRef(BaseModel):
    order_id: int


def _part_out(p: Part) -> PartOut:
    out = PartOut.model_validate(p)
    out.low_stock = p.stock <= p.min_stock
    return out


def _get_part(db: Session, part_id: int, lock: bool = False) -> Part:
    stmt = select(Part).where(Part.id == part_id)
    if lock:
        stmt = stmt.with_for_update()
    p = db.scalar(stmt)
    if not p:
        raise HTTPException(404, f"Repuesto {part_id} no encontrado")
    return p


def _alert_low_stock(parts: list[Part]):
    for p in parts:
        if p.stock <= p.min_stock:
            notify("Stock bajo de repuesto",
                   f"{p.name} ({p.sku}) tiene {p.stock} unidades (mínimo {p.min_stock}).",
                   role=ROLE_ADMIN, type="alerta")


# ---------------------------------------------------------------- repuestos
@app.get("/parts", response_model=list[PartOut], tags=["repuestos"])
def list_parts(q: str | None = None, category: str | None = None, low_stock: bool = False,
               db: Session = Depends(get_db), _=Depends(require_roles(*STAFF))):
    stmt = select(Part).where(Part.active.is_(True)).order_by(Part.category, Part.name)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Part.name.ilike(like), Part.sku.ilike(like), Part.brand.ilike(like)))
    if category:
        stmt = stmt.where(Part.category == category)
    if low_stock:
        stmt = stmt.where(Part.stock <= Part.min_stock)
    return [_part_out(p) for p in db.scalars(stmt)]


@app.get("/parts/{part_id}", response_model=PartOut, tags=["repuestos"])
def get_part(part_id: int, db: Session = Depends(get_db), _=Depends(require_roles(*STAFF))):
    return _part_out(_get_part(db, part_id))


@app.post("/parts", response_model=PartOut, status_code=201, tags=["repuestos"])
def create_part(data: PartIn, db: Session = Depends(get_db), _=Depends(require_roles(ROLE_ADMIN))):
    sku = data.sku.strip().upper()
    if db.scalar(select(Part).where(Part.sku == sku)):
        raise HTTPException(409, f"Ya existe un repuesto con SKU {sku}")
    p = Part(**data.model_dump(exclude={"sku"}), sku=sku)
    if data.stock:
        p.movements.append(StockMovement(type="ENTRADA", quantity=data.stock, note="Stock inicial"))
    db.add(p)
    db.commit()
    return _part_out(p)


@app.put("/parts/{part_id}", response_model=PartOut, tags=["repuestos"])
def update_part(part_id: int, data: PartUpdate, db: Session = Depends(get_db), _=Depends(require_roles(ROLE_ADMIN))):
    p = _get_part(db, part_id)
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    db.commit()
    return _part_out(p)


@app.post("/parts/{part_id}/stock", response_model=PartOut, tags=["repuestos"])
def add_stock(part_id: int, data: StockIn, db: Session = Depends(get_db), _=Depends(require_roles(ROLE_ADMIN))):
    p = _get_part(db, part_id, lock=True)
    if data.type == "ENTRADA" and data.quantity <= 0:
        raise HTTPException(422, "La entrada debe ser una cantidad positiva")
    if p.stock + data.quantity < 0:
        raise HTTPException(409, "El ajuste dejaría el stock en negativo")
    p.stock += data.quantity
    db.add(StockMovement(part_id=p.id, type=data.type, quantity=data.quantity, note=data.note))
    db.commit()
    return _part_out(p)


@app.get("/movements", response_model=list[MovementOut], tags=["repuestos"])
def list_movements(part_id: int | None = None, order_id: int | None = None, db: Session = Depends(get_db),
                   _=Depends(require_roles(*STAFF))):
    stmt = select(StockMovement).order_by(StockMovement.created_at.desc()).limit(200)
    if part_id:
        stmt = stmt.where(StockMovement.part_id == part_id)
    if order_id:
        stmt = stmt.where(StockMovement.order_id == order_id)
    return db.scalars(stmt).all()


# ---------------------------------------------------------------- interno
@app.post("/internal/consume", response_model=list[PartOut], tags=["interno"])
def consume(data: ConsumeIn, db: Session = Depends(get_db), _=Depends(internal_only)):
    """Descuenta del stock los repuestos de una orden aprobada (todo o nada)."""
    totals: dict[int, int] = {}
    for it in data.items:
        totals[it.part_id] = totals.get(it.part_id, 0) + it.quantity
    parts = {pid: _get_part(db, pid, lock=True) for pid in sorted(totals)}
    missing = [f"{parts[pid].name} (disponible {parts[pid].stock}, requerido {qty})"
               for pid, qty in totals.items() if parts[pid].stock < qty]
    if missing:
        db.rollback()
        raise HTTPException(409, "Stock insuficiente: " + "; ".join(missing))
    for pid, qty in totals.items():
        parts[pid].stock -= qty
        db.add(StockMovement(part_id=pid, type="SALIDA", quantity=-qty, order_id=data.order_id,
                             note=f"Consumo orden {data.order_id}"))
    db.commit()
    _alert_low_stock(list(parts.values()))
    return [_part_out(p) for p in parts.values()]


@app.post("/internal/release", tags=["interno"])
def release(data: OrderRef, db: Session = Depends(get_db), _=Depends(internal_only)):
    """Devuelve al stock los repuestos de una orden cancelada (compensación)."""
    net = dict(db.execute(select(StockMovement.part_id, func.sum(StockMovement.quantity))
                          .where(StockMovement.order_id == data.order_id)
                          .group_by(StockMovement.part_id)).all())
    returned = 0
    for pid, qty in net.items():
        if qty < 0:
            p = _get_part(db, pid, lock=True)
            p.stock += -qty
            db.add(StockMovement(part_id=pid, type="DEVOLUCION", quantity=-qty, order_id=data.order_id,
                                 note=f"Devolución por cancelación de orden {data.order_id}"))
            returned += -qty
    db.commit()
    return {"returned_units": returned}
