# Design

## Context

El proyecto es una API backend pura (sin frontend propio) para un taller mecánico, con stack Python 3.12 + FastAPI + SQLModel/SQLAlchemy async + PostgreSQL 16 + Alembic + bcrypt + PyJWT. La Knowledge Base (`knowledge-base/`) define el modelo de datos, las 20 reglas de negocio (RN-01 a RN-20), las 6 capas por módulo y los endpoints de referencia. Este change solo establece la infraestructura: estructura de directorios, dependencias, configuración, motor de BD, fábrica de sesiones, configuración de Alembic y esqueleto de `seed.py`. No implementa lógica de dominio (ese alcance corresponde a C-02 en adelante). Véase `proposal.md - Why` para la motivación completa.

## Goals / Non-Goals

**Goals:**
- Crear la estructura de directorios por módulo funcional (`app/core/` y `app/modules/{health,usuarios,clientes,repuestos,ordenes}/`), con `__init__.py` en cada paquete
- Configurar el motor de base de datos asíncrono y la fábrica de sesiones (creados en el lifespan, guardados en `app.state`, liberados con `dispose()`)
- Configurar Alembic con plantilla asíncrona (sin `create_all`), leyendo la URL desde la configuración de la aplicación
- Crear `.env.example` con todas las variables de entorno (sin secretos por defecto)
- Crear `requirements.txt` con las dependencias mínimas del stack (PyJWT y bcrypt, sin `passlib` ni `python-jose`)
- Crear `app/main.py` con dos grupos de rutas: Abierto (sin auth) y Protegido (con control de cambio de contraseña inyectado una sola vez a nivel de router)
- Dejar la base de seguridad (`security.py`, `dependencies.py`) con esqueletos tipados y explícitos, coherentes con el diseño de cookie HttpOnly
- Esqueleto de `seed.py` (datos reales se cargan en C-09)

**Non-Goals:**
- Implementar modelos de dominio (corresponde a C-02 `core-models`)
- Implementar las 6 capas de cada módulo (`models.py`, `schemas.py`, `repository.py`, `unit_of_work.py`, `service.py`, `router.py`): se crean en C-02 y en los changes que implementan cada módulo
- Implementar autenticación/autorización funcional (corresponde a C-03 `auth` y C-04 `usuarios-y-roles`)
- Implementar endpoints de negocio (corresponden a C-04 a C-08)
- Generar migraciones de tablas (se unifican en C-09: Migración 001 autogenerada + Migración 002 con disparador de sólo agregado)
- Ejecutar y validar `alembic upgrade head` / `alembic downgrade base` (C-09)
- Calcular el hash ficticio del login (diferido a C-03)
- Cargar datos iniciales (corresponde a C-09 `seed.py` completo)

## Decisions

**Estructura por módulo funcional con 6 capas estrictas** — Cada módulo (`usuarios`, `clientes`, `repuestos`, `ordenes`, `health`) contendrá sus propios `models.py`, `schemas.py`, `repository.py`, `unit_of_work.py`, `service.py`, `router.py`. Cada capa sabe lo suyo y nada más. Alternativa considerada: estructura por capa (todos los routers juntos, todos los modelos juntos). Rechazada porque el TP exige organización por módulo funcional y cada módulo debe ser autónomo. **En C-01 solo se crean los directorios y sus `__init__.py`**: los archivos de cada capa se agregan en C-02 y en los changes posteriores, para no adelantar lógica de dominio ni dejar archivos vacíos que aparenten implementación.

**Unit of Work como gestor de contexto asíncrono** — Confirma al salir del bloque, revierte si hay excepción, no cierra la sesión (no la creó). Ningún servicio construye su propio UoW; el router lo construye con una dependencia y se lo pasa al servicio. Ningún repositorio hace `commit()`, solo `flush()`. (Implementación en C-02.)

