"""Acceso a base de datos compartido por todos los microservicios.

Cada microservicio tiene SU PROPIA base de datos (patrón *database per service*);
este módulo solo comparte el código, no los datos.
"""
import logging
import os
import time
from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

log = logging.getLogger("db")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
# pool_recycle evita conexiones cerradas por MySQL tras inactividad (wait_timeout)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=1800, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def cop(value: float) -> str:
    """Formato de moneda colombiana: 255850 -> '$255.850'."""
    return "$" + f"{value or 0:,.0f}".replace(",", ".")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_missing_columns() -> None:
    """Migración ligera: agrega a las tablas existentes las columnas nuevas de los modelos.

    Solo añade columnas (siempre como NULL permitidas); nunca borra ni modifica datos.
    """
    insp = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        existing = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing:
                continue
            col_type = col.type.compile(dialect=engine.dialect)
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type} NULL"))
            log.info("Migración: columna %s.%s agregada", table.name, col.name)


def init_db(retries: int = 30, delay: float = 2.0) -> None:
    """Crea las tablas (y columnas nuevas), reintentando mientras la base de datos arranca."""
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(engine)
            add_missing_columns()
            return
        except OperationalError:
            log.warning("Base de datos no disponible (intento %s/%s)", attempt, retries)
            time.sleep(delay)
    raise RuntimeError("No fue posible conectar con la base de datos")
