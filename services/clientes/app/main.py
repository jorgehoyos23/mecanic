"""Microservicio de Clientes y Vehículos."""
from datetime import datetime

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from common.app import create_app
from common.db import get_db
from common.security import (ROLE_ADMIN, ROLE_CLIENTE, ROLE_SISTEMA, STAFF, CurrentUser, get_current_user,
                             internal_only, require_roles)

from .models import Customer, Vehicle

app = create_app("Clientes y Vehículos", "Perfiles de clientes y registro de sus vehículos.")


# ---------------------------------------------------------------- esquemas
class CustomerIn(BaseModel):
    user_id: int | None = None
    full_name: str = Field(min_length=3)
    email: str
    phone: str | None = None
    address: str | None = None
    document: str | None = None


class CustomerUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    address: str | None = None
    document: str | None = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    full_name: str
    email: str
    phone: str | None
    address: str | None
    document: str | None
    created_at: datetime
    vehicle_count: int = 0


class VehicleIn(BaseModel):
    plate: str = Field(min_length=3, max_length=15)
    brand: str = Field(min_length=2)
    model: str = Field(min_length=1)
    year: int = Field(ge=1950, le=2100)
    color: str | None = None
    vin: str | None = None
    mileage: int = Field(default=0, ge=0)
    customer_id: int | None = None  # solo lo usa el administrador

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, v: str) -> str:
        return v.strip().upper().replace(" ", "")


class VehicleUpdate(BaseModel):
    color: str | None = None
    mileage: int | None = Field(default=None, ge=0)
    vin: str | None = None


class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    owner_user_id: int | None = None
    owner_name: str | None = None
    plate: str
    brand: str
    model: str
    year: int
    color: str | None
    vin: str | None
    mileage: int
    created_at: datetime


def _vehicle_out(v: Vehicle) -> VehicleOut:
    out = VehicleOut.model_validate(v)
    out.owner_user_id = v.customer.user_id
    out.owner_name = v.customer.full_name
    return out


def _customer_out(db: Session, c: Customer) -> CustomerOut:
    out = CustomerOut.model_validate(c)
    out.vehicle_count = db.scalar(select(func.count(Vehicle.id)).where(Vehicle.customer_id == c.id)) or 0
    return out


def _my_customer(db: Session, user: CurrentUser) -> Customer:
    c = db.scalar(select(Customer).where(Customer.user_id == user.id))
    if not c:
        raise HTTPException(404, "No se encontró el perfil de cliente de este usuario")
    return c


def _get_vehicle_checked(db: Session, vehicle_id: int, user: CurrentUser) -> Vehicle:
    v = db.get(Vehicle, vehicle_id)
    if not v:
        raise HTTPException(404, "Vehículo no encontrado")
    if user.role == ROLE_CLIENTE and v.customer.user_id != user.id:
        raise HTTPException(403, "Este vehículo no te pertenece")
    return v


# ---------------------------------------------------------------- clientes
@app.post("/internal/customers", response_model=CustomerOut, status_code=201, tags=["interno"])
def internal_create_customer(data: CustomerIn, db: Session = Depends(get_db), _=Depends(internal_only)):
    if data.user_id and db.scalar(select(Customer).where(Customer.user_id == data.user_id)):
        raise HTTPException(409, "El usuario ya tiene un perfil de cliente")
    c = Customer(**data.model_dump())
    db.add(c)
    db.commit()
    return _customer_out(db, c)


@app.post("/customers", response_model=CustomerOut, status_code=201, tags=["clientes"])
def create_customer(data: CustomerIn, db: Session = Depends(get_db), _=Depends(require_roles(ROLE_ADMIN))):
    """El administrador puede registrar clientes que llegan al taller sin cuenta en la plataforma."""
    data.user_id = None
    c = Customer(**data.model_dump())
    db.add(c)
    db.commit()
    return _customer_out(db, c)


@app.get("/customers", response_model=list[CustomerOut], tags=["clientes"])
def list_customers(q: str | None = None, db: Session = Depends(get_db), _=Depends(require_roles(*STAFF))):
    stmt = select(Customer).order_by(Customer.full_name)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Customer.full_name.ilike(like), Customer.email.ilike(like), Customer.document.ilike(like)))
    return [_customer_out(db, c) for c in db.scalars(stmt)]


