"""Fábrica de aplicaciones FastAPI con la configuración común."""
import logging
import threading
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text

from common.db import SessionLocal, engine, init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")


def create_app(title: str, description: str, seed: Callable | None = None, background_seed: bool = False) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        init_db()
        if seed:
            def run_seed():
                with SessionLocal() as db:
                    seed(db)
            if background_seed:
                threading.Thread(target=run_seed, daemon=True).start()
            else:
                run_seed()
        yield

    app = FastAPI(
        title=title,
        description=description,
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/health", tags=["salud"])
    def health():
        """Estado del servicio y de su conexión a la base de datos."""
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db = "ok"
        except Exception:  # noqa: BLE001
            db = "error"
        return {"status": "ok" if db == "ok" else "degradado", "service": title,
                "database": {"status": db, "engine": engine.dialect.name, "name": engine.url.database}}

    return app
