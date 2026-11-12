"""Microservicio de Notificaciones.

Almacena las notificaciones de la plataforma (bandeja in-app) y simula el envío
por correo electrónico escribiendo en el log del contenedor.
"""
import logging
from datetime import datetime
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from common.app import create_app
from common.db import get_db
from common.security import CurrentUser, get_current_user, internal_only

from .models import Notification

log = logging.getLogger("notificaciones")

app = create_app("Notificaciones", "Avisos sobre avances y finalización de los servicios.")


class NotificationIn(BaseModel):
    user_id: int | None = None
    role: str | None = None
    title: str
    message: str
    type: Literal["info", "exito", "alerta"] = "info"
    order_id: int | None = None


class NotificationOut(NotificationIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    read: bool
    created_at: datetime


def _mine(user: CurrentUser):
    return or_(Notification.user_id == user.id, Notification.role == user.role)


@app.post("/internal/notifications", response_model=NotificationOut, status_code=201, tags=["interno"])
def create_notification(data: NotificationIn, db: Session = Depends(get_db), _=Depends(internal_only)):
    if data.user_id is None and data.role is None:
        raise HTTPException(422, "Se requiere user_id o role")
    n = Notification(**data.model_dump())
    db.add(n)
    db.commit()
    target = f"usuario {data.user_id}" if data.user_id else f"rol {data.role}"
    log.info("[EMAIL simulado] Para %s | %s | %s", target, data.title, data.message)
    return n


@app.get("/notifications/me", response_model=list[NotificationOut], tags=["notificaciones"])
def my_notifications(unread_only: bool = False, limit: int = 50, db: Session = Depends(get_db),
                     user: CurrentUser = Depends(get_current_user)):
    stmt = select(Notification).where(_mine(user)).order_by(Notification.id.desc()).limit(min(limit, 200))
    if unread_only:
        stmt = stmt.where(Notification.read.is_(False))
    return db.scalars(stmt).all()


@app.get("/notifications/me/unread-count", tags=["notificaciones"])
def unread_count(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    count = db.scalar(select(func.count(Notification.id)).where(_mine(user), Notification.read.is_(False)))
    return {"unread": count or 0}


@app.post("/notifications/{notification_id}/read", response_model=NotificationOut, tags=["notificaciones"])
def mark_read(notification_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    n = db.scalar(select(Notification).where(Notification.id == notification_id, _mine(user)))
    if not n:
        raise HTTPException(404, "Notificación no encontrada")
    n.read = True
    db.commit()
    return n


@app.post("/notifications/me/read-all", tags=["notificaciones"])
def mark_all_read(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    res = db.execute(update(Notification).where(_mine(user), Notification.read.is_(False)).values(read=True))
    db.commit()
    return {"updated": res.rowcount}
