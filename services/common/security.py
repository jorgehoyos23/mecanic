"""Autenticación con JWT compartida.

El servicio de *usuarios y autenticación* emite los tokens; el resto de
microservicios solo los valida con el secreto compartido (JWT_SECRET), sin
tener que consultar al servicio de autenticación en cada petición.
"""
import hashlib
import hmac
import os
import secrets
import time

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-cambiar-en-produccion")
JWT_ALG = "HS256"
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_MINUTES", "480")) * 60

ROLE_CLIENTE = "cliente"
ROLE_MECANICO = "mecanico"
ROLE_ADMIN = "admin"
ROLE_SISTEMA = "sistema"  # llamadas internas entre microservicios
STAFF = (ROLE_ADMIN, ROLE_MECANICO)


# ---------------------------------------------------------------- contraseñas
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"pbkdf2${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, expected = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return hmac.compare_digest(digest.hex(), expected)


# ---------------------------------------------------------------- tokens
class CurrentUser(BaseModel):
    id: int
    email: str = ""
    name: str = ""
    role: str


def create_token(user_id: int, email: str, name: str, role: str, ttl: int = TOKEN_TTL_SECONDS) -> str:
    now = int(time.time())
    payload = {"sub": str(user_id), "email": email, "name": name, "role": role, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def service_token() -> str:
    """Token de corta duración para llamadas servicio-a-servicio."""
    return create_token(0, "sistema@taller.local", "Sistema", ROLE_SISTEMA, ttl=300)


_bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> CurrentUser:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")
    try:
        data = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "La sesión expiró")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
    return CurrentUser(id=int(data["sub"]), email=data.get("email", ""), name=data.get("name", ""), role=data["role"])


def require_roles(*roles: str):
    """Dependencia que exige uno de los roles indicados. El rol 'sistema' siempre pasa."""

    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role != ROLE_SISTEMA and user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para esta operación")
        return user

    return dependency


internal_only = require_roles()  # solo el rol 'sistema'
