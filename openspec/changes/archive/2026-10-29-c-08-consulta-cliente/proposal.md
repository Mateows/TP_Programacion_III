# Proposal

## Why

Los clientes autenticados necesitan consultar el estado de sus reparaciones sin acceder a información de otros clientes. C-07 permite consultar el detalle individual de una orden, pero todavía falta una vista paginada que reúna únicamente las órdenes asociadas a los vehículos del cliente.

## What Changes

- Agregar `GET /mis-ordenes` para clientes autenticados.
- Devolver una respuesta paginada con las órdenes asociadas a los vehículos de la ficha del cliente autenticado.
- Aplicar autorización de "lo propio" usando la relación entre usuario, cliente y vehículo; nunca aceptar un `cliente_id` o `usuario_id` enviado por el solicitante para ampliar el alcance.
- Reutilizar la representación del detalle de orden definida por C-07 cuando corresponda, sin reimplementar `GET /ordenes/{id}` ni `GET /estados-orden`.
- Responder `401` sin sesión, `403` cuando la cuenta autenticada no tiene una ficha de cliente utilizable para la consulta y `422` ante parámetros de paginación inválidos o fuera de rango.

## Capabilities

### New Capabilities

- `consulta-cliente`: Consulta paginada y restringida de las órdenes propias del cliente autenticado.

### Modified Capabilities

No existing capability requirements are changed. The new route is a separate customer-facing capability and does not alter the contracts already defined for `ordenes-de-trabajo`.

## Impact

- Afecta el módulo de órdenes y sus capas de router, schemas, service, repository y tests.
- Requiere una consulta eficiente que relacione la sesión autenticada con su ficha de cliente, sus vehículos y sus órdenes.
- No requiere nuevas dependencias externas ni cambios de base de datos.
- Debe conservar la carga anticipada y evitar N+1, mantener la paginación existente y respetar los roles vigentes consultados desde la base.
