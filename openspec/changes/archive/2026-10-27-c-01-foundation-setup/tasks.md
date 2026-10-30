# Tasks

## 1. Estructura de directorios y dependencias

- [x] 1.1 Crear estructura de directorios: app/, app/core/, app/modules/{health,usuarios,clientes,repuestos,ordenes}/, migrations/versions/, test/ y verificar que todas las carpetas existen (listar directorio)
- [x] 1.2 Crear requirements.txt con dependencias del stack (Python 3.12, FastAPI 0.111, SQLModel 0.0.24, SQLAlchemy 2.0 async, asyncpg/psycopg3, Alembic 1.13, pydantic-settings 2.0, bcrypt 4.0, PyJWT 2.8, uvicorn) y verificar que el archivo existe y lista las dependencias

## 2. Configuración core

- [x] 2.1 Crear app/core/config.py con Settings de pydantic-settings que lea variables de entorno (POSTGRES_*, SECRET_KEY, BCRYPT_COST, SQL_ECHO) sin valores por defecto en secretos, con @computed_field DATABASE_URL y verificar que se puede importar sin fallar
- [x] 2.2 Crear app/core/database.py con motor async, fábrica de sesiones y get_session; motor y fábrica creados en lifespan y guardados en app.state; get_session obtiene la fábrica desde app.state; las sesiones usan expire_on_commit=False; verificar que no hay create_all al importar
- [x] 2.3 Crear app/core/security.py con hash bcrypt fuera del bucle (asyncio.to_thread + semáforo), JWT con PyJWT (sub, iat, exp), sin OAuth2PasswordBearer, y verificar que bcrypt no se llama dentro del event loop

## 3. Aplicación principal

- [x] 3.1 Crear app/main.py con aplicación FastAPI, lifespan (crear motor y fábrica al arrancar, dispose() al apagar) y dos grupos de rutas (Abierto y Protegido); verificar que la app se importa sin errores. Hash ficticio del login diferido a C-03.
- [x] 3.2 Crear app/core/dependencies.py con get_current_user (lee token de cookie access_token), get_active_roles (esqueleto), require_password_change (esqueleto) y requiere_rol (esqueleto); verificar que se importan sin errores

## 4. Alembic y migraciones

> **Alcance**: C-01 solo deja la configuración de Alembic lista (plantilla asíncrona, URL desde entorno, `target_metadata` vacío). La generación de la Migración 001 (autogenerate), la Migración 002 (disparadores de solo agregado) y la validación de `alembic upgrade head` / `alembic downgrade base` se realizan exclusivamente en **C-09** (`integracion-final-migraciones-validacion`). No hay tareas de migración pendientes en C-01.

- [x] 4.1 Crear alembic.ini, migrations/env.py (plantilla asíncrona) y migrations/script.py.mako; verificar que env.py usa AsyncSession y no tiene secretos hardcodeados

## 5. seed.py esqueleto

- [x] 5.1 Crear seed.py con esqueleto de carga de datos iniciales (función main que termina correctamente sin NotImplementedError); verificar que se ejecuta sin errores (aunque no cargue datos reales todavía)

## 6. Archivos de entorno y verificación final

- [x] 6.1 Crear .env.example con POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT, SECRET_KEY, BCRYPT_COST, SQL_ECHO y verificar que no hay valores por defecto en secretos
- [x] 6.2 Verificación final: arrancar la aplicación con la configuración local disponible y confirmar que el lifespan inicializa el motor y la fábrica de sesiones sin errores, y que el motor se libera con `dispose()` al apagar

## Workflow follow-up

- Archivar el cambio con `/opsx:archive c-01-foundation-setup` una vez implementadas y verificadas todas las tareas.
- La generación de la migración 001, la migración 002 y la validación de `alembic upgrade`/`downgrade` pertenecen a **C-09**, no a este change.
