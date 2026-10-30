# Proposal

## Why

C-01 dejó lista la infraestructura base (aplicación, configuración, motor async, seguridad y Alembic configurado), pero todavía no existe el modelo de datos persistente ni la capa de acceso a datos. Sin ellos, C-03 (auth) y los módulos de dominio no pueden implementarse sin improvisar persistencia y romper las reglas del proyecto: ningún repositorio hace `commit()`, el borrado de vehículos y repuestos es lógico, las lecturas usan carga anticipada y todas las fechas son `timestamptz`.

Este change define los contratos de persistencia y los primeros modelos de tabla, para que los changes posteriores construyan sobre una base única y coherente.

## What Changes

- `app/core/repository.py` — `TimestampMixin` con marcas temporales `timestamptz`; `BaseRepository[T]` con operaciones async y `flush()` (nunca `commit()`); `SoftDeleteRepository[T]` con filtro de registros dados de baja, `get_by_id_including_deleted` y `soft_delete`.
- `app/core/unit_of_work.py` — `UnitOfWork` base como gestor de contexto async: confirma al salir del bloque, revierte si hay excepción y no cierra la sesión (no la creó).
- `app/modules/usuarios/models.py` — modelos de tabla `Usuario`, `AsignacionRol`, `IntentoAcceso` y `EventoSeguridad`, con sus constraints e índices.
- `app/modules/ordenes/models.py` — modelo de tabla `EstadoOrden` (catálogo con PK `codigo`, `posicion` UNIQUE y `es_final`).
- Sin endpoints, sin schemas de request/response y sin migraciones: la Migración 001 se autogenera en C-09.
- No se usa `create_all` en ningún punto.

## Capabilities

### New Capabilities

- `gestion-de-usuarios`: modelo persistente de cuentas de usuario, asignaciones de rol con vigencia y revocación, intentos de acceso y eventos de seguridad.
- `estados-de-orden`: catálogo de estados del ciclo de vida de una orden de trabajo, con código como clave primaria, posición única e indicador de estado final.
- `acceso-a-datos`: contratos de repositorio y Unit of Work que garantizan `flush()` sin `commit()`, borrado lógico, carga anticipada y transacciones atómicas.

### Modified Capabilities

(Ninguna — no existen specs principales todavía; C-02 crea las primeras capacidades.)

## Impact

- Código nuevo: `app/core/repository.py`, `app/core/unit_of_work.py`, `app/modules/usuarios/models.py`, `app/modules/ordenes/models.py`.
- No se aplica ningún cambio de esquema en este change: la Migración 001 (todas las tablas) y la Migración 002 (disparadores de solo agregado) se generan y validan en C-09.
- Consumidores directos: C-03 `auth` y C-04 `usuarios-y-roles` (usuarios/roles/auditoría); C-05, C-06 y C-07 usarán los repositorios y el catálogo de estados.
- No se modifican endpoints, `app/main.py` ni la configuración de C-01.
