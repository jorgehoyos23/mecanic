"""Ejecuta Mecasolic SIN Docker (modo desarrollo).

- Cada microservicio corre como un proceso uvicorn con SU PROPIA base de datos:
    * MySQL  -> si existe el archivo .env con DB_MOTOR=mysql (ver .env.example).
                Se crean automáticamente las bases mecasolic_auth, mecasolic_clientes, ...
    * SQLite -> en cualquier otro caso (carpeta .datos_locales/).
- Un mini API Gateway en http://localhost:8080 sirve el frontend y enruta /api/<servicio>/.

Uso:
    python -m venv .venv
    .venv\\Scripts\\pip install fastapi uvicorn sqlalchemy httpx pyjwt pymysql cryptography
    .venv\\Scripts\\python scripts\\ejecutar_sin_docker.py

Detener con Ctrl+C.
"""
import http.server
import os
import pathlib
import socket
import socketserver
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / ".datos_locales"
SVCS = ["auth", "clientes", "servicios", "ordenes", "inventario", "facturacion", "notificaciones", "mecanicos"]
PORTS = {s: 8101 + i for i, s in enumerate(SVCS)}
GATEWAY_PORT = int(os.getenv("PUERTO", "8080"))
MIME = {".js": "application/javascript", ".css": "text/css", ".html": "text/html; charset=utf-8",
        ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}


def load_env() -> dict:
    """Lee el archivo .env (CLAVE=valor) de la raíz del proyecto."""
    cfg = {}
    env_file = ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


def database_urls(cfg: dict) -> dict:
    """Devuelve la URL de base de datos de cada servicio (y crea las bases en MySQL si hace falta)."""
    if cfg.get("DB_MOTOR", "").lower() != "mysql":
        DATA.mkdir(exist_ok=True)
        print("Base de datos: SQLite (crea un archivo .env con DB_MOTOR=mysql para usar MySQL)")
        return {s: f"sqlite:///{(DATA / (s + '.db')).as_posix()}" for s in SVCS}

    import pymysql  # se importa solo cuando se usa MySQL

    host, port = cfg.get("MYSQL_HOST", "127.0.0.1"), int(cfg.get("MYSQL_PORT", "3306"))
    user, password = cfg.get("MYSQL_USER", "root"), cfg.get("MYSQL_PASSWORD", "")
    prefix = cfg.get("MYSQL_PREFIJO", "mecasolic_")
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=password)
    except pymysql.err.OperationalError as exc:
        sys.exit(f"\n❌ No se pudo conectar a MySQL en {host}:{port} con el usuario '{user}'.\n"
                 f"   Revisa MYSQL_USER / MYSQL_PASSWORD en el archivo .env\n   Detalle: {exc}")
    with conn, conn.cursor() as cur:
        for s in SVCS:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{prefix}{s}` "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    print(f"Base de datos: MySQL {host}:{port} · bases {prefix}<servicio> listas")
    pwd = urllib.parse.quote_plus(password)
    return {s: f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{prefix}{s}?charset=utf8mb4" for s in SVCS}


def start_services():
    DATA.mkdir(exist_ok=True)
    cfg = load_env()
    urls = database_urls(cfg)
    env_base = {**os.environ, "PYTHONPATH": str(ROOT / "services"),
                "JWT_SECRET": cfg.get("JWT_SECRET", "secreto-local-de-desarrollo-32-bytes!"),
                **{f"{s.upper()}_URL": f"http://127.0.0.1:{p}" for s, p in PORTS.items()}}
    procs = []
    for s in SVCS:  # 'mecanicos' va al final porque necesita a 'auth' para crear sus usuarios demo
        env = {**env_base, "DATABASE_URL": urls[s]}
        log = open(DATA / f"{s}.log", "a", encoding="utf-8")
        procs.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORTS[s]), "--root-path", f"/api/{s}"],
            cwd=ROOT / "services" / s, env=env, stdout=log, stderr=subprocess.STDOUT))
        print(f"  · {s:<15} http://127.0.0.1:{PORTS[s]}  (log: .datos_locales/{s}.log)")
        time.sleep(0.5)
    return procs


class Gateway(http.server.BaseHTTPRequestHandler):
    def _handle(self):
        parts = self.path.split("/", 3)
        if len(parts) >= 3 and parts[1] == "api" and parts[2] in PORTS:
            url = f"http://127.0.0.1:{PORTS[parts[2]]}/" + (parts[3] if len(parts) > 3 else "")
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) or None
            headers = {k: v for k, v in self.headers.items() if k.lower() in ("authorization", "content-type")}
            try:
                with urllib.request.urlopen(urllib.request.Request(url, data=body, method=self.command,
                                                                   headers=headers), timeout=30) as r:
                    code, data, ctype = r.status, r.read(), r.headers.get("Content-Type", "application/json")
            except urllib.error.HTTPError as e:
                code, data, ctype = e.code, e.read(), e.headers.get("Content-Type", "application/json")
            except urllib.error.URLError:
                code, data, ctype = 503, b'{"detail":"Servicio no disponible"}', "application/json"
        else:
            f = ROOT / "frontend" / (self.path.split("?")[0].lstrip("/") or "index.html")
            if not f.is_file():
                f = ROOT / "frontend" / "index.html"
            code, data, ctype = 200, f.read_bytes(), MIME.get(f.suffix, "application/octet-stream")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _handle

    def log_message(self, *args):
        pass


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    request_queue_size = 64


class Server6(Server):
    address_family = socket.AF_INET6


if __name__ == "__main__":
    print("Iniciando microservicios…")
    procs = start_services()
    print(f"\nPlataforma lista en  http://localhost:{GATEWAY_PORT}   (Ctrl+C para detener)\n")
    try:
        # 'localhost' en Windows prueba primero IPv6 (::1); escuchar en ambas evita esperas de ~2 s por conexión
        try:
            threading.Thread(target=Server6(("::1", GATEWAY_PORT), Gateway).serve_forever, daemon=True).start()
        except OSError:
            pass  # sin IPv6: basta con IPv4
        Server(("127.0.0.1", GATEWAY_PORT), Gateway).serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            p.terminate()
