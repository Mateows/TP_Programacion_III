# Spec Delta

## Purpose

Permitir que un cliente autenticado consulte en forma paginada el estado de las órdenes asociadas a sus propios vehículos, sin exponer órdenes pertenecientes a otros clientes.

## ADDED Requirements

### Requirement: Consulta paginada de mis órdenes

El sistema SHALL exponer `GET /mis-ordenes` para devolver una página de órdenes asociadas a los vehículos del cliente autenticado, con `items`, `total`, `page`, `size` y `pages`.

#### Scenario: Cliente consulta sus órdenes

- **WHEN** un cliente autenticado solicita `GET /mis-ordenes` sin parámetros
- **THEN** la respuesta es `200` con la primera página, tamaño por omisión 20 y sólo órdenes de sus vehículos

#### Scenario: Cliente consulta una página válida

- **WHEN** un cliente autenticado solicita una página entre 1 y la última disponible con un tamaño entre 1 y 100
- **THEN** la respuesta es `200` y contiene los metadatos de paginación coherentes con el resultado

#### Scenario: Cliente no tiene órdenes

- **WHEN** un cliente autenticado no tiene órdenes asociadas a sus vehículos
- **THEN** la respuesta es `200` con `items` vacío, `total` igual a 0 y una representación de paginación válida

#### Scenario: Página inexistente

- **WHEN** un cliente autenticado solicita una página posterior a la última disponible
- **THEN** la respuesta es `422` y no se devuelven órdenes

#### Scenario: Parámetros inválidos

- **WHEN** la solicitud usa una página menor que 1 o un tamaño menor que 1 o mayor que 100
- **THEN** la respuesta es `422`

### Requirement: Aislamiento de órdenes propias

El sistema SHALL determinar el alcance de la consulta exclusivamente a partir de la cuenta autenticada, su ficha de cliente y los vehículos relacionados, sin aceptar un identificador de cliente o usuario para seleccionar otro alcance.

#### Scenario: Cliente no ve órdenes ajenas

- **WHEN** existen órdenes de vehículos de dos clientes y cada cliente solicita `GET /mis-ordenes`
- **THEN** cada respuesta contiene únicamente las órdenes de los vehículos de la cuenta autenticada

#### Scenario: Cliente consulta un vehículo dado de baja

- **WHEN** una orden histórica pertenece a un vehículo que fue dado de baja y el vehículo está relacionado con la ficha del cliente
- **THEN** la orden continúa perteneciendo al resultado propio porque la baja del vehículo no rompe su relación histórica

#### Scenario: Cuenta sin ficha de cliente

- **WHEN** una cuenta autenticada sin ficha de cliente solicita `GET /mis-ordenes`
- **THEN** la respuesta es `403` y no se consultan ni exponen órdenes de otra ficha

### Requirement: Autenticación de la consulta propia

El sistema SHALL requerir una sesión autenticada para `GET /mis-ordenes` y SHALL evaluar la autorización con los roles vigentes de la cuenta según las reglas generales de acceso.

#### Scenario: Solicitud sin sesión

- **WHEN** un actor solicita `GET /mis-ordenes` sin cookie de sesión válida
- **THEN** la respuesta es `401`

#### Scenario: Cambio de contraseña pendiente

- **WHEN** una cuenta autenticada con cambio de contraseña pendiente solicita `GET /mis-ordenes`
- **THEN** la respuesta es `403` conforme a la restricción global de rutas protegidas
