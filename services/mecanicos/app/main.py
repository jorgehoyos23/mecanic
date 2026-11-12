"""Microservicio de Mecánicos y Asignaciones."""
import logging
import time
from datetime import datetime

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from common.app import create_app
from common.clients import call
from common.db import get_db, utcnow
from common.security import (ROLE_ADMIN, ROLE_MECANICO, STAFF, CurrentUser, internal_only, require_roles)

from .models import Assignment, Mechanic

log = logging.getLogger("mecanicos")

DEMO_MECHANICS = [
    {"full_name": "Carlos Ramírez", "email": "mecanico@taller.com", "specialty": "Motor y transmisión", "phone": "3001112233"},
    {"full_name": "Laura Gómez", "email": "laura@taller.com", "specialty": "Frenos y suspensión", "phone": "3004445566"},
    {"full_name": "Andrés Torres", "email": "andres@taller.com", "specialty": "Sistema eléctrico", "phone": "3007778899"},
]


def seed(db: Session):
    """Crea mecánicos de demostración (con su cuenta en el servicio de autenticación)."""
    if db.scalar(select(func.count(Mechanic.id))):
        return
    for attempt in range(20):
        try:
            for m in DEMO_MECHANICS:
                user = call("auth", "POST", "/internal/users", params={"get_or_create": "true"},
                            json={**m, "password": "mecanico123", "role": ROLE_MECANICO})
                if not db.scalar(select(Mechanic).where(Mechanic.user_id == user["id"])):
                    db.add(Mechanic(user_id=user["id"], **m))
            db.commit()
            log.info("Mecánicos de demostración creados")
            return
        except HTTPException as exc:
            db.rollback()
            log.warning("Esperando al servicio de autenticación (%s): %s", attempt + 1, exc.detail)
            time.sleep(3)


app = create_app("Mecánicos y Asignaciones", "Gestión del personal técnico y su asignación a órdenes de trabajo.",
                 seed=seed, background_seed=True)


# ---------------------------------------------------------------- esquemas
class MechanicIn(BaseModel):
    full_name: str = Field(min_length=3)
    email: str
    password: str = Field(min_length=6)
    phone: str | None = None
    specialty: str = "General"


class MechanicUpdate(BaseModel):
    phone: str | None = None
    specialty: str | None = None
    active: bool | None = None


class MechanicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    full_name: str
    email: str
    phone: str | None
    specialty: str
    active: bool
    created_at: datetime
    active_assignments: int = 0


class AssignmentIn(BaseModel):
    order_id: int
    mechanic_id: int
    notes: str | None = None


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_id: int
    mechanic_id: int
    notes: str | None
    active: bool
    assigned_at: datetime
    released_at: datetime | None
    mechanic_name: str = ""
    mechanic_user_id: int | None = None


def _mechanic_out(db: Session, m: Mechanic) -> MechanicOut:
    out = MechanicOut.model_validate(m)
    out.active_assignments = db.scalar(select(func.count(Assignment.id)).where(
        Assignment.mechanic_id == m.id, Assignment.active.is_(True))) or 0
    return out


def _assignment_out(a: Assignment) -> AssignmentOut:
    out = AssignmentOut.model_validate(a)
    out.mechanic_name = a.mechanic.full_name
    out.mechanic_user_id = a.mechanic.user_id
    return out


# ---------------------------------------------------------------- mecánicos
@app.get("/mechanics", response_model=list[MechanicOut], tags=["mecánicos"])
def list_mechanics(active: bool | None = None, specialty: str | None = None, db: Session = Depends(get_db),
                   _=Depends(require_roles(*STAFF))):
    stmt = select(Mechanic).order_by(Mechanic.full_name)
    if active is not None:
        stmt = stmt.where(Mechanic.active.is_(active))
    if specialty:
        stmt = stmt.where(Mechanic.specialty.ilike(f"%{specialty}%"))
    return [_mechanic_out(db, m) for m in db.scalars(stmt)]


