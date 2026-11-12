# Mecasolic · Plataforma de Gestión de Taller Mecánico

Plataforma basada en **microservicios** para gestionar clientes, vehículos, mecánicos, órdenes de trabajo,
servicios de mantenimiento, cotizaciones, repuestos, facturación y notificaciones.

Un cliente puede **registrar su vehículo**, **solicitar un servicio** de mantenimiento o reparación,
**consultar el diagnóstico y la cotización**, **seguir el estado** de la orden y **recibir notificaciones**
de cada avance hasta la finalización y entrega.

## Arquitectura

```
                    ┌──────────────────────────────────────────┐
  Navegador ──────► │ API Gateway (Nginx :8080) + Frontend SPA │
                    └──────────────────┬───────────────────────┘
                                       │  /api/<servicio>/...
   ┌──────────┬───────────┬────────────┼────────────┬────────────┬─────────────┬────────────────┐
   ▼          ▼           ▼            ▼            ▼            ▼             ▼                ▼
 auth     clientes    mecanicos    servicios     ordenes     inventario   facturacion   notificaciones
   │          │           │            │            │            │             │                │
   └──────────┴───────────┴────── PostgreSQL (una base de datos por servicio) ─┴────────────────┘
```

| Microservicio | Responsabilidad | Base de datos |
|---|---|---|
| **auth** – Usuarios y autenticación | Registro, login, emisión de JWT, roles (`cliente`, `mecanico`, `admin`) | `auth_db` |
| **clientes** – Clientes y vehículos | Perfil del cliente, registro y consulta de vehículos | `clientes_db` |
| **mecanicos** – Mecánicos y asignaciones | Personal técnico, especialidad, carga de trabajo, asignación a órdenes | `mecanicos_db` |
| **servicios** – Servicios y cotizaciones | Catálogo de servicios, cotizaciones con mano de obra y repuestos | `servicios_db` |
| **ordenes** – Órdenes de trabajo y reparaciones | Ciclo de vida de la orden, diagnóstico, bitácora de avances (**orquestador**) | `ordenes_db` |
| **inventario** – Repuestos | Stock, entradas, consumos por orden, devoluciones, alertas de stock bajo | `inventario_db` |
| **facturacion** – Facturación y pagos | Factura con IVA al finalizar la orden, registro de pagos | `facturacion_db` |
| **notificaciones** | Bandeja de notificaciones por usuario o por rol (y correo simulado en el log) | `notificaciones_db` |

### Decisiones de diseño

- **Python + FastAPI**: cada servicio publica su documentación Swagger en `/api/<servicio>/docs`.
- **Database per service**: ningún servicio consulta la base de datos de otro. Las referencias entre servicios
  son IDs (p. ej., `vehicle_id` en una orden) y, cuando hace falta, se guarda una copia del dato
  (`vehicle_label`, `client_name`) para no depender de otro servicio al listar.
- **Comunicación REST síncrona** (`services/common/clients.py`). Las llamadas internas usan un JWT con rol
  `sistema` y van a endpoints `/internal/...`, que no están disponibles para usuarios.
- **Autenticación sin estado**: `auth` firma los JWT y los demás servicios solo los validan con el secreto
  compartido (`JWT_SECRET`).
- **Compensaciones (patrón saga)**: si falla un paso de una operación distribuida, se deshace lo anterior. Por
  ejemplo, si al aprobar una cotización falla el registro de la decisión, los repuestos vuelven al
  inventario. Al cancelar una orden ya aprobada también se devuelve el stock.
- **Notificaciones tolerantes a fallos**: si el servicio de notificaciones no está disponible, la operación
  principal no falla.

## Flujo de una orden de trabajo

