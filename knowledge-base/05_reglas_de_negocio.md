# Reglas de Negocio

Cada regla tiene un código único `RN-{NN}` para trazabilidad. Total: 20 reglas (RN-01 a RN-20).

## Dominio: Unicidad e integridad

- **RN-01**: El correo de un usuario y el documento de un cliente son únicos. La patente de un vehículo y el código de un repuesto son únicos entre los que no están dados de baja. Garantizado por UNIQUE e índices únicos parciales en la base; respuesta 409 con mensaje propio.
- **RN-02**: El auto-registro crea el usuario, su rol CLIENTE y su ficha de cliente: o quedan las tres filas, o ninguna. Si el documento ya es de un cliente del taller, el registro da 409 y no se apropia de esa ficha. Un solo Unit of Work.

## Dominio: Roles y autorización

- **RN-03**: Un usuario tiene a lo sumo una asignación abierta por rol. Índice único parcial; respuesta 409.
- **RN-04**: Los permisos se deciden con los roles vigentes en la base, en cada petición. Los roles que trae el token son informativos. Dependencia que consulta `asignacion_rol`.
- **RN-05**: Un administrador no puede revocarse su propio rol ADMIN, y el sistema nunca queda sin administradores vigentes. Comprobación en el servicio; respuesta 409.
- **RN-06**: Mientras un usuario tenga el cambio de contraseña pendiente, sólo puede usar las rutas de salud y `/auth`. Dos grupos de rutas; respuesta 403.
- **RN-07**: Al cambiar la contraseña, las sesiones emitidas antes dejan de valer, aunque sean del mismo segundo que el cambio; la que devuelve el propio cambio, no. Comparación de `iat` con `password_cambiada_en`, sin truncar; respuesta 401.

## Dominio: Seguridad de acceso

- **RN-08**: Después de 5 intentos fallidos con el mismo correo desde la misma dirección en 60 segundos, el login responde 429 sin verificar la contraseña. Un login correcto reinicia la cuenta: los fallos anteriores siguen en la tabla, pero dejan de contar. Conteo sobre `intento_acceso`; After Retry.
- **RN-09**: El login responde lo mismo, y tarda lo mismo, exista o no el correo. Mismo mensaje; verificación contra un hash ficticio.

## Dominio: Órdenes de trabajo

- **RN-10**: Una orden nace PENDIENTE con al menos un ítem y sin repuestos repetidos. El precio de cada ítem se copia del repuesto, y el total lo calcula el servidor. DTO; el precio y el total nunca viajan en el cuerpo.
- **RN-11**: Las transiciones de una orden son PENDIENTE → EN_REPARACION (la inicia un mecánico, que queda asignado), EN_REPARACION → TERMINADA (la termina el mecánico asignado o un administrador) y PENDIENTE → CANCELADA. Servicio; 409 si el estado no lo permite.
- **RN-12**: Cancelan una orden la recepción, el administrador o el dueño del vehículo. El permiso se evalúa antes que el estado. Servicio; 403 antes que 409.
- **RN-13**: Terminar una orden descuenta el stock de cada ítem, deja un movimiento por cada salida y una línea de historial. Si un repuesto no alcanza, no queda ninguna de esas escrituras. Un solo Unit of Work; respuesta 409.
- **RN-14**: El stock de un repuesto sólo cambia a través de movimientos: el alta con stock inicial, la reposición y la terminación de órdenes. No se edita por PATCH. Punto único de escritura de stock.
- **RN-15**: `historial_estado_orden`, `movimiento_stock` y `historial_precio_repuesto` son de sólo agregado: nadie puede modificar ni borrar sus filas. Disparador en la base, instalado por migración.
- **RN-16**: Un vehículo o un repuesto dado de baja deja de aparecer y no se puede usar en órdenes nuevas, pero sus datos se conservan. Un vehículo con órdenes abiertas (en un estado que el catálogo no marca como final) no se da de baja. Borrado lógico; `es_final`; respuesta 409.
- **RN-17**: Lo propio sólo pide estar autenticado: un cliente ve sus vehículos y las órdenes de sus vehículos, y ninguna otra. `/mis-*` y comprobación de dueño; respuesta 403.
- **RN-18**: Ningún error devuelve al cliente texto interno de la base, que le entregaría el mapa del esquema. Ninguna entrada inválida termina en un 500. Traducción del `IntegrityError`; validación en el contrato.
- **RN-19**: Los estados posibles de una orden son las filas del catálogo `estado_orden`. El catálogo se consulta desde la API y no se edita desde ella. Si está vacío, crear una orden responde 409 con un mensaje propio. Clave foránea; repositorio de sólo lectura.
- **RN-20**: Cada cambio del precio de un repuesto deja una línea en `historial_precio_repuesto`, en la misma transacción que el cambio. Un PATCH que no cambia el precio no deja línea. Un solo Unit of Work; `CHECK precio_nuevo > precio_anterior`.

## Dominio: Excepciones globales

- Toda ruta del grupo protegido responde además 401 sin sesión y 403 con el cambio de contraseña pendiente.
- El login sigue este orden: primero el límite de intentos (RN-08), que cuesta una consulta y, si se superó, responde 429 con `Retry-After` sin calcular ningún hash; después la verificación, contra el hash del usuario o contra un hash ficticio si el correo no existe (RN-09).
- La ruta de cancelar no lleva `requiere_rol` (el dueño de un vehículo puede cancelar su orden y no tiene un rol de personal). La decisión la toma el servicio: primero quién es y qué relación tiene con la orden (403), y recién después si el estado permite cancelarla (409).
