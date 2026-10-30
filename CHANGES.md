# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **TP Programación III — Taller mecánica: órdenes de trabajo, stock y acceso con FastAPI y PostgreSQL**.
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están en `openspec/changes/archive/`).
2. Leer los docs de la knowledge-base indicados en "Leer antes".
3. Ejecutar `/opsx:propose <nombre-del-change>`.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Al ejecutar `/opsx:archive <nombre-del-change>`, marcar el checkbox `[x]` en este archivo.

---

## Árbol de dependencias

```
C-01 foundation-setup
  └── C-02 core-models
        └── C-03 auth                          ← desbloquea TODO lo demás
              │
              ├── C-04 usuarios-y-roles
              ├── C-05 clientes-y-vehiculos    ← paralelo con C-04, C-06
              ├── C-06 repuestos-stock         ← paralelo con C-04, C-05
                    │
                    └── C-07 ordenes-de-trabajo  ← necesita C-03, C-04, C-05, C-06
                          │
                          └── C-08 consulta-cliente   ← depende directamente de C-07
              └── C-09 integracion-final-migraciones-validacion  ← depende de C-04, C-05, C-06, C-07, C-08
```

### Paralelismo por fase

> Cada "gate" es un punto de sincronización. Los changes dentro de un grupo pueden ejecutarse en paralelo.

```
GATE 0: ninguna
  → C-01 foundation-setup              [Agente A]

GATE 1: C-01 ✓
  → C-02 core-models                   [Agente A]

GATE 2: C-02 ✓
  → C-03 auth                          [Agente A]

GATE 3: C-03 ✓                     ← PRIMER FORK (3 paralelos)
  → C-04 usuarios-y-roles              [Agente B]
  → C-05 clientes-y-vehiculos          [Agente C]
  → C-06 repuestos-stock               [Agente B]

GATE 4: C-03 ✓, C-04 ✓, C-05 ✓, C-06 ✓
  → C-07 ordenes-de-trabajo            [Agente A — si C-03 ✓, C-04 ✓, C-05 ✓ y C-06 ✓]

GATE 5: C-07 ✓
  → C-08 consulta-cliente              [Agente C]

GATE 6: C-04 ✓, C-05 ✓, C-06 ✓, C-07 ✓, C-08 ✓
  → C-09 integracion-final-migraciones-validacion  [Agente C — si C-04 ✓, C-05 ✓, C-06 ✓, C-07 ✓ y C-08 ✓]
```

### Camino crítico (6 changes — mínimo irreducible)

```
C-01 → C-02 → C-03 → C-05 → C-07 → C-09 integracion-final-migraciones-validacion
```

> **Nota:** este camino crítico es **ilustrativo** (ruta secuencial mínima). Las ramas paralelas se ejecutan de forma concurrente: tras C-03, C-04, C-05 y C-06 pueden ejecutarse en paralelo; C-07 requiere que C-03, C-04, C-05 y C-06 estén listas; C-08 corre tras C-07; y C-09 integra una vez que C-04, C-05, C-06, C-07 y C-08 estén completas.

### Plan óptimo con 3 agentes

```
Paso │ Agente A (Backend Core) │ Agente B (Backend Aux) │ Agente C (Infra/Cliente)
─────┼─────────────────────────┼────────────────────────┼─────────────────────────
  1  │ C-01 foundation-setup   │         —              │         —
  2  │ C-02 core-models        │         —              │         —
  3  │ C-03 auth               │         —              │         —
  4  │         —               │ C-04 usuarios-y-roles  │ C-05 clientes-y-vehiculos
  5  │         —               │ C-06 repuestos-stock   │         —
  6  │ C-07 ordenes-de-trabajo │         —              │         —
  7  │         —               │         —              │ C-08 consulta-cliente
  8  │         —               │         —              │ C-09 integracion-final-migraciones-validacion
```

---

## FASE 0 — Cimientos / Infraestructura base

