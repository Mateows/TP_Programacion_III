# Proposal

## Why

El catálogo de estados existe desde C-02, pero no hay órdenes: el taller no puede registrar una reparación, asignarla, consumir stock ni cerrarla, y la baja de vehículos no puede bloquearse por órdenes abiertas (RN-16) porque `SinOrdenesAbiertas` siempre responde cero. C-07 implementa el ciclo de vida completo de la orden de trabajo, que es el núcleo operativo del sistema y de lo que dependen C-08 y C-09.

## What Changes

- **Modelos nuevos** en `app/modules/ordenes/models.py`: `OrdenTrabajo` (vehículo, mecánico opcional, estado FK, falla, total `NUMERIC(12,2)` calculado por el servidor, `creada_en`), `ItemOrden` (cantidad, precio unitario copiado, `UNIQUE (orden_id, repuesto_id)`, CHECKs de cantidad y precio) e `HistorialEstadoOrden` (sólo agregado, `desde_estado` nullable, `hasta_estado`, actor y momento). Todas las FK indexadas, fechas `timestamptz`, dinero `Decimal`.
- **`POST /ordenes`** (ADMIN, RECEPCION): nace `PENDIENTE` con al menos un ítem, sin repuestos repetidos, precio copiado del repuesto y total calculado por el servidor; escribe la primera línea `null → PENDIENTE`. `201`/`403`/`409` (repuesto o vehículo inexistente o dado de baja, catálogo de estados vacío)/`422` (cuerpo inválido, ítem repetido).
- **`GET /ordenes`** (ADMIN, RECEPCION, MECANICO): filtro opcional por `estado` validado contra el catálogo (`422` si no existe), paginación `page`/`size` con `PaginaResponse`.
- **`GET /ordenes/{id}`** (personal o dueño del vehículo): detalle con vehículo, cliente, ítems, repuestos e historial, con carga anticipada y sin N+1; `403` para autenticado sin permiso, `404` si no existe.
- **`POST /ordenes/{id}/iniciar`** (sólo MECANICO): `PENDIENTE → EN_REPARACION` y el actor queda asignado; `403` sin rol MECANICO, `404`, `409` si el estado no lo permite.
- **`POST /ordenes/{id}/terminar`** (mecánico asignado o ADMIN): autorización (`403`) antes que estado (`409`); descuenta stock de cada ítem, deja un movimiento de salida con `orden_id` y una línea `EN_REPARACION → TERMINADA`, todo en un solo Unit of Work; stock insuficiente → `409` sin ninguna escritura.
- **`POST /ordenes/{id}/cancelar`** (ADMIN, RECEPCION o dueño del vehículo): permiso (`403`) antes que estado (`409`); sólo desde `PENDIENTE` hacia `CANCELADA`; el dueño cancela sin rol de personal.
- **`GET /estados-orden`** (cualquier autenticado): catálogo ordenado por posición con `es_final`; `401` sin sesión. Sin escritura desde la API.
- **Consumo de stock**: nuevo motivo compartido `MOTIVO_CONSUMO_ORDEN` en `app/modules/repuestos/motivos.py`; el movimiento conserva `cantidad` positiva y referencia la orden.
- **RN-16 real**: se reemplaza `SinOrdenesAbiertas` por un verificador que consulta `orden_trabajo` unida a `estado_orden.es_final`; la baja de vehículo con órdenes no finales responde `409` sin cambiar el contrato HTTP existente. La regla ya está especificada en `clientes-y-vehiculos`, por lo que el comportamiento no cambia: sólo se completa su implementación.
- **Aviso al cliente simulado** al terminar, programado con `BackgroundTasks` después de la respuesta y del commit; no altera el resultado HTTP.
- **Sin migraciones, seed ni disparadores**: los modelos quedan listos para la migración 001 y RN-15 de C-09.

## Capabilities

### New Capabilities

- `ordenes-de-trabajo`: ciclo de vida de la orden de trabajo (alta, listado, detalle, inicio, terminación, cancelación, ítems, historial de estados, consumo de stock y autorización por rol o por dueño del vehículo).

### Modified Capabilities

<!-- Ninguna: RN-16 ya está especificada en clientes-y-vehiculos y no cambia su comportamiento
     observable; estados-de-orden ya define el catálogo de sólo lectura. C-07 completa sus
     implementaciones sin modificar requisitos existentes. -->

## Impact

- **Código nuevo**: `app/modules/ordenes/{models,schemas,errors,repository,service,router,verificacion}.py`; `app/main.py` monta `/ordenes` y `/estados-orden` en `router_protegido`.
- **Código existente**: `app/modules/repuestos/motivos.py` (nuevo motivo); `app/modules/clientes/{router,verificacion}.py` (inyección del verificador real y retiro del stub); tests de clientes que dependían del stub.
- **Dependencias**: `BackgroundTasks` de FastAPI (sin dependencias nuevas); reutiliza `UnitOfWork`, `PaginaResponse`, `get_session`, `requiere_rol` y `CurrentUser`.
- **Base de datos**: sólo modelos; la migración 001, el seed del catálogo/órdenes y los disparadores de sólo agregado pertenecen a C-09.
- **Consumidores**: C-08 (`/mis-ordenes`) reutiliza modelos, repositorios y la autorización de dueño; C-09 genera la migración con estas tablas.