**Soft delete para vehículos y repuestos** — `SoftDeleteRepository[T]` hereda de `BaseRepository[T]`, filtra dados de baja y agrega `get_by_id_including_deleted` y `soft_delete`. Índices únicos parciales con `WHERE borrado_en IS NULL` para patente y código de repuesto (unicidad solo entre vigentes). (Implementación en C-02/C-05/C-06.)

**Motor y fábrica de sesiones creados en el lifespan** — No al importar un módulo, para evitar crear recursos antes de que exista el bucle de eventos. Se guardan en `app.state` y `get_session` toma la fábrica de `app.state`, entrega una sesión con `expire_on_commit=False` y la cierra al terminar. Si `app.state` no está inicializado, se lanza un `RuntimeError` explícito (no se crean recursos silenciosamente).

**Alembic solo configurado en C-01** — `migrations/env.py` queda con plantilla asíncrona, URL tomada de `app.core.config` (sin credenciales hardcodeadas) y `target_metadata = None`, porque todavía no existen modelos. La Migración 001 autogenerada (todas las tablas) y la Migración 002 escrita a mano (disparador de sólo agregado sobre `historial_estado_orden`, `movimiento_stock`, `historial_precio_repuesto`) se generan y validan en C-09. No se usa `create_all`.

**Bcrypt fuera del bucle de eventos** — `asyncio.to_thread` + semáforo que limita cuántas operaciones corren a la vez, tanto para `hash_password` como para `verify_password`. El hash se devuelve como `str` (se decodifica el `bytes` de bcrypt). Hash calculado antes de abrir la transacción.

**JWT solo en cookie `access_token`** con `HttpOnly`, `SameSite=Lax`, `Max-Age`; nunca en el cuerpo ni en `Authorization: Bearer`. Se firma con PyJWT (HS256) incluyendo `iat` y `exp`; el parámetro de expiración se aplica realmente.

**Hash ficticio del login diferido a C-03** — El diseño de C-03 exige comparar contra un hash ficticio cuando el correo no existe (para no filtrar qué usuarios existen). Ese hash se calcula una sola vez en el lifespan de C-03 y se guarda en `app.state`. C-01 no lo calcula ni lo sustituye por la clave JWT, porque obtener `SECRET_KEY` no equivale a un hash bcrypt.

## Risks / Trade-offs

[Driver asyncpg vs psycopg3] → El TP acepta ambos; la decisión se deja para la implementación (ver `10_preguntas_abiertas.md` IN-02). No bloquea este change.

[seed.py esqueleto vs completo] → Se deja esqueleto aquí; los datos reales (catálogo de estados, usuarios, clientes, vehículos, repuestos, órdenes) se cargan en C-09. Trade-off: C-02 a C-07 trabajan sobre una base vacía hasta que C-09 ejecute `seed.py`.

[Sin migraciones hasta C-09] → C-01 no puede validar `alembic upgrade`/`downgrade` sobre un esquema real porque la Migración 001 se autogenera en C-09. Trade-off: la configuración de Alembic se valida solo en carga/import, y la validación funcional queda formalmente en C-09.

[Aviso al cliente simulado con BackgroundTasks] → Se pierde si el proceso se reinicia; no hay reintento. Aceptado por el TP (capítulo 8 resuelve esto con Redis). No se implementa en este change.

## Migration Plan

1. Crear `requirements.txt` e instalar dependencias
2. Crear `.env` a partir de `.env.example` (sin secretos por defecto; la app no arranca si faltan)
3. Verificar que `migrations/env.py` carga la configuración y que `target_metadata` es `None` (no hay modelos todavía)
4. **C-09**: generar la Migración 001 con `alembic autogenerate` (esquema completo), escribir a mano la Migración 002 con los disparadores de solo agregado sobre `historial_estado_orden`, `movimiento_stock` y `historial_precio_repuesto`, y validar `alembic upgrade head` sobre base vacía, `alembic downgrade base` y un nuevo `alembic upgrade head` verificando que todo funcione
5. Rollback: `alembic downgrade base` elimina el esquema (C-09)

## Open Questions

(Ninguna — todas las decisiones de este change están resueltas en la KB y el CHANGES.md.)
