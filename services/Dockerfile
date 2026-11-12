# Imagen común para todos los microservicios.
# Se construye con:  --build-arg SERVICE=<nombre_del_servicio>
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

ARG SERVICE
COPY common /srv/common
COPY ${SERVICE}/app /srv/app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# ROOT_PATH (p.ej. /api/auth) permite que /docs funcione detrás del API Gateway
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --root-path \"${ROOT_PATH:-}\""]
