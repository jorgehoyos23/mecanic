"""Comunicación síncrona (HTTP/REST) entre microservicios."""
import logging
import os

import httpx
from fastapi import HTTPException

from common.security import service_token

log = logging.getLogger("clients")

SERVICE_NAMES = ("auth", "clientes", "mecanicos", "servicios", "ordenes", "inventario", "facturacion", "notificaciones")
SERVICES = {name: os.getenv(f"{name.upper()}_URL", f"http://{name}:8000") for name in SERVICE_NAMES}


def call(service: str, method: str, path: str, json=None, params=None, timeout: float = 10.0):
    """Invoca otro microservicio con un token de sistema.

    Los errores 4xx del servicio remoto se propagan con su mismo mensaje; si el
    servicio no responde se devuelve 503.
    """
    url = SERVICES[service].rstrip("/") + path
    headers = {"Authorization": f"Bearer {service_token()}"}
    try:
        resp = httpx.request(method, url, json=json, params=params, headers=headers, timeout=timeout)
    except httpx.HTTPError as exc:
        log.error("Error llamando a %s %s: %s", service, path, exc)
        raise HTTPException(503, f"El servicio de {service} no está disponible")
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        raise HTTPException(resp.status_code if resp.status_code < 500 else 502, detail)
    return resp.json() if resp.content else None


def notify(title: str, message: str, *, user_id: int | None = None, role: str | None = None,
           type: str = "info", order_id: int | None = None) -> None:
    """Envía una notificación. Nunca hace fallar la operación principal."""
    if user_id is None and role is None:
        return
    try:
        call("notificaciones", "POST", "/internal/notifications", json={
            "user_id": user_id, "role": role, "title": title, "message": message,
            "type": type, "order_id": order_id,
        })
    except HTTPException as exc:
        log.warning("No se pudo enviar la notificación '%s': %s", title, exc.detail)
