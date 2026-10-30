# Proposal

## Why

Este change establece la infraestructura base del proyecto antes de implementar cualquier funcionalidad de dominio: estructura de directorios por módulo, dependencias de Python (FastAPI, SQLModel, SQLAlchemy async, PostgreSQL, Alembic, bcrypt, PyJWT), configuración de entorno (`.env.example`), aplicación FastAPI con lifespan y dos grupos de rutas (abierto y protegido), motor de base de datos asíncrono, fábrica de sesiones, configuración de Alembic con plantilla asíncrona, y el esqueleto de `seed.py`. Sin esta base, ningún cambio posterior (core-models, auth, órdenes de trabajo, etc.) puede implementarse.

## What Changes

- `app/` — estructura de directorios por módulo (`health`, `usuarios`, `clientes`, `repuestos`, `ordenes`), con `__init__.py` en cada paquete. Los archivos de las 6 capas (`models.py`, `schemas.py`, `repository.py`, `unit_of_work.py`, `service.py`, `router.py`) se crean en los changes que implementan cada módulo (C-02 en adelante), no en este.
- `app/core/` — `config.py`, `database.py`, `security.py`, `dependencies.py` (base de configuración, motor/sesiones y seguridad). `repository.py`, `paginacion.py` y `unit_of_work.py` pertenecen a C-02 `core-models`.
- `app/main.py` — aplicación FastAPI, lifespan (motor y fábrica en `app.state`, `dispose()` al apagar) y dos grupos de rutas (abierto y protegido)
- `requirements.txt` — Python 3.12, FastAPI 0.111, SQLModel 0.0.24, SQLAlchemy 2.0 async, asyncpg/psycopg3, Alembic 1.13, pydantic-settings 2.0, bcrypt 4.0, PyJWT 2.8, uvicorn
- `.env.example` — POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT, SECRET_KEY, BCRYPT_COST, SQL_ECHO
- `alembic.ini`, `migrations/env.py` (plantilla asíncrona), `migrations/script.py.mako` — **solo configuración**: la migración 001, la migración 002 y la validación de `alembic upgrade`/`downgrade` se realizan en C-09
- `seed.py` — esqueleto (datos iniciales se cargan en C-09)
- `test/` — carpeta para archivos `.http` y `solo_agregado.sql` (contenido en C-09)

## Capabilities

Este cambio es de infraestructura y setup; no introduce nuevas capacidades de dominio ni modifica requisitos de specs existentes.

### New Capabilities

(Ninguna — cambio de infraestructura pura.)

### Modified Capabilities

(Ninguno — no cambia requisitos de specs existentes.)

## Impact

- Código nuevo bajo `app/` (sin modificar código existente)
- `migrations/` — nueva carpeta con configuración de Alembic (sin revisiones: la migración 001 se autogenera en C-09)
- `requirements.txt` — nuevas dependencias de proyecto
- `.env.example` — plantilla de variables de entorno (secretos no versionados)
- `seed.py` — esqueleto; datos reales se cargan en C-09

**Nota sobre specs**: este change no altera comportamiento de dominio, por tanto no genera specs ni delta specs. Se opta por `skip_specs: true` en `.openspec.yaml` (no se inventan requisitos solo para satisfacer validación).
