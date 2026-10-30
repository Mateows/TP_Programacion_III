# Proposal

## Why

El taller no puede registrar a quién atiende ni qué vehículo ingresa: hoy existen cuentas de usuario y roles, pero ninguna ficha de cliente ni de vehículo. Sin ese vínculo no hay forma de asociar una orden de trabajo a un vehículo (C-07), ni de que un cliente autenticado consulte lo suyo (RN-17). C-03 dejó explícitamente diferida a este change la creación de la ficha de cliente en el auto-registro (RN-02), porque el modelo no existía todavía.

## What Changes

- Se incorporan los modelos de tabla `cliente` y `vehiculo`, con las restricciones de la KB: `cliente.usuario_id` nulo y único (uno a uno opcional con `usuario`), `cliente.documento` único, `vehiculo.patente` única sólo entre los vigentes (índice único parcial `WHERE borrado_en IS NULL`), `CHECK anio BETWEEN 1950 AND 2100`, y un índice explícito por cada clave foránea.
- Se agrega el alta de cliente por personal (`POST /clientes`, roles `RECEPCION` y `ADMIN`) con documento único y respuesta `201`/`409`/`422`.
- Se agrega la consulta de un cliente con sus vehículos vigentes (`GET /clientes/{id}`, `200`/`404`).
- Se agrega el alta de vehículo para un cliente existente (`POST /clientes/{id}/vehiculos`, `201`/`404`/`409`/`422`).
- Se agrega la baja lógica de vehículo (`DELETE /vehiculos/{id}`, `204`/`404`/`409`) que se rechaza cuando el vehículo tiene órdenes abiertas (RN-16).
- Se agrega la consulta de los vehículos propios (`GET /mis-vehiculos`, autenticado sin rol específico, `200`) que nunca devuelve vehículos ajenos (RN-17).
- **BREAKING**: `POST /auth/registro` pasa a exigir `documento` y a aceptar `telefono`, y crea la ficha de cliente junto con la cuenta y el rol `CLIENTE` en la misma unidad de trabajo (RN-02). Un registro cuyo documento ya pertenece a un cliente del taller responde `409` y no se apropia de esa ficha.
- La verificación de "órdenes abiertas" se resuelve con un verificador inyectable sin implementación real en este change: la tabla `orden_trabajo` pertenece a C-07, que sustituirá el verificador por la consulta efectiva sin cambiar el contrato observable de la baja.

## Capabilities

### New Capabilities

- `clientes-y-vehiculos`: fichas de cliente del taller, vehículos asociados con patente vigente única, altas y consultas por personal, baja lógica condicionada por órdenes abiertas y consulta de lo propio por parte del cliente autenticado.

### Modified Capabilities

- `autenticacion`: el requirement de registro de cuenta de cliente cambia — el alta pasa a incluir documento y teléfono y a crear la ficha de cliente en la misma transacción, con `409` cuando el documento ya está registrado.

## Impact

- **Código nuevo**: `app/modules/clientes/` completo en seis capas (models, schemas, errors, repository, service, router), hoy sólo un `__init__.py`.
- **Código modificado**: `app/modules/auth/schemas.py` (`RegistroRequest`), `app/modules/auth/service.py` (`registrar_cuenta`), `app/modules/auth/router.py` (traducción del conflicto de documento), `app/main.py` (montaje de `/clientes`, `/vehiculos` y `/mis-vehiculos` en el grupo protegido).
- **Reutiliza**: `BaseRepository` y `SoftDeleteRepository` (`app/core/repository.py`), `UnitOfWork`, `requiere_rol`/`CurrentUser` (`app/core/dependencies.py`), `traducir_integridad`.
- **Datos**: dos tablas nuevas. La migración no se genera acá: C-09 unifica todas las migraciones.
- **Pruebas**: unidades de servicio y de contrato HTTP para las rutas nuevas, más la actualización de los tests de `POST /auth/registro` por el campo obligatorio nuevo.
- **Dependencias**: C-03 (autenticación y roles vigentes). C-05 queda como proveedor de `vehiculo` para C-07 y para C-08.
- **Fuera de alcance**: edición o baja de clientes (la KB no define `borrado_en` para `cliente` ni endpoints de modificación), paginación o búsqueda de clientes, alta de vehículo sin cliente existente, y la consulta de órdenes propias (C-08).
