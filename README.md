# API Taller Mecánico

**Grupo:** No hay Token que aguante  
**Integrantes:** Mateo Liendo

---

API REST asincrónica para la gestión diaria de un taller mecánico: **clientes, vehículos, órdenes de trabajo y stock de repuestos**, con autenticación por cookie `HttpOnly` y autorización por roles decidida en la base de datos en cada petición.

Es el trabajo práctico integrador de las unidades 1 a 6 de **Programación III** («del objeto a la transacción»). El alcance es el backend: no hay frontend propio; la web del taller sería un cliente externo que consume esta API.

---

## Índice

1. [Descripción](#descripción)
2. [Estado del proyecto](#estado-del-proyecto)
3. [Stack tecnológico](#stack-tecnológico)
4. [Arquitectura](#arquitectura)
5. [Estructura de directorios](#estructura-de-directorios)
6. [Puesta en marcha](#puesta-en-marcha)
7. [Variables de entorno](#variables-de-entorno)
8. [Autenticación y autorización](#autenticación-y-autorización)
9. [Endpoints](#endpoints)
10. [Modelo de datos](#modelo-de-datos)
11. [Migraciones](#migraciones)
12. [Datos iniciales (seed)](#datos-iniciales-seed)
13. [Casos de prueba](#casos-de-prueba)
14. [Documentación interna](#documentación-interna)

---

## Descripción

El sistema modela el circuito completo del taller:

- **Recepción** da de alta clientes y vehículos y abre una orden por cada ingreso, con la falla y los repuestos a usar.
- **Mecánico** toma (inicia) la orden, la repara y la da por terminada; al terminarla se descuenta el stock de cada repuesto usado en una sola transacción.
- **Administrador** mantiene el catálogo de repuestos, repone stock, cambia precios con historial, y administra personal y roles.
- **Cliente** se auto-registra y consulta el estado de sus propios vehículos y sus órdenes.
- **Sistema** registra eventos de seguridad con el actor `'SISTEMA'`.

La integridad se delega a PostgreSQL: claves foráneas, `CHECK`, índices únicos parciales para el borrado lógico y los roles vigentes, un catálogo de estados y un disparador de **sólo agregado** sobre tres tablas de auditoría.

---

## Estado del proyecto

| ID | Change | Estado | Fase |
|---|---|---|---|
| C-01 | `foundation-setup` | ✓ completado | 0 — Cimientos |
| C-02 | `core-models` | ✓ completado | 1 — Modelos |
| C-03 | `auth` | ✓ completado | 2 — Autenticación |
| C-04 | `usuarios-y-roles` | ✓ completado | 3 — Personal y roles |
| C-05 | `clientes-y-vehiculos` | ✓ completado | 3 — Dominio |
| C-06 | `repuestos-stock` | ✓ completado | 3 — Dominio |
| C-07 | `ordenes-de-trabajo` | ✓ completado | 4 — Dominio |
| C-08 | `consulta-cliente` | ✓ completado | 5 — Cliente |
| C-09 | `integracion-final-migraciones-validacion` | ✓ completado | 6 — Entrega |

**9 de 9 changes completados y archivados** en `openspec/changes/archive/`. La validación final cubre 19 casos (C-01 a C-19) con 115/115 verificaciones y 921 pruebas automatizadas en verde.

---

## Stack tecnológico

| Capa | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.12 |
| Framework web | FastAPI | 0.111 |
| Modelos de tabla | SQLModel | 0.0.24 |
| Motor / sesión async | SQLAlchemy | 2.0 (asíncrono) |
| Driver PostgreSQL | asyncpg | 0.30 |
| Base de datos | PostgreSQL | 16 |
| Migraciones | Alembic | 1.13 (plantilla asíncrona) |
| Configuración | pydantic-settings | 2.0 |
| Hash de contraseñas | bcrypt | 4.0 |
| Token firmado | PyJWT | 2.8 (HS256) |
| Servidor ASGI | uvicorn | 0.29 |

---

## Arquitectura

Arquitectura **en capas** con flujo de una sola dirección por petición:

```
Petición HTTP
     │
     ▼
┌──────────────────────────────────────────────────┐
│ main.py — FastAPI + lifespan                     │
│   grupo abierto (/health, /auth)                 │
│   grupo protegido (resto de endpoints)           │
└──────────────────────────────────────────────────┘
     │
     ▼
router.py  ── arma el UoW con una dependencia y lo pasa CERRADO
     │         traduce errores de dominio a códigos HTTP
     ▼
service.py ── reglas de negocio; abre el UoW con `async with`
     │         nunca construye el UoW directamente
     ▼
unit_of_work.py ── commit al salir sin excepción / rollback con excepción
     │             no cierra la sesión (no la creó)
     ▼
repository.py ── add/update → flush() y nada más; nunca commit()
     │            lecturas con JOIN explícitos (sin lazy loading, sin N+1)
     ▼
models.py (SQLModel) ── PostgreSQL 16
```

Principios que sostienen el diseño:

- **Un solo punto de confirmación.** `UnitOfWork.__aexit__` hace `commit()` si el bloque terminó bien y `rollback()` si salió con excepción. Los repositorios hacen `flush()` para obtener la PK y **nunca** `commit()`.
- **Sin carga perezosa.** Las lecturas que necesitan relaciones las precargan con `JOIN` explícitos en el repositorio, con un número fijo de consultas independiente de la cantidad de ítems (verificado en el caso C-15).
- **Esquema solo por Alembic.** `create_all` está prohibido; el esquema se crea únicamente con `alembic upgrade head`.
- **Autorización en cada petición.** Los roles vigentes se consultan en la base en cada petición (no desde el token); revocar un rol surte efecto de inmediato.

---

## Estructura de directorios

```
TP_Programacion_III/
├── app/
│   ├── main.py                  # FastAPI, lifespan, dos grupos de rutas
│   ├── core/
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── database.py          # Motor async, fábrica de sesiones, get_session
│   │   ├── dependencies.py      # get_current_user, requiere_rol, require_password_change
│   │   ├── paginacion.py        # PaginaResponse, ParametrosPagina, PaginaFueraDeRango
│   │   ├── repository.py        # BaseRepository[T], SoftDeleteRepository[T]
│   │   ├── security.py          # bcrypt fuera del bucle + JWT (crear / verificar)
│   │   └── unit_of_work.py      # UnitOfWork: commit/rollback, no cierra sesión
│   └── modules/
│       ├── health/
│       │   └── router.py        # GET /health/live  GET /health/ready
│       ├── auth/
│       │   └── router.py        # POST /auth/registro  login  logout  yo  cambiar-password
│       ├── usuarios/
│       │   ├── models.py        # usuario, asignacion_rol, intento_acceso, evento_seguridad
│       │   ├── schemas.py
│       │   ├── repository.py
│       │   ├── service.py
│       │   └── router.py        # /usuarios  /eventos
│       ├── clientes/
│       │   ├── models.py        # cliente, vehiculo
│       │   ├── schemas.py
│       │   ├── repository.py
│       │   ├── service.py
│       │   └── router.py        # /clientes  /vehiculos  /mis-vehiculos
│       ├── repuestos/
│       │   ├── models.py        # repuesto, movimiento_stock, historial_precio_repuesto
│       │   ├── schemas.py
│       │   ├── repository.py
│       │   ├── service.py
│       │   └── router.py        # /repuestos
│       └── ordenes/
│           ├── models.py        # estado_orden, orden_trabajo, item_orden, historial_estado_orden
│           ├── schemas.py
│           ├── repository.py
│           ├── service.py
│           ├── router.py        # /ordenes  /estados-orden  /mis-ordenes
│           ├── avisos.py        # Aviso simulado con BackgroundTasks
│           ├── errors.py
│           └── verificacion.py  # VerificadorOrdenesAbiertas (RN-16)
├── migrations/
│   ├── env.py                   # Plantilla asíncrona; URL desde Settings
│   └── versions/
│       ├── 0001_inicial.py      # 13 tablas (autogenerado con Alembic)
│       └── 0002_solo_agregado.py# Disparadores de inmutabilidad (escrito a mano)
├── test/
│   ├── casos_de_prueba.http     # Casos C-01 a C-19 para REST Client
│   ├── solo_agregado.sql        # Validación de triggers y FK (caso C-14)
│   └── evidencia_c09.md         # Resultados de la validación final
├── knowledge-base/              # 10 documentos de dominio
├── openspec/
│   ├── specs/                   # Capacidades especificadas
│   └── changes/archive/         # C-01 a C-09 archivados
├── seed.py                      # Carga de datos iniciales
├── alembic.ini
├── requirements.txt
├── CHANGES.md                   # Roadmap de los 9 changes
└── .env.example                 # Variables documentadas sin secretos
```

Cada módulo sigue la misma arquitectura de seis capas: **Router → Service → UoW → Repository → Models → Schemas**.

---

## Puesta en marcha

### Requisitos previos

- Python 3.12
- PostgreSQL 16 corriendo localmente
- Una base de datos creada (por defecto `taller_db`)

### 1. Crear el entorno virtual e instalar dependencias

```powershell
# Windows
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# Linux / macOS
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```powershell
# Windows
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

Editar `.env` con los datos de PostgreSQL y generar una `SECRET_KEY` aleatoria:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Aplicar las migraciones

```powershell
# Windows
.\.venv\Scripts\python.exe -m alembic upgrade head

# Linux / macOS
.venv/bin/python -m alembic upgrade head
```

### 4. Cargar los datos iniciales

```powershell
# Windows
.\.venv\Scripts\python.exe seed.py

# Linux / macOS
.venv/bin/python seed.py
```

### 5. Levantar el servidor

```powershell
# Windows
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Linux / macOS
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- API: http://127.0.0.1:8000
- Documentación interactiva (Swagger): http://127.0.0.1:8000/docs

---

## Variables de entorno

Definidas en `app/core/config.py` y documentadas en `.env.example`.

| Variable | Obligatoria | Default | Descripción |
|---|---|---|---|
| `POSTGRES_USER` | No | `postgres` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | **Sí** | — | Contraseña de PostgreSQL; sin ella la app no arranca |
| `POSTGRES_DB` | No | `taller_db` | Base de datos |
| `POSTGRES_HOST` | No | `localhost` | Host de la base |
| `POSTGRES_PORT` | No | `5432` | Puerto de la base |
| `SECRET_KEY` | **Sí** | — | Clave de firma del JWT (HS256); sin ella la app no arranca |
| `BCRYPT_COST` | No | `12` | Costo de bcrypt |
| `JWT_EXPIRES_MINUTES` | No | `30` | Duración del JWT y `Max-Age` de la cookie |
| `COOKIE_SECURE` | No | `false` | Atributo `Secure` de la cookie (`true` en producción con TLS) |
| `SQL_ECHO` | No | `false` | Muestra las consultas SQL en consola (útil para diagnosticar N+1) |
| `LOGIN_MAX_INTENTOS` | No | `5` | Intentos fallidos antes del 429 |
| `LOGIN_VENTANA_SEGUNDOS` | No | `60` | Ventana de tiempo del rate limiting |

`.env` **no se versiona** (está en `.gitignore`). No hay credenciales en el repositorio.

---

## Autenticación y autorización

### Sesión: cookie `access_token`

El JWT viaja **únicamente** en la cookie `access_token`, nunca en el cuerpo de la respuesta ni en un header `Authorization: Bearer`.

| Atributo | Valor |
|---|---|
| `HttpOnly` | Sí — no accesible desde JavaScript |
| `SameSite` | `Lax` |
| `Secure` | según `COOKIE_SECURE` (`false` en desarrollo) |
| `Max-Age` | `JWT_EXPIRES_MINUTES × 60` |

### Token JWT

Firmado con HS256. Claims: `sub` (id del usuario), `iat` (emisión, sin truncar), `exp` (vencimiento) y `roles` (informativos — nunca autorizan por sí solos).

### Los cuatro roles

`ADMIN`, `RECEPCION`, `MECANICO`, `CLIENTE`. Viven en la tabla `asignacion_rol`, no en una columna de `usuario`. Un rol está **vigente** si no está revocado (`revocada_en IS NULL`) y no venció (`vence_en` nulo o futuro).

### Autorización en cada petición

Los roles se consultan en la base en cada petición (RN-04). Revocar un rol quita el permiso de inmediato, sin esperar a que venza el token.

### Dos grupos de rutas

| Grupo | Rutas | Exige |
|---|---|---|
| **Abierto** | `/health/*`, `/auth/*` | Nada (algunas rutas dentro de `/auth` exigen sesión por su cuenta) |
| **Protegido** | Todo lo demás | Sesión válida → 401; `debe_cambiar_password = false` → 403 |

### Reglas de seguridad clave

- **RN-07** — El cambio de contraseña invalida las sesiones anteriores. `iat` se compara con `password_cambiada_en` sin truncar.
- **RN-08** — Después de 5 fallos del mismo `(email, ip)` en 60 s, el login responde 429 con `Retry-After` sin verificar ningún hash.
- **RN-09** — Correo inexistente y contraseña incorrecta devuelven el mismo 401 y tardan parecido (hash ficticio).

---

## Endpoints

Todas las rutas del grupo protegido responden además **401** sin sesión y **403** con cambio de contraseña pendiente.

### Grupo abierto

| Método | Ruta | Descripción | Códigos |
|---|---|---|---|
| GET | `/health/live` | Liveness — no toca la base | `200` |
| GET | `/health/ready` | Readiness — ejecuta `SELECT 1` | `200`, `503` |
| POST | `/auth/registro` | Auto-registro: usuario + rol CLIENTE + ficha de cliente en un solo UoW | `201`, `409`, `422` |
| POST | `/auth/login` | Inicia sesión; JWT en cookie, nunca en el cuerpo | `200`, `401`, `422`, `429` |
| POST | `/auth/logout` | Borra la cookie `access_token` | `200` |
| GET | `/auth/yo` | Datos de la sesión, roles vigentes (base) y roles del token | `200`, `401` |
| POST | `/auth/cambiar-password` | Verifica la actual, cambia e invalida sesiones previas | `200`, `401`, `422` |

### Módulo `usuarios`

| Método | Ruta | Rol | Descripción | Códigos |
|---|---|---|---|---|
| POST | `/usuarios` | ADMIN | Alta de personal con contraseña provisoria | `201`, `409`, `422` |
| GET | `/usuarios/{id}/roles` | ADMIN | Historial completo de roles (incluye revocados) | `200`, `404` |
| POST | `/usuarios/{id}/roles` | ADMIN | Asigna un rol con vencimiento opcional | `201`, `404`, `409`, `422` |
| DELETE | `/usuarios/{id}/roles/{rol}` | ADMIN | Revoca el rol (escribe `revocada_en`, no borra) | `200`, `404`, `409` |
| GET | `/eventos` | ADMIN | Historial de seguridad paginado | `200`, `422` |

### Módulo `clientes`

| Método | Ruta | Rol | Descripción | Códigos |
|---|---|---|---|---|
| POST | `/clientes` | ADMIN, RECEPCION | Alta de ficha de cliente | `201`, `409`, `422` |
| GET | `/clientes/{id}` | ADMIN, RECEPCION | Ficha con vehículos vigentes | `200`, `404` |
| POST | `/clientes/{id}/vehiculos` | ADMIN, RECEPCION | Alta de vehículo | `201`, `404`, `409`, `422` |
| DELETE | `/vehiculos/{id}` | ADMIN, RECEPCION | Baja lógica; 409 si tiene órdenes abiertas (RN-16) | `204`, `404`, `409` |
| GET | `/mis-vehiculos` | autenticado | Vehículos propios del cliente autenticado (RN-17) | `200` |

### Módulo `repuestos`

| Método | Ruta | Rol | Descripción | Códigos |
|---|---|---|---|---|
| GET | `/repuestos` | ADMIN, RECEPCION, MECANICO | Listado paginado con búsqueda por descripción (`q`) | `200`, `422` |
| POST | `/repuestos` | ADMIN | Alta con stock inicial como movimiento (RN-14) | `201`, `409`, `422` |
| PATCH | `/repuestos/{id}` | ADMIN | Edita descripción o precio; el precio deja historial (RN-20) | `200`, `404`, `422` |
| DELETE | `/repuestos/{id}` | ADMIN | Baja lógica | `204`, `404` |
| POST | `/repuestos/{id}/reponer` | ADMIN | Reposición de stock con movimiento (RN-14) | `200`, `404`, `422` |
| GET | `/repuestos/{id}/movimientos` | ADMIN | Historial de movimientos de stock | `200`, `404`, `422` |
| GET | `/repuestos/{id}/precios` | ADMIN | Historial de cambios de precio | `200`, `404`, `422` |

### Módulo `ordenes`

| Método | Ruta | Rol | Descripción | Códigos |
|---|---|---|---|---|
| POST | `/ordenes` | ADMIN, RECEPCION | Alta PENDIENTE con ≥ 1 ítem; precio copiado y total calculado por servidor (RN-10) | `201`, `409`, `422` |
| GET | `/ordenes` | ADMIN, RECEPCION, MECANICO | Listado paginado con filtro por estado | `200`, `422` |
| GET | `/ordenes/{id}` | personal o dueño del vehículo | Detalle completo con carga anticipada (3 consultas fijas) | `200`, `403`, `404` |
| POST | `/ordenes/{id}/iniciar` | MECANICO | `PENDIENTE → EN_REPARACION`; queda asignado (RN-11) | `200`, `403`, `404`, `409` |
| POST | `/ordenes/{id}/terminar` | MECANICO asignado o ADMIN | `EN_REPARACION → TERMINADA`; descuenta stock atómicamente (RN-13) | `200`, `403`, `404`, `409` |
| POST | `/ordenes/{id}/cancelar` | ADMIN, RECEPCION o dueño | `PENDIENTE → CANCELADA`; permiso antes que estado (RN-12) | `200`, `403`, `404`, `409` |
| GET | `/estados-orden` | autenticado | Catálogo de estados ordenado por posición | `200` |
| GET | `/mis-ordenes` | autenticado | Órdenes propias del cliente autenticado, paginado (RN-17) | `200`, `403`, `422` |

---

## Modelo de datos

13 tablas agrupadas por módulo. Todas las fechas son `timestamptz`, el dinero es `NUMERIC`/`Decimal` (nunca `float`), y toda clave foránea lleva índice explícito.

### Identidad y accesos

| Tabla | Descripción | Restricciones clave |
|---|---|---|
| `usuario` | Cuenta de acceso; el rol **no** es columna | `email` UNIQUE; `password_cambiada_en` timestamptz |
| `asignacion_rol` | Rol con vigencia e historial | CHECK `rol IN (...)` ; único parcial `(usuario_id, rol) WHERE revocada_en IS NULL` |
| `intento_acceso` | Cada intento de login | Índice `(email, ip, cuando)` |
| `evento_seguridad` | Auditoría; `actor` es texto, no FK | — |

### Clientes

| Tabla | Descripción | Restricciones clave |
|---|---|---|
| `cliente` | Ficha de cliente, con o sin cuenta | `usuario_id` UNIQUE y nullable; `documento` UNIQUE |
| `vehiculo` | Vehículo con borrado lógico | Único parcial `(patente) WHERE borrado_en IS NULL`; CHECK `anio BETWEEN 1950 AND 2100` |

### Repuestos e inventario

| Tabla | Descripción | Restricciones clave |
|---|---|---|
| `repuesto` | Catálogo con borrado lógico | Único parcial `(codigo) WHERE borrado_en IS NULL`; CHECK `precio > 0`, `stock >= 0` |
| `movimiento_stock` | Punto único de escritura del stock | CHECK `cantidad > 0`; **sólo agregado** |
| `historial_precio_repuesto` | Cada cambio de precio | CHECK `precio_nuevo > 0` y `precio_nuevo > precio_anterior`; **sólo agregado** |

### Órdenes de trabajo

| Tabla | Descripción | Restricciones clave |
|---|---|---|
| `estado_orden` | Catálogo de estados; cargado por `seed.py` | PK `codigo` (no `id`); `posicion` UNIQUE; `es_final` boolean |
| `orden_trabajo` | Orden de un vehículo | `estado` FK a `estado_orden.codigo`; CHECK `total >= 0` |
| `item_orden` | Repuesto usado en la orden (composición) | UNIQUE `(orden_id, repuesto_id)`; CHECK `cantidad > 0` y `precio_unitario > 0` |
| `historial_estado_orden` | Transición de estado | FKs `desde_estado`/`hasta_estado` al catálogo; **sólo agregado** |

### Los tres índices únicos parciales

| Tabla | Índice | `WHERE` | Para qué |
|---|---|---|---|
| `asignacion_rol` | `(usuario_id, rol)` | `revocada_en IS NULL` | A lo sumo una asignación abierta por rol |
| `vehiculo` | `(patente)` | `borrado_en IS NULL` | La patente se reutiliza tras la baja |
| `repuesto` | `(codigo)` | `borrado_en IS NULL` | El código se reutiliza tras la baja |

### Tablas de sólo agregado

`historial_estado_orden`, `movimiento_stock` y `historial_precio_repuesto` rechazan `UPDATE` y `DELETE` mediante un disparador PL/pgSQL creado por la migración `0002`. `INSERT` sigue permitido; el disparador aplica sin importar el origen (API, seed o `psql`).

---

## Migraciones

Alembic con **plantilla asíncrona**. La URL sale de `Settings`; `create_all` está prohibido.

| Revisión | Archivo | Qué hace |
|---|---|---|
| `0001` | `0001_inicial.py` | Autogenerada: 13 tablas, CHECK, FK, índices y los tres `postgresql_where` para los índices únicos parciales |
| `0002` | `0002_solo_agregado.py` | Escrita a mano: función PL/pgSQL y disparadores `BEFORE UPDATE OR DELETE` sobre las tres tablas de sólo agregado (RN-15). El `downgrade` borra disparadores y función |

Ciclo de verificación:

```powershell
alembic upgrade head      # aplica todo
alembic downgrade base    # revierte todo (tablas + disparadores)
alembic upgrade head      # re-aplica (idempotencia verificada)
```

---

## Datos iniciales (seed)

`seed.py` deja la base en un estado conocido y reproducible. Vacía las 13 tablas con `TRUNCATE ... RESTART IDENTITY CASCADE` (no dispara los triggers de sólo agregado, que son `FOR EACH ROW` sobre `UPDATE`/`DELETE`) y recarga todo en un solo Unit of Work.

### Usuarios de prueba

Todos usan la contraseña `Secreto123!`.

| Email | Rol | Notas |
|---|---|---|
| `admin@example.com` | ADMIN | Administrador principal |
| `admin2@example.com` | ADMIN | Segundo administrador |
| `recepcion@example.com` | RECEPCION | |
| `mecanico@example.com` | MECANICO | Asignado a la orden 2 del seed |
| `mecanico2@example.com` | MECANICO | |
| `cliente@example.com` | CLIENTE | Ficha: Laura Cliente |
| `nuevo@example.com` | MECANICO | `debe_cambiar_password = true` |

### Resto del estado inicial

| Qué | Datos |
|---|---|
| `estado_orden` | PENDIENTE (1), EN_REPARACION (2), TERMINADA (3, final), CANCELADA (4, final) |
| Clientes | Laura (`30111222`, con cuenta `cliente@example.com`); Jorge (`28999888`, sin cuenta) |
| Vehículos | Toyota Corolla 2020 y Ford Focus 2018 (Laura); Chevrolet Onix 2019 (Jorge) |
| Repuestos | Filtro de aceite (stock 10, $8500), Pastillas de freno (4, $32000), Bujía (2, $5000), Aceite 5W30 (20, $12000) |
| Movimientos | Un movimiento «Stock inicial» por cada repuesto |
| Órdenes | Orden 1 PENDIENTE (vehículo de Laura); Orden 2 EN_REPARACION (vehículo de Jorge, asignada al mecánico, con 4 bujías cuando hay 2 en stock — insumo del caso C-11) |
| Historial de precios | Filtro de aceite: de $8000 a $8500 |
| Evento de seguridad | `actor='SISTEMA'`, «Carga de los datos iniciales» |

---

## Casos de prueba

### `test/casos_de_prueba.http`

19 casos (C-01 a C-19) listos para ejecutar con la extensión **REST Client** de VS Code, contra la API levantada con el seed cargado. Cubren autenticación, autorización, ciclo completo de órdenes, control de stock, paginación y casos borde.

### `test/solo_agregado.sql`

Valida los 6 rechazos de los disparadores de inmutabilidad (RN-15) y el rechazo por clave foránea inválida (caso C-14). Cada intento abre una transacción y la revierte con `ROLLBACK`; el script es re-ejecutable y no deja cambios.

```powershell
$env:PGPASSWORD='tu_password'
& psql -h localhost -U postgres -d taller_db -f test/solo_agregado.sql
```

### Resultado de la validación final

Documentado en `test/evidencia_c09.md`:

- **19/19 casos** completados con **115/115 verificaciones** OK.
- Ciclo de migraciones `upgrade → downgrade → upgrade` verificado.
- Caso C-15 (conteo fijo de consultas): **5 SELECT** tanto con 2 ítems como con 4 ítems en el detalle de una orden.

---

## Documentación interna

| Documento | Contenido |
|---|---|
| [`knowledge-base/01_vision_y_objetivos.md`](knowledge-base/01_vision_y_objetivos.md) | Propósito, objetivos por actor, alcance y criterios de éxito |
| [`knowledge-base/02_descripcion_general.md`](knowledge-base/02_descripcion_general.md) | Stack, arquitectura en capas y referencia de endpoints |
| [`knowledge-base/03_actores_y_roles.md`](knowledge-base/03_actores_y_roles.md) | Actores, matriz RBAC completa y rutas públicas |
| [`knowledge-base/04_modelo_de_datos.md`](knowledge-base/04_modelo_de_datos.md) | 13 entidades, ERD, índices parciales y seed |
| [`knowledge-base/05_reglas_de_negocio.md`](knowledge-base/05_reglas_de_negocio.md) | RN-01 a RN-20 con su garante técnico |
| [`knowledge-base/06_funcionalidades.md`](knowledge-base/06_funcionalidades.md) | Historias de usuario por épica |
| [`knowledge-base/07_flujos_principales.md`](knowledge-base/07_flujos_principales.md) | Flujos extremo a extremo |
| [`knowledge-base/08_arquitectura_propuesta.md`](knowledge-base/08_arquitectura_propuesta.md) | Patrones, estructura de directorios, seguridad y variables |
| [`knowledge-base/09_decisiones_y_supuestos.md`](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones DD-01 a DD-05 y supuestos SU-01 a SU-05 |
| [`CHANGES.md`](CHANGES.md) | Roadmap: 9 changes, dependencias, gates y camino crítico |
| [`openspec/`](openspec/) | Specs de capacidades y changes archivados |
