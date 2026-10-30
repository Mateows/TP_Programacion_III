# Proposal: c-06-repuestos-stock

## Why

El taller necesita un catálogo de repuestos con existencias confiables antes de poder armar órdenes de trabajo: C-07 depende de que cada repuesto tenga precio y stock, y de que toda variación de stock quede registrada como movimiento. Hoy `app/modules/repuestos/` sólo tiene un `__init__.py` vacío, no existe ningún modelo de dinero en el proyecto y el catálogo no se puede consultar ni administrar.

## What Changes

- Nuevo módulo `app/modules/repuestos/` con las tres entidades del dominio de inventario: `repuesto`, `movimiento_stock` e `historial_precio_repuesto`.
- `GET /repuestos` — listado paginado con búsqueda por descripción; ADMIN, RECEPCION y MECANICO.
- `POST /repuestos` — alta con código único entre vigentes, precio mayor que cero y stock inicial; ADMIN. El stock inicial se registra como movimiento (RN-14).
- `PATCH /repuestos/{id}` — edición parcial (`exclude_unset`) de descripción y precio; el cambio de precio deja una línea en el historial en la misma transacción (RN-20). El stock no se edita por PATCH (RN-14).
- `POST /repuestos/{id}/reponer` — reposición de stock como movimiento; ADMIN.
- `GET /repuestos/{id}/movimientos` y `GET /repuestos/{id}/precios` — ADMIN.
- `DELETE /repuestos/{id}` — borrado lógico, `204` sin cuerpo; el repuesto deja de aparecer y de poder usarse en órdenes nuevas, pero conserva sus datos (RN-16).
- Restricciones en la base: índice único parcial de `codigo` entre vigentes, `CHECK precio > 0`, `CHECK stock >= 0`, `CHECK cantidad > 0`, `CHECK precio_nuevo > 0` y `CHECK precio_nuevo > precio_anterior`.
- **BREAKING**: ninguno. No se modifica ningún contrato existente. `PaginaResponse` y `PaginaFueraDeRango` se mueven de `app/modules/usuarios/` a `app/core/paginacion.py` conservando su nombre y comportamiento, para que los módulos nuevos no dependan de `usuarios`.

## Capabilities

### New Capabilities

- `repuestos-y-stock`: catálogo de repuestos con precio y existencias, alta, edición con historial de precios, reposición y movimientos de stock de sólo agregado, baja lógica, y consulta paginada con búsqueda.

### Modified Capabilities

Ninguna. Las reglas transversales de persistencia (`acceso-a-datos`) y de autorización por roles vigentes (`gestion-de-usuarios`) ya cubren lo que C-06 necesita y no cambian sus requisitos.

## Impact

- **Código nuevo**: `app/modules/repuestos/{models,repository,schemas,errors,service,router,motivos}.py`; montaje de `/repuestos` en `router_protegido` (`app/main.py`).
- **Código existente tocado**: `app/core/paginacion.py` (alojará `PaginaResponse` y `PaginaFueraDeRango`), `app/modules/usuarios/schemas.py` y `app/modules/usuarios/errors.py` (re-exportan desde `core`, sin cambiar su API pública), `app/main.py`.
- **Dependencias**: sin dependencias nuevas. Primer uso de `NUMERIC`/`Decimal` en el proyecto.
- **Base de datos**: tres tablas nuevas; la migración y el seed son responsabilidad de **C-09** (no se generan acá).
- **Fuera de alcance**: `GET /repuestos/{id}` (detalle), consumo de repuestos al terminar órdenes (C-07), migraciones, seed y disparadores de sólo agregado (C-09).
