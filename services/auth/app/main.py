"""Microservicio de Usuarios y Autenticación."""
import logging
import os
import re
from datetime import datetime

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from common.app import create_app
from common.clients import call
from common.db import get_db
from common.security import (ROLE_ADMIN, ROLE_CLIENTE, ROLE_MECANICO, CurrentUser, create_token,
                             get_current_user, hash_password, internal_only, require_roles, verify_password)

from .models import User

log = logging.getLogger("auth")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ROLES = (ROLE_CLIENTE, ROLE_MECANICO, ROLE_ADMIN)


# ---------------------------------------------------------------- esquemas
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    phone: str | None
    role: str
    active: bool
    created_at: datetime


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: str
    password: str = Field(min_length=6)
    phone: str | None = None

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Correo electrónico inválido")
        return v


class InternalUserIn(RegisterIn):
    role: str = ROLE_CLIENTE


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserUpdate(BaseModel):
    active: bool | None = None
    role: str | None = None


def _token_for(user: User) -> TokenOut:
    return TokenOut(access_token=create_token(user.id, user.email, user.full_name, user.role),
                    user=UserOut.model_validate(user))


def _create_user(db: Session, data: RegisterIn, role: str) -> User:
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(409, "Ya existe un usuario con ese correo")
    user = User(email=data.email, full_name=data.full_name.strip(), phone=data.phone,
                password_hash=hash_password(data.password), role=role)
    db.add(user)
    db.commit()
    return user


# ---------------------------------------------------------------- semilla
def seed(db: Session):
    email = os.getenv("ADMIN_EMAIL", "admin@taller.com").lower()
    if not db.scalar(select(User).where(User.email == email)):
        db.add(User(email=email, full_name="Administrador Mecasolic", role=ROLE_ADMIN,
                    password_hash=hash_password(os.getenv("ADMIN_PASSWORD", "admin123"))))
        db.commit()
        log.info("Usuario administrador creado: %s", email)
    # nombre anterior a la marca Mecasolic
    old = db.scalar(select(User).where(User.email == email, User.full_name == "Administrador del Taller"))
    if old:
        old.full_name = "Administrador Mecasolic"
        db.commit()


app = create_app("Usuarios y Autenticación", "Registro, inicio de sesión, emisión de JWT y gestión de usuarios.", seed=seed)


# ---------------------------------------------------------------- endpoints
@app.post("/register", response_model=TokenOut, status_code=201, tags=["auth"])
def register(data: RegisterIn, db: Session = Depends(get_db)):
    """Registro público: crea un usuario con rol *cliente* y su perfil en el servicio de clientes."""
    user = _create_user(db, data, ROLE_CLIENTE)
    try:
        call("clientes", "POST", "/internal/customers", json={
            "user_id": user.id, "full_name": user.full_name, "email": user.email, "phone": user.phone})
    except HTTPException:
        # compensación: si no se pudo crear el perfil de cliente, se revierte el usuario
        db.delete(user)
        db.commit()
        raise
    return _token_for(user)


@app.post("/login", response_model=TokenOut, tags=["auth"])
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Correo o contraseña incorrectos")
    if not user.active:
        raise HTTPException(403, "El usuario está desactivado")
    return _token_for(user)


@app.get("/me", response_model=UserOut, tags=["auth"])
def me(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.get(User, current.id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    return user


@app.get("/users", response_model=list[UserOut], tags=["usuarios"])
def list_users(role: str | None = None, db: Session = Depends(get_db), _=Depends(require_roles(ROLE_ADMIN))):
    stmt = select(User).order_by(User.id)
    if role:
        stmt = stmt.where(User.role == role)
    return db.scalars(stmt).all()


@app.patch("/users/{user_id}", response_model=UserOut, tags=["usuarios"])
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db),
                _=Depends(require_roles(ROLE_ADMIN))):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    if data.role is not None:
        if data.role not in ROLES:
            raise HTTPException(422, f"Rol inválido. Opciones: {', '.join(ROLES)}")
        user.role = data.role
    if data.active is not None:
        user.active = data.active
    db.commit()
    return user


@app.post("/internal/users", response_model=UserOut, status_code=201, tags=["interno"])
def internal_create_user(data: InternalUserIn, get_or_create: bool = False,
                         db: Session = Depends(get_db), _=Depends(internal_only)):
    """Usado por otros servicios (p.ej. Mecánicos) para crear cuentas de usuario."""
    if data.role not in ROLES:
        raise HTTPException(422, "Rol inválido")
    if get_or_create:
        existing = db.scalar(select(User).where(User.email == data.email))
        if existing:
            return existing
    return _create_user(db, data, data.role)
