# Descripción General

## Stack tecnológico

| Capa | Tecnología | Versión mínima |
|------|------------|----------------|
| Lenguaje | Python | 3.12 |
| Framework web | FastAPI | 0.111 |
| Modelos de tabla | SQLModel | 0.0.24 |
| Motor / sesión / carga anticipada | SQLAlchemy | 2.0 (asíncrono) |
| Controlador de PostgreSQL | asyncpg o psycopg 3 asíncrono | 0.30 / capítulo 4 |
| Base de datos | PostgreSQL | 16 |
| Migraciones | Alembic | 1.13 (plantilla asíncrona) |
| Configuración | pydantic-settings | 2.0 |
| Hash de contraseñas | bcrypt | 4.0 |
| Token firmado | PyJWT | 2.8 |
| Servidor ASGI | uvicorn | el que instala `fastapi[standard]` |

## Arquitectura general

Organización por **módulo funcional**, con las mismas seis capas en todos los módulos:

```
Router → Service → Unit of Work → Repository → Models → Schemas
```

Cada módulo contiene sus propios archivos: `models.py`, `schemas.py`, `repository.py`, `unit_of_work.py`, `service.py`, `router.py`.

**Capa por capa:**

- **Router**: construye el Unit of Work con una dependencia, lo pasa al servicio sin abrirlo, traduce errores de dominio a códigos HTTP.
- **Service**: recibe el Unit of Work, lo abre con `async with`, nunca lo construye. Contiene las reglas de negocio.
- **Unit of Work**: gestor de contexto asíncrono; confirma al salir del bloque, revierte si hay excepción, no cierra la sesión (no la creó).
- **Repository**: recibe sesión y clase del modelo en el constructor. `add` y `update` hacen `flush()`, nunca `commit()`. Jerarquía: `BaseRepository[T]` y `SoftDeleteRepository[T]`.
- **Models**: modelos de tabla con restricciones y relaciones.
- **Schemas**: contratos de entrada y salida, separados de los modelos de tabla. `extra="forbid"` en contratos de entrada.

Módulos mínimos: `health`, `usuarios`, `clientes`, `repuestos`, `ordenes`. `AsignacionRol`, `EventoSeguridad` viven en `usuarios`; `Vehiculo` en `clientes`; `MovimientoStock` y `HistorialPrecio` en `repuestos`; `EstadoOrden`, `ItemOrden` e `HistorialEstadoOrden` en `ordenes`. El módulo `health` sólo tiene `router.py`.

## Integraciones externas

Ninguna integración externa obligatoria para la v1. El aviso al cliente se resuelve con `BackgroundTasks` dentro del mismo proceso (simulado con `await asyncio.sleep(0.5)` y un mensaje en el registro).

## API REST (resumen de endpoints principales)

**Grupo abierto:**
- `GET /health/live` — cualquiera, 200
- `GET /health/ready` — cualquiera, 200 / 503
- `POST /auth/registro` — cualquiera, 201 / 409 / 422
- `POST /auth/login` — cualquiera, 200 / 401 / 422 / 429
- `POST /auth/logout` — cualquiera, 200
- `GET /auth/yo` — autenticado, 200 / 401
- `POST /auth/cambiar-password` — autenticado, 200 / 401 / 422

**Grupo protegido:**
- `POST /usuarios` (alta de personal) — ADMIN, 201 / 409 / 422
- `GET/POST/DELETE /usuarios/{id}/roles` — ADMIN, varios códigos
- `GET /eventos` — ADMIN, 200 / 422
- `POST /clientes` — RECEPCION, ADMIN, 201 / 409 / 422
- `GET /clientes/{id}`, `POST /clientes/{id}/vehiculos`, `DELETE /vehiculos/{id}` — RECEPCION, ADMIN
- `GET /mis-vehiculos` — autenticado, 200
- `GET /repuestos` (q, page, size) — ADMIN, RECEPCION, MECANICO, 200 / 422
- `GET/POST/PATCH/DELETE /repuestos/{id}`, `POST /repuestos/{id}/reponer` — ADMIN
- `GET /repuestos/{id}/movimientos`, `GET /repuestos/{id}/precios` — ADMIN
- `POST /ordenes` — RECEPCION, ADMIN, 201 / 409 / 422
- `GET /ordenes` (estado, page, size) — ADMIN, RECEPCION, MECANICO, 200 / 422
- `GET /ordenes/{id}` — personal o dueño del vehículo, 200 / 403 / 404
- `POST /ordenes/{id}/iniciar` — MECANICO, 200 / 404 / 409
- `POST /ordenes/{id}/terminar` — mecánico asignado o ADMIN, 200 / 403 / 404 / 409
- `POST /ordenes/{id}/cancelar` — RECEPCION, ADMIN o dueño, 200 / 403 / 404 / 409
- `GET /estados-orden` — autenticado, 200
- `GET /mis-ordenes` (page, size) — autenticado, 200 / 422

**Clasificación de rutas:** en `main.py` se montan exactamente dos grupos de rutas distintos: el grupo "Abierto" (sin autenticación) y el grupo "Protegido". El grupo "Protegido" inyecta la dependencia del control de cambio obligatorio de contraseña **una sola vez a nivel de router** (no por ruta). Toda ruta del grupo protegido responde además 401 si no hay sesión válida y 403 si el usuario tiene el cambio de contraseña pendiente.
