# Imagen para publicar en Render: toda la plataforma en un solo contenedor.
# (Para desarrollo local con un contenedor por microservicio usa docker-compose.yml)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY services/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY services /srv/services
COPY frontend /srv/frontend
COPY scripts/servidor_unico.py /srv/scripts/servidor_unico.py

# Render define la variable PORT; en local se usa 8080
EXPOSE 8080
CMD ["python", "scripts/servidor_unico.py"]
