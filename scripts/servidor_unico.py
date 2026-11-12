"""Ejecuta TODO Mecasolic en un solo proceso (pensado para Render u otro hosting con poca RAM).

- Los 8 microservicios se montan en /api/<servicio> dentro de una sola app FastAPI.
- Cada servicio sigue teniendo SU PROPIA base de datos:
    * Postgres (variable DATABASE_URL, p. ej. la que da Render): un *schema* por servicio.
    * SQLite   (sin DATABASE_URL): un archivo por servicio en .datos_locales/.
- El frontend se sirve en / (igual que el API Gateway de Docker).

Uso local:   .venv\\Scripts\\python scripts\\servidor_unico.py     (PORT=8080 por defecto)
"""
import importlib
import os
import pathlib
import sys
from contextlib import AsyncExitStack, asynccontextmanager

ROOT = pathlib.Path(__file__).resolve().parent.parent
SERVICES_DIR = ROOT / "services"
FRONTEND = (ROOT / "frontend").resolve()
DATA = ROOT / ".datos_locales"
# 'mecanicos' va al final porque necesita a 'auth' para crear sus usuarios demo
SVCS = ["auth", "clientes", "servicios", "ordenes", "inventario", "facturacion", "notificaciones", "mecanicos"]
PORT = int(os.getenv("PORT", "8080"))


def database_urls() -> dict:
    base = os.getenv("DATABASE_URL", "").strip()
    if not base:
        DATA.mkdir(exist_ok=True)
        print("Base de datos: SQLite (.datos_locales/)")
        return {s: f"sqlite:///{(DATA / (s + '.db')).as_posix()}" for s in SVCS}

    for prefix in ("postgres://", "postgresql://"):
        if base.startswith(prefix):
            base = "postgresql+psycopg://" + base[len(prefix):]
    from sqlalchemy import create_engine, text

    engine = create_engine(base, pool_pre_ping=True)
    with engine.begin() as conn:
        for s in SVCS:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{s}"'))
    engine.dispose()
    print("Base de datos: Postgres (un schema por servicio)")
    sep = "&" if "?" in base else "?"
    return {s: f"{base}{sep}options=-csearch_path%3D{s}" for s in SVCS}


def load_services() -> dict:
    """Importa cada microservicio por separado, con su propia DATABASE_URL."""
    os.environ.setdefault("JWT_SECRET", "secreto-local-de-desarrollo-32-bytes!")
    for s in SVCS:  # las llamadas entre servicios pasan por este mismo servidor
        os.environ[f"{s.upper()}_URL"] = f"http://127.0.0.1:{PORT}/api/{s}"
    urls = database_urls()
    sys.path.insert(0, str(SERVICES_DIR))
    apps = {}
    for s in SVCS:
        os.environ["DATABASE_URL"] = urls[s]
        # 'app' y 'common' se reimportan para que cada servicio tenga su propio motor de BD
        for name in list(sys.modules):
            if name.split(".")[0] in ("app", "common"):
                del sys.modules[name]
        sys.path.insert(0, str(SERVICES_DIR / s))
        try:
            apps[s] = importlib.import_module("app.main").app
        finally:
            sys.path.pop(0)
        print(f"  · {s:<15} /api/{s}")
    return apps


def build_app():
    from fastapi import FastAPI
    from fastapi.responses import FileResponse

    services = load_services()

    @asynccontextmanager
    async def lifespan(_app):
        # Starlette no ejecuta el 'lifespan' de las apps montadas: se hace aquí (crea tablas y datos demo)
        async with AsyncExitStack() as stack:
            for sub in services.values():
                await stack.enter_async_context(sub.router.lifespan_context(sub))
            yield

    main = FastAPI(title="Mecasolic", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    for s, sub in services.items():
        main.mount(f"/api/{s}", sub)

    @main.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        f = (FRONTEND / path).resolve()
        if not path or not f.is_file() or FRONTEND not in f.parents:
            f = FRONTEND / "index.html"
        return FileResponse(f)

    return main


if __name__ == "__main__":
    import uvicorn

    print("Iniciando Mecasolic…")
    uvicorn.run(build_app(), host=os.getenv("HOST", "0.0.0.0"), port=PORT,
                proxy_headers=True, forwarded_allow_ips="*")