### [C-01] `foundation-setup`
- **Estado**: `[x]` completado
- **Scope**:
  - Estructura de directorios: `app/`, `app/core/`, `app/modules/{health,usuarios,clientes,repuestos,ordenes}/`, `migrations/versions/`, `test/`
  - `requirements.txt`: Python 3.12, FastAPI 0.111, SQLModel 0.0.24, SQLAlchemy 2.0 async, asyncpg/psycopg3, Alembic 1.13, pydantic-settings 2.0, bcrypt 4.0, PyJWT 2.8, uvicorn
  - `.env.example` con POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT, SECRET_KEY, BCRYPT_COST, SQL_ECHO
  - `app/main.py`: aplicación FastAPI, lifespan, dos grupos de rutas (abierto y protegido)
  - `app/core/config.py`: Settings con pydantic-settings
  - `app/core/database.py`: motor async, fábrica de sesiones, get_session
  - `app/core/security.py`: base de bcrypt (fuera del bucle) y JWT con PyJWT (cookie, no Bearer)
  - `app/core/dependencies.py`: esqueletos de usuario actual y roles (completos en C-03/C-04)
  - `alembic.ini`, `migrations/env.py` plantilla asíncrona, `migrations/script.py.mako` — solo configuración; no genera migraciones ni ejecuta `upgrade`/`downgrade` (se validan en C-09)
  - `seed.py` esqueleto
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/01_vision_y_objetivos.md` (qué es el sistema y por qué existe)
  - `knowledge-base/02_descripcion_general.md` §Stack tecnológico
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios, §Variables de entorno

---

## FASE 1 — Modelos core y migración inicial

### [C-02] `core-models`
- **Estado**: `[x]` completado
- **Verificación**: `pytest test/unit -q` → 51 passed; `openspec validate c-02-core-models --strict` → válido; `openspec status` → 31/31 tareas
- **Scope**:
  - Mixin con timestamps, `BaseRepository[T]`, `SoftDeleteRepository[T]` en `app/core/repository.py`
  - `app/core/unit_of_work.py`: UnitOfWork base (gestor de contexto async)
  - `app/modules/usuarios/models.py`: Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad
  - `app/modules/ordenes/models.py`: EstadoOrden (catálogo, PK=codigo, no es `id`)
  - Solo se definen modelos de tabla; la generación de migraciones se unifica en C-09
- **Dependencias**: C-01
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §entidades, §Seed data inicial
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones (Repository, UoW)
  - `knowledge-base/09_decisiones_y_supuestos.md` (DD-02, DD-03, DD-05)

---

## FASE 2 — Autenticación y acceso

### [C-03] `auth`
- **Estado**: `[x]` completado
- **Verificación**: `pytest test/unit -q` → 154 passed; `pytest test/integration -q` → 21 passed; `openspec validate c-03-auth --strict` → válido; `openspec status` → 4/4 artefactos, 38/38 tareas
- **Scope**:
  - `POST /auth/registro` — bcrypt hash (fuera del bucle con to_thread + semáforo), JWT en cookie HttpOnly, rate limiting 5/60s
  - `POST /auth/login` — intento_acceso, 429 sin verificar contraseña, hash real o ficticio, Set-Cookie con HttpOnly/SameSite/Max-Age
  - `POST /auth/logout` — borrar cookie de sesión
  - `GET /auth/yo` — usuario, roles vigentes, roles del token
  - `POST /auth/cambiar-password` — invalida sesiones previas (iat vs password_cambiada_en sin truncar)
  - Seguridad: JWT con sub/iat/exp/roles vigentes; bcrypt costo desde configuración; longitud máxima 72 bytes en campos bcrypt
  - No incluye migraciones (se unifican en C-09)
- **Dependencias**: C-02
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §Rutas de salud y autenticación
  - `knowledge-base/05_reglas_de_negocio.md` §Seguridad de acceso (RN-07, RN-08, RN-09)
  - `knowledge-base/07_flujos_principales.md` §Flujo 2: Login con límite de intentos

---

## FASE 3 — Gestión de personal, clientes y repuestos

> Los changes C-04, C-05 y C-06 pueden proponerse en paralelo tras C-03.

### [C-04] `usuarios-y-roles`
- **Estado**: `[x]` completado
- **Verificación**: `pytest test/unit -q` → 265 passed; `pytest test/integration -q` → 56 passed; `openspec validate c-04-usuarios-y-roles --strict` → válido; `openspec status` → 4/4 artefactos, 32/32 tareas
- **Scope**:
  - `POST /usuarios` — alta de personal (ADMIN), contraseña provisoria con cambio obligatorio y sin roles
  - `GET/POST/DELETE /usuarios/{id}/roles` — historial completo, asignación con vencimiento opcional y revocación sin borrar fila
  - `GET /eventos` — historial de seguridad paginado (ADMIN) con `app/core/paginacion.py`
  - `app/core/repository.py`: `contar()` genérico reutilizable por C-06 y C-07
  - Consume las dependencias de sesión y roles entregadas por C-03 (`get_current_user`, `requiere_rol`, `require_password_change`)
  - RN-03: una asignación abierta por rol (índice único parcial); la reasignación revoca la vencida con `flush` previo al `INSERT`
  - RN-05: no revocarse propio ADMIN; nunca quedar sin administradores vigentes
  - Registro en evento_seguridad con actor `USUARIO:{id}` en la misma unidad de trabajo
- **Dependencias**: C-03
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos
  - `knowledge-base/05_reglas_de_negocio.md` §Roles y autorización (RN-03, RN-04, RN-05)
  - `knowledge-base/07_flujos_principales.md` §Flujo 5: Cambio de rol de usuario

### [C-05] `clientes-y-vehiculos`
- **Estado**: `[x]` completado
- **Verificación**: `pytest test/unit -q` → 371 passed; `pytest test/integration -q` → 92 passed; `openspec validate c-05-clientes-y-vehiculos --strict` → válido; `openspec status` → 4/4 artefactos, 27/27 tareas
- **Scope**:
  - `app/modules/clientes/models.py`: `Cliente` (`usuario_id` nulo y único, `documento` único) y `Vehiculo` (`borrado_en`, `CHECK anio BETWEEN 1950 AND 2100`, índice único parcial `ix_vehiculo_patente_vigente`)
  - `POST /clientes` — RECEPCION, ADMIN; documento único (RN-01)
  - `GET /clientes/{id}` — con vehículos vigentes asociados
  - `POST /clientes/{id}/vehiculos` — patente única parcial (WHERE borrado_en IS NULL), normalizada (`strip` + `upper`), año 1950-2100
  - `DELETE /vehiculos/{id}` — borrado lógico `204`; no si tiene órdenes abiertas (RN-16), vía `VerificadorOrdenesAbiertas` inyectable cuya implementación real llega en C-07
  - `GET /mis-vehiculos` — cliente autenticado, solo propios (RN-17); `403` si la cuenta no tiene ficha
  - SoftDeleteRepository para vehículos
  - Cada clave foránea con índice explícito (PostgreSQL no lo crea solo)
  - `POST /auth/registro` extendido: exige `documento`, acepta `telefono` y crea la ficha de cliente junto con la cuenta y el rol `CLIENTE` en la misma unidad de trabajo (RN-02)
- **Dependencias**: C-03
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §clientes, §vehiculos
  - `knowledge-base/06_funcionalidades.md` §Épica 3: Clientes y vehículos (US-009 a US-013)
  - `knowledge-base/05_reglas_de_negocio.md` §Unicidad e integridad (RN-01, RN-16, RN-17)

### [C-06] `repuestos-stock`
- **Estado**: `[x]` completado
- **Verificación**: `pytest test/unit -q` → 505 passed; `pytest test/integration -q` → 150 passed; `openspec validate c-06-repuestos-stock --strict` → válido; `openspec status` → 4/4 artefactos, 25/25 tareas
- **Corrección post-implementación**: `GET /repuestos?q=` calculaba `total`/`pages` sin el filtro de búsqueda; ahora `RepuestoRepository.contar(texto=...)` comparte el filtro con `listar_paginado` y ambos lo ligan como parámetro
- **Scope**:
  - `app/modules/repuestos/models.py`: `Repuesto` (`borrado_en`, `CHECK precio > 0`, `CHECK stock >= 0`, índice único parcial `ix_repuesto_codigo_vigente`), `MovimientoStock` (`cantidad > 0`, tres FK indexadas, `orden_id` nula hasta C-07) e `HistorialPrecioRepuesto` (`CHECK precio_nuevo > 0`, `CHECK precio_nuevo > precio_anterior`)
  - `GET /repuestos` — búsqueda por descripción, paginación (page 1+, size 1-100, default 20); ADMIN, RECEPCION y MECANICO
  - `POST /repuestos` — ADMIN; código único parcial (normalizado `strip` + `upper`), precio > 0, stock >= 0; stock inicial como movimiento "Stock inicial" (RN-14)
  - `PATCH /repuestos/{id}` — exclude_unset; si cambia precio, línea en historial_precio_repuesto misma transacción (RN-20); bajar el precio → 409; no editar stock por PATCH
  - `POST /repuestos/{id}/reponer` — movimiento "Reposición" de stock (RN-14)
  - `GET /repuestos/{id}/movimientos`, `GET /repuestos/{id}/precios` — ADMIN
  - `DELETE /repuestos/{id}` — borrado lógico `204` (aplica SoftDeleteRepository para repuestos)
  - CHECK precio > 0, CHECK stock >= 0, CHECK precio_nuevo > precio_anterior
  - `PaginaResponse` y `PaginaFueraDeRango` movidos a `app/core/paginacion.py` (re-exportados desde `usuarios`)
- **Dependencias**: C-03
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §repuesto, §movimiento_stock, §historial_precio_repuesto
  - `knowledge-base/06_funcionalidades.md` §Épica 4: Repuestos y stock (US-014 a US-018)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-14, RN-20

---

## FASE 4 — Órdenes de trabajo

### [C-07] `ordenes-de-trabajo`
- **Estado**: `[x]` completado
- **Archivado**: `openspec/changes/archive/2026-10-29-c-07-ordenes-de-trabajo/`; capability `ordenes-de-trabajo` sincronizada en `openspec/specs/ordenes-de-trabajo/spec.md` (10 requisitos / 52 escenarios)
- **Verificación**: `pytest test/unit -q` → 693 passed; `pytest test/integration -q` → 201 passed; `openspec validate c-07-ordenes-de-trabajo --strict` → válido; `openspec status` → 4/4 artefactos, 29/29 tareas
- **Scope**:
  - `POST /ordenes` — RECEPCION, ADMIN; nace PENDIENTE, al menos un ítem, sin repuestos repetidos, precio copiado del repuesto, total calculado por servidor, primera línea historial (desde=null, hasta=PENDIENTE)
  - `GET /ordenes` — filtro por estado, paginación (ADMIN, RECEPCION, MECANICO)
  - `GET /ordenes/{id}` — detalle con carga anticipada (sin N+1), vehículo, cliente, ítems, repuestos, historial
  - `POST /ordenes/{id}/iniciar` — MECANICO; PENDIENTE → EN_REPARACION, queda asignado (RN-11)
  - `POST /ordenes/{id}/terminar` — mecánico asignado o ADMIN; UoW atómico; descuenta stock de cada ítem, movimiento por salida, línea historial; rollback completo si stock insuficiente (RN-13); BackgroundTasks aviso al cliente simulado
  - `POST /ordenes/{id}/cancelar` — RECEPCION, ADMIN o dueño del vehículo; PENDIENTE → CANCELADA; permiso antes que estado (403 antes 409)
  - `GET /estados-orden` - catálogo, autenticado, TERMINADA y CANCELADA marcadas como finales
  - Sustituir `SinOrdenesAbiertas` (dejado inyectable en C-05) por la consulta real a `orden_trabajo`/`estado_orden.es_final`, cerrando RN-16 sin cambiar el contrato HTTP de `DELETE /vehiculos/{id}`
  - modelos para la migración 001 unificada
- **Implementación efectiva**: módulo `app/modules/ordenes` (`models`, `schemas`, `errors`, `repository`, `service`, `router`, `verificacion`, `avisos`); `MOTIVO_CONSUMO_ORDEN = "Consumo por orden"` en `repuestos/motivos.py`; `GET /ordenes/{id}` permite al dueño del vehículo y responde `403` a un no-dueño autenticado; el detalle se resuelve con 3 consultas fijas; la terminación bloquea los repuestos con `SELECT ... FOR UPDATE` y valida el stock completo antes de mutar; el aviso al cliente se simula con `await asyncio.sleep(0.5)` y un mensaje en el log (SU-01). Sin migraciones, seed ni disparadores (C-09); sin `create_all` ni `Relationship`.
- **Dependencias**: C-03, C-04, C-05, C-06
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §órdenes-de-trabajo, §item_orden, §historial_estado_orden
  - `knowledge-base/06_funcionalidades.md` §Épica 5: Órdenes de trabajo (US-019 a US-026)
  - `knowledge-base/07_flujos_principales.md` §Flujo 3: Apertura de orden, §Flujo 4: Terminar orden

---

## FASE 5 — Consulta cliente, salud y seed

### [C-08] `consulta-cliente`
- **Estado**: `[x]` completado
- **Archivado**: `openspec/changes/archive/2026-10-29-c-08-consulta-cliente/`; capability `consulta-cliente` sincronizada en `openspec/specs/consulta-cliente/spec.md` (3 requisitos / 10 escenarios)
- **Scope**:
  - `GET /mis-ordenes` — paginación, sólo órdenes propias (RN-17)
  - Autorización de "lo propio": el cliente sólo puede consultar sus vehículos y las órdenes asociadas a ellos
  - La autorización de cancelación, incluido el orden 403 antes que 409, pertenece exclusivamente a C-07
  - `GET /ordenes/{id}` y `GET /estados-orden` son implementados en C-07; C-08 no los reimplementa
- **Dependencias**: C-03, C-05, C-07
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RN-17 (lo propio)
  - `knowledge-base/06_funcionalidades.md` §US-013, US-025, US-026
  - `knowledge-base/02_descripcion_general.md` §API REST (grupo protegido)

### [C-09] `integracion-final-migraciones-validacion`
- **Estado**: `[x]` completado (30/10/2026: migraciones `upgrade`/`downgrade`/`upgrade` a `0002 (head)`, `seed.py` OK, **19/19 casos C-01 a C-19 con 115/115 verificaciones**, **921 pytest passed**)
- **Scope**:
  - Etapa de integración amplia (no necesariamente un change de 4 a 6 horas como los demás): genera migraciones, corre seed.py y valida casos de prueba
  - Migración 001: autogenerada con `alembic autogenerate` (todas las tablas definidas de C-02 a C-07)
  - Migración 002: escrita a mano, disparador de "sólo agregado" sobre historial_estado_orden, movimiento_stock, historial_precio_repuesto (RN-15)
  - `seed.py` completo: catálogo estados, usuarios (admin, recepcion, mecanico, cliente), clientes, vehículos, repuestos con stock inicial, órdenes, historial precios, evento seguridad SISTEMA
  - `GET /health/live` — sin tocar DB, 200
  - `GET /health/ready` — `SELECT 1` contra la base, 200 / 503
  - Tests: C-01 a C-19 (archivos .http), solo_agregado.sql (caso C-14: rechazos del disparador)
  - Validación de migraciones (tareas trasladadas desde C-01, antes 4.2 y 4.3): ejecutar `alembic upgrade head` sobre base vacía, verificar la creación del esquema completo, ejecutar `alembic downgrade base`, ejecutar nuevamente `alembic upgrade head` y verificar que todas las operaciones funcionan
  - C-09 es el único change responsable de generar y validar las migraciones completas; C-01 solo deja la configuración de Alembic
- **Dependencias**: C-04, C-05, C-06, C-07, C-08
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §Migraciones
  - `knowledge-base/04_modelo_de_datos.md` §Seed data inicial
  - `knowledge-base/08_arquitectura_propuesta.md` §Migraciones, §Seguridad

---

## Checklist de validación al cerrar

- [x] El header dice "CHANGES — Secuencia de Implementación".
- [x] La sección "Cómo usar este documento" tiene los 5 pasos numerados.
- [x] El "Árbol de dependencias" usa ASCII art con `└──` y `│`.
- [x] Hay al menos un GATE por cada fork de paralelismo detectado (GATE 3 es PRIMER FORK).
- [x] El camino crítico tiene una flecha lineal sin ramas.
- [x] La tabla de "Plan óptimo con 3 agentes" tiene 3 columnas y los pasos enumerados.
- [x] Cada change tiene exactamente 5 campos: Estado, Scope, Dependencias, Governance, Leer antes.
- [x] Cada "Leer antes" tiene 3 a 5 archivos KB con sección cuando aplica.
- [x] El Scope tiene bullets operacionales (modelos, endpoints, migraciones, tests).
- [x] Cada Governance tiene uno de los 4 niveles: BAJO, MEDIO, ALTO, CRITICO.
- [x] Los changes están agrupados en FASES con nombres semánticos.

---

## Resumen

✅ `CHANGES.md` creado en la raíz con **9 changes** organizados en **6 fases**.

**Camino crítico**: 6 changes (C-01 → C-02 → C-03 → C-05 → C-07 → C-09)
**Gates de paralelismo**: 7 (GATE 0 a GATE 6)
**Primer change recomendado**: `C-01` (foundation-setup)

Para arrancar: `/opsx:propose C-01-foundation-setup`