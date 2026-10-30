# Proposal

## Why

El desarrollo modular del backend (C-01 a C-08) implementó modelos, repositorios, servicios y endpoints, pero la base de datos PostgreSQL aún no posee su esquema inicial ni sus disparadores de inmutabilidad (RN-15), la suite de endpoints carece de las sondas de salud (`/health/live` y `/ready`), `seed.py` no cuenta con la carga de datos maestros y operativos, y faltan los casos de prueba de integración de la consigna (`test/*.http` y `solo_agregado.sql`). C-09 consolida, migra, puebla y valida el sistema completo contra PostgreSQL 16/17 en un estado listo para producción.

## What Changes

- **Migración 001 (`0001_inicial.py`)**: Configuración de `target_metadata = SQLModel.metadata` en `migrations/env.py` con la importación de todos los modelos de dominio (`usuarios`, `clientes`, `repuestos`, `ordenes`). Generación vía `alembic revision --autogenerate` de las 13 tablas, claves foráneas con índices explícitos, restricciones CHECK e índices únicos parciales (borrado lógico de vehículos/repuestos y asignaciones de rol abiertas).
- **Migración 002 (`0002_solo_agregado.py`)**: Migración DDL escrita a mano con función PL/pgSQL y disparadores `BEFORE UPDATE OR DELETE` sobre las tres tablas de sólo agregado (`historial_estado_orden`, `movimiento_stock`, `historial_precio_repuesto`) para cumplir RN-15, incluyendo función de `downgrade()`.
- **Validación del ciclo de migraciones**: Ejecución y verificación de idempotencia: `alembic upgrade head` (creación limpia) → `alembic downgrade base` (eliminación total) → `alembic upgrade head` (re-aplicación completa).
- **Endpoints de Salud (`/health`)**: Creación de `app/modules/health/router.py` con:
  - `GET /health/live` (US-027): Respuesta `200 OK` inmediata sin tocar base de datos.
  - `GET /health/ready` (US-028): Ejecución asíncrona de `SELECT 1` contra la base de datos; responde `200 OK` si contesta o `503 Service Unavailable` ante fallas de conexión. Montaje en `router_abierto` de `app/main.py`.
- **Carga de Datos Iniciales (`seed.py`)**: Script idempotente que puebla el catálogo de estados, usuarios de prueba con roles, clientes, vehículos, repuestos con stock inicial, órdenes de trabajo, historial de precios y evento inicial de seguridad (`SISTEMA`), compatible con los disparadores de sólo agregado.
- **Suite de Pruebas de Integración y Disparadores**:
  - `test/solo_agregado.sql`: Script SQL que valida los 6 rechazos por disparador de sólo agregado (UPDATE y DELETE en las 3 tablas inmutables) y el rechazo por FK inexistente (Caso C-14).
  - Casos C-01 a C-19 en archivos `.http` dentro de `test/` (ej. `test/casos_de_prueba.http`) con solicitudes, variables de entorno y respuestas esperadas documentadas.
  - Verificación del conteo constante de consultas SQL (Caso C-15) bajo `SQL_ECHO=true`.
  - Verificación de regresión completa de `pytest` (907+ tests).

## Capabilities

### New Capabilities
- `salud-del-sistema`: Endpoints de monitoreo y disponibilidad operativa (`GET /health/live` y `GET /health/ready`) para verificar el estado de la aplicación y su conectividad con la base de datos.

### Modified Capabilities
<!-- Ninguna capability existente modifica sus requisitos funcionales. Los modelos, reglas RBAC, stock y órdenes ya están especificados en sus capabilities correspondientes. -->

## Impact

- **Código nuevo / modificado**:
  - `migrations/env.py` (importación de modelos y binding de metadata).
  - `migrations/versions/0001_inicial.py` y `migrations/versions/0002_solo_agregado.py`.
  - `app/modules/health/router.py` y montaje en `app/main.py`.
  - `seed.py` (implementación completa de carga inicial).
  - `test/solo_agregado.sql` y `test/casos_de_prueba.http`.
- **Base de Datos**: Creación formal del esquema de 13 tablas, 3 disparadores PL/pgSQL y población inicial en PostgreSQL.
- **Dependencias**: Requiere que los cambios C-04, C-05, C-06, C-07 y C-08 estén integrados y estables en el repositorio.