@app.get("/customers/me", response_model=CustomerOut, tags=["clientes"])
def my_profile(db: Session = Depends(get_db), user: CurrentUser = Depends(require_roles(ROLE_CLIENTE))):
    return _customer_out(db, _my_customer(db, user))


@app.put("/customers/me", response_model=CustomerOut, tags=["clientes"])
def update_my_profile(data: CustomerUpdate, db: Session = Depends(get_db),
                      user: CurrentUser = Depends(require_roles(ROLE_CLIENTE))):
    c = _my_customer(db, user)
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(c, k, v)
    db.commit()
    return _customer_out(db, c)


@app.get("/customers/by-user/{user_id}", response_model=CustomerOut, tags=["clientes"])
def customer_by_user(user_id: int, db: Session = Depends(get_db), _=Depends(require_roles(*STAFF))):
    c = db.scalar(select(Customer).where(Customer.user_id == user_id))
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    return _customer_out(db, c)


@app.get("/customers/{customer_id}", response_model=CustomerOut, tags=["clientes"])
def get_customer(customer_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    c = db.get(Customer, customer_id)
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    if user.role == ROLE_CLIENTE and c.user_id != user.id:
        raise HTTPException(403, "No puedes ver este cliente")
    return _customer_out(db, c)


# ---------------------------------------------------------------- vehículos
@app.get("/vehicles", response_model=list[VehicleOut], tags=["vehículos"])
def list_vehicles(customer_id: int | None = None, q: str | None = None, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(get_current_user)):
    stmt = select(Vehicle).order_by(Vehicle.id.desc())
    if user.role == ROLE_CLIENTE:
        stmt = stmt.where(Vehicle.customer_id == _my_customer(db, user).id)
    elif customer_id:
        stmt = stmt.where(Vehicle.customer_id == customer_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Vehicle.plate.ilike(like), Vehicle.brand.ilike(like), Vehicle.model.ilike(like)))
    return [_vehicle_out(v) for v in db.scalars(stmt)]


@app.post("/vehicles", response_model=VehicleOut, status_code=201, tags=["vehículos"])
def create_vehicle(data: VehicleIn, db: Session = Depends(get_db),
                   user: CurrentUser = Depends(require_roles(ROLE_CLIENTE, ROLE_ADMIN))):
    if user.role == ROLE_CLIENTE:
        customer = _my_customer(db, user)
    else:
        if not data.customer_id:
            raise HTTPException(422, "Debes indicar el cliente dueño del vehículo")
        customer = db.get(Customer, data.customer_id)
        if not customer:
            raise HTTPException(404, "Cliente no encontrado")
    if db.scalar(select(Vehicle).where(Vehicle.plate == data.plate)):
        raise HTTPException(409, f"Ya existe un vehículo con la placa {data.plate}")
    v = Vehicle(customer_id=customer.id, **data.model_dump(exclude={"customer_id"}))
    db.add(v)
    db.commit()
    db.refresh(v)
    return _vehicle_out(v)


@app.get("/vehicles/{vehicle_id}", response_model=VehicleOut, tags=["vehículos"])
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    return _vehicle_out(_get_vehicle_checked(db, vehicle_id, user))


@app.put("/vehicles/{vehicle_id}", response_model=VehicleOut, tags=["vehículos"])
def update_vehicle(vehicle_id: int, data: VehicleUpdate, db: Session = Depends(get_db),
                   user: CurrentUser = Depends(get_current_user)):
    v = _get_vehicle_checked(db, vehicle_id, user)
    for k, val in data.model_dump(exclude_none=True).items():
        setattr(v, k, val)
    db.commit()
    return _vehicle_out(v)


@app.delete("/vehicles/{vehicle_id}", status_code=204, tags=["vehículos"])
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db),
                   user: CurrentUser = Depends(require_roles(ROLE_CLIENTE, ROLE_ADMIN, ROLE_SISTEMA))):
    v = _get_vehicle_checked(db, vehicle_id, user)
    db.delete(v)
    db.commit()
