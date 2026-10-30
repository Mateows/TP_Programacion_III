# Arquitectura Propuesta

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|--------|--------------|---------|
| Unit of Work | `app/core/unit_of_work.py` + `app/modules/*/unit_of_work.py` | Confirmar o revertir al salir del bloque; ninguna escritura suelta |
| Repository | `app/core/repository.py` + `app/modules/*/repository.py` | Abstraer acceso a datos; `flush()` nunca `commit()` |
| Soft Delete Repository | `app/core/repository.py` (`SoftDeleteRepository[T]`) | Borrado lógico de vehículos y repuestos; filtrar dados de baja |
| Repository de sólo lectura | Catálogo `estado_orden` | Su PK no es `id`; desde la API no se escribe; no hereda de `BaseRepository` |
| Capas estrictas por módulo | Router → Service → UoW → Repository → Models → Schemas | Cada capa sabe lo suyo y nada más |
| Paginación envoltorio | `app/core/paginacion.py` | `{items, total, page, size, pages}` para listados |
| BackgroundTasks | `main.py` (lifespan) | Aviso al cliente simulado después de enviar la respuesta |

**Reglas de oro del patrón:**
- Ningún servicio construye su propio Unit of Work; el router lo construye y se lo pasa.
- Ningún repositorio hace `commit()`; solo `flush()`. El Unit of Work confirma.
- El Unit of Work no cierra la sesión (no la creó).
- Todas las lecturas usan carga anticipada declarada en el repositorio (sin N+1, sin carga perezosa).

## Estructura de directorios

```
proyecto/
├── app/
│   ├── main.py                      # Aplicación, lifespan, dos grupos de rutas (abierto y protegido)
│   ├── core/
│   │   ├── config.py                # Settings con pydantic-settings
│   │   ├── database.py              # Motor, fábrica de sesiones, get_session
│   │   ├── security.py              # Hash bcrypt fuera del bucle, emisión y verificación JWT
│   │   ├── dependencies.py          # Usuario actual, roles vigentes, cambio obligatorio, requiere_rol
│   │   ├── repository.py            # BaseRepository[T], SoftDeleteRepository[T]
│   │   ├── paginacion.py            # Envoltorio de listados y cálculo de páginas
│   │   └── unit_of_work.py          # UnitOfWork base (gestor de contexto async)
│   └── modules/
│       ├── health/
│       │   └── router.py
│       ├── usuarios/
│       │   ├── models.py            # Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad
│       │   ├── schemas.py
│       │   ├── repository.py
│       │   ├── unit_of_work.py
│       │   ├── service.py
│       │   └── router.py
│       ├── clientes/
│       │   ├── models.py            # Cliente, Vehiculo
│       │   ├── schemas.py
│       │   ├── repository.py
│       │   ├── unit_of_work.py
│       │   ├── service.py
│       │   └── router.py
│       ├── repuestos/
│       │   ├── models.py            # Repuesto, MovimientoStock, HistorialPrecioRepuesto
│       │   ├── schemas.py
│       │   ├── repository.py
│       │   ├── unit_of_work.py
│       │   ├── service.py
│       │   └── router.py
│       └── ordenes/
│           ├── models.py            # EstadoOrden, OrdenTrabajo, ItemOrden, HistorialEstadoOrden
│           ├── schemas.py
│           ├── repository.py        # EstadoOrden repository de sólo lectura
│           ├── unit_of_work.py
│           ├── service.py
│           └── router.py
├── migrations/
│   ├── env.py                       # Plantilla asíncrona de Alembic
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_inicial.py          # Autogenerada con autogenerate (todas las tablas)
│       └── 0002_solo_agregado.py    # Escrita a mano: disparador sobre las 3 tablas de sólo agregado
├── test/
│   ├── *.http                       # Casos de prueba (C-01 a C-19)
│   └── solo_agregado.sql            # Caso C-14: rechazos del disparador
├── seed.py                          # Carga datos iniciales (catálogo, usuarios, repuestos, órdenes)
├── requirements.txt
├── env.example                      # Variables sin secretos
├── .env                             # No versionado (secreto de firma, credenciales DB)
└── alembic.ini
```

## Seguridad

- **Autenticación**: contraseñas hasheadas con bcrypt (costo desde configuración, no fijo en código), bcrypt fuera del bucle de eventos (`to_thread`) bajo semáforo que limita cuántas corren a la vez. Token JWT firmado con `sub`, `iat` (sin truncar a segundos), `exp` y roles vigentes al emitirlo. Viaja solo en cookie `access_token` con `HttpOnly`, `Max-Age` igual a la duración del token, `Secure` configurable. Cuerpo del login no trae el token.
- **Autorización**: roles consultados en la base en cada petición (RN-04); 401 y 403 distinguidos. `requiere_rol` consulta `asignacion_rol` en cada petición. **Excepción**: `POST /ordenes/{id}/cancelar` no usa `requiere_rol` genérica — el dueño del vehículo puede cancelar su propia orden sin rol de personal; el servicio evalúa primero quién es y qué relación tiene con la orden (403), y recién después si el estado permite cancelarla (409).
- **Validación de input**: contratos de entrada con `extra="forbid"`; `exclude_unset` para PATCH parcial; longitud máxima 72 bytes en campos de bcrypt (bytes, no caracteres; una "ñ" ocupa dos).
- **Secrets management**: clave de firma de JWT y contraseña de base solo desde variables de entorno o `.env` (no versionado). Sin valores por defecto en el código; si faltan, la aplicación no arranca.

## Variables de entorno

| Variable | Descripción | Ejemplo | Sensible |
|----------|-------------|---------|----------|
| POSTGRES_USER | Usuario de la base de datos | `taller` | Sí |
| POSTGRES_PASSWORD | Contraseña de la base | `****` | Sí |
| POSTGRES_DB | Nombre de la base | `taller_db` | No |
| POSTGRES_HOST | Host de la base | `localhost` | No |
| POSTGRES_PORT | Puerto de la base | `5432` | No |
| SECRET_KEY | Clave de firma de JWT | `****` | Sí |
| BCRYPT_COST | Costo de bcrypt | `12` | No |
| SQL_ECHO | Habilitar logging de SQL | `true` | No |

La dirección de la base se arma con las variables sueltas `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` con un driver asíncrono (`postgresql+asyncpg` o `postgresql+psycopg`).

## Migraciones

- El esquema se crea exclusivamente con Alembic (plantilla asíncrona); **no se usa `create_all`**.
- Migración 1: generada con `autogenerate`, todas las tablas.
- Migración 2: escrita a mano, con el disparador de "sólo agregado" sobre `historial_estado_orden`, `movimiento_stock` y `historial_precio_repuesto` (RN-15), porque la comparación automática no ve funciones ni disparadores.
- Cada migración se lee antes de aplicarla y lleva un comentario que lo diga.
- `alembic upgrade head` sobre base vacía, `alembic downgrade base` y otra vez `upgrade head` deben funcionar.
- El catálogo `estado_orden` se crea vacío; sus filas las carga `seed.py`.