@app.post("/mechanics", response_model=MechanicOut, status_code=201, tags=["mecánicos"])
def create_mechanic(data: MechanicIn, db: Session = Depends(get_db), _=Depends(require_roles(ROLE_ADMIN))):
    """Crea el mecánico y su cuenta de acceso (rol *mecanico*) en el servicio de autenticación."""
    user = call("auth", "POST", "/internal/users", json={
        "full_name": data.full_name, "email": data.email, "password": data.password,
        "phone": data.phone, "role": ROLE_MECANICO})
    m = Mechanic(user_id=user["id"], full_name=data.full_name, email=user["email"],
                 phone=data.phone, specialty=data.specialty)
    db.add(m)
    db.commit()
    return _mechanic_out(db, m)


@app.get("/mechanics/me", response_model=MechanicOut, tags=["mecánicos"])
def my_mechanic(db: Session = Depends(get_db), user: CurrentUser = Depends(require_roles(ROLE_MECANICO))):
    m = db.scalar(select(Mechanic).where(Mechanic.user_id == user.id))
    if not m:
        raise HTTPException(404, "No tienes perfil de mecánico")
    return _mechanic_out(db, m)


@app.get("/mechanics/{mechanic_id}", response_model=MechanicOut, tags=["mecánicos"])
def get_mechanic(mechanic_id: int, db: Session = Depends(get_db), _=Depends(require_roles(*STAFF))):
    m = db.get(Mechanic, mechanic_id)
    if not m:
        raise HTTPException(404, "Mecánico no encontrado")
    return _mechanic_out(db, m)


@app.put("/mechanics/{mechanic_id}", response_model=MechanicOut, tags=["mecánicos"])
def update_mechanic(mechanic_id: int, data: MechanicUpdate, db: Session = Depends(get_db),
                    _=Depends(require_roles(ROLE_ADMIN))):
    m = db.get(Mechanic, mechanic_id)
    if not m:
        raise HTTPException(404, "Mecánico no encontrado")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(m, k, v)
    db.commit()
    return _mechanic_out(db, m)


# ---------------------------------------------------------------- asignaciones
@app.post("/assignments", response_model=AssignmentOut, status_code=201, tags=["asignaciones"])
def create_assignment(data: AssignmentIn, db: Session = Depends(get_db), _=Depends(require_roles(ROLE_ADMIN))):
    """Asigna un mecánico a una orden. Si la orden ya tenía mecánico, la asignación anterior se libera."""
    m = db.get(Mechanic, data.mechanic_id)
    if not m:
        raise HTTPException(404, "Mecánico no encontrado")
    if not m.active:
        raise HTTPException(409, "El mecánico está inactivo")
    db.execute(update(Assignment).where(Assignment.order_id == data.order_id, Assignment.active.is_(True))
               .values(active=False, released_at=utcnow()))
    a = Assignment(order_id=data.order_id, mechanic_id=m.id, notes=data.notes)
    db.add(a)
    db.commit()
    db.refresh(a)
    return _assignment_out(a)


@app.get("/assignments", response_model=list[AssignmentOut], tags=["asignaciones"])
def list_assignments(order_id: int | None = None, mechanic_id: int | None = None, active: bool | None = None,
                     db: Session = Depends(get_db), _=Depends(require_roles(*STAFF))):
    stmt = select(Assignment).order_by(Assignment.assigned_at.desc())
    if order_id:
        stmt = stmt.where(Assignment.order_id == order_id)
    if mechanic_id:
        stmt = stmt.where(Assignment.mechanic_id == mechanic_id)
    if active is not None:
        stmt = stmt.where(Assignment.active.is_(active))
    return [_assignment_out(a) for a in db.scalars(stmt)]


@app.post("/internal/orders/{order_id}/release", tags=["interno"])
def release_order(order_id: int, db: Session = Depends(get_db), _=Depends(internal_only)):
    """Libera las asignaciones activas cuando la orden termina o se cancela."""
    res = db.execute(update(Assignment).where(Assignment.order_id == order_id, Assignment.active.is_(True))
                     .values(active=False, released_at=utcnow()))
    db.commit()
    return {"released": res.rowcount}