```
SOLICITADA ─► EN_DIAGNOSTICO ─► COTIZADA ─► APROBADA ─► EN_REPARACION ─► FINALIZADA ─► ENTREGADA
  (cliente)    (admin asigna     (mecánico     (cliente       (mecánico)      (mecánico:     (admin, solo
               mecánico)         diagnostica   aprueba:                       se genera      con factura
                                 y cotiza)     se descuenta                   la factura)    pagada)
                                     │         el stock)
                                     └─► RECHAZADA ─► (nueva cotización)
CANCELADA: el cliente puede cancelar antes de aprobar; el admin, antes de finalizar (se devuelve el stock).
```

Cada transición queda registrada en la bitácora de la orden y genera notificaciones para el cliente, el
mecánico o los administradores, según corresponda.

## Cómo ejecutar

Requisitos: **Docker Desktop**.

```bash
docker compose up --build
```

- Aplicación web: <http://localhost:8080>
- Swagger de cada servicio: `http://localhost:8080/api/<servicio>/docs` (p. ej., `/api/ordenes/docs`)
- PostgreSQL expuesto en `localhost:5433` (usuario/contraseña `taller`/`taller`)

### Cuentas de demostración (se crean al iniciar)

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@taller.com` | `admin123` |
| Mecánico | `mecanico@taller.com` (también `laura@taller.com` y `andres@taller.com`) | `mecanico123` |
| Cliente | Regístrate desde la pantalla de inicio | — |

Además, se cargan 7 servicios en el catálogo y 10 repuestos en el inventario.

### Prueba automática del flujo completo

Con la plataforma levantada:

```bash
python scripts/prueba_flujo.py
```

La prueba recorre todo el ciclo: registro, vehículo, solicitud, asignación, diagnóstico, aprobación con
descuento de stock, reparación, factura, pago, entrega, notificaciones, control de acceso (401/403) y
cancelación con devolución de stock.

## Estructura del proyecto

```
taller-mecanico/
├── docker-compose.yml
├── db/init.sql                 # crea una base de datos por microservicio
├── gateway/nginx.conf          # API Gateway + servidor del frontend
├── frontend/                   # SPA en HTML/CSS/JS (sin compilación)
├── scripts/prueba_flujo.py     # prueba de extremo a extremo
└── services/
    ├── Dockerfile              # imagen común (ARG SERVICE)
    ├── requirements.txt
    ├── common/                 # código compartido: BD, JWT, cliente HTTP, fábrica de app
    └── <servicio>/app/
        ├── models.py           # modelos SQLAlchemy
        └── main.py             # endpoints FastAPI
```

## Endpoints principales

| Método | Ruta (vía gateway) | Rol |
|---|---|---|
| POST | `/api/auth/register` · `/api/auth/login` | público |
| GET/POST | `/api/clientes/vehicles` | cliente, admin |
| GET | `/api/servicios/catalog` | público |
| POST | `/api/ordenes/orders` | cliente, admin |
| GET | `/api/ordenes/orders` · `/api/ordenes/orders/{id}` | todos (cada rol ve lo suyo) |
| POST | `/api/ordenes/orders/{id}/assign` | admin |
| POST | `/api/ordenes/orders/{id}/diagnosis` | mecánico, admin |
| POST | `/api/ordenes/orders/{id}/quote-decision` | cliente, admin |
| POST | `/api/ordenes/orders/{id}/status` | según la transición |
| POST | `/api/ordenes/orders/{id}/notes` | mecánico, admin |
| GET/POST | `/api/inventario/parts` · `/api/inventario/parts/{id}/stock` | mecánico (lectura), admin |
| GET | `/api/facturacion/invoices` · POST `/invoices/{id}/pay` | cliente, admin |
| GET | `/api/notificaciones/notifications/me` | todos |

## Posibles mejoras

- Mensajería asíncrona (RabbitMQ o Kafka) para los eventos de la orden y las notificaciones.
- Envío real de correo, SMS o WhatsApp desde el servicio de notificaciones.
- Integración con una pasarela de pagos real.
- Migraciones con Alembic en lugar de `create_all`.
