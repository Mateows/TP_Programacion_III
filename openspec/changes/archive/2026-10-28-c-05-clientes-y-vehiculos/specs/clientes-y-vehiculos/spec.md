# Spec Delta

## Purpose

Define las fichas de los clientes del taller y los vehículos que se les asocian: altas y consultas por parte del personal, patente única entre vigentes, baja lógica condicionada por órdenes abiertas y consulta de lo propio por el cliente autenticado.

## ADDED Requirements

### Requirement: Ficha de cliente del taller

El sistema SHALL persistir cada cliente del taller con identificador propio, nombre, documento único y teléfono opcional, y SHALL vincularlo opcionalmente con una cuenta de usuario mediante una referencia única. Ninguna cuenta SHALL tener más de una ficha de cliente y ninguna ficha SHALL apuntar a más de una cuenta.

#### Scenario: Cliente sin cuenta asociada

- **WHEN** se registra un cliente que no corresponde a ninguna cuenta de usuario
- **THEN** la ficha queda almacenada con su referencia de cuenta vacía

#### Scenario: Cliente asociado a una cuenta

- **WHEN** se registra un cliente vinculado a una cuenta de usuario que no tiene otra ficha
- **THEN** la ficha queda almacenada con la referencia a esa cuenta

#### Scenario: Documento repetido

- **WHEN** se intenta registrar un cliente con un documento que ya pertenece a otro cliente
- **THEN** la operación se rechaza por violación de unicidad y no queda ninguna ficha nueva

#### Scenario: Documentos distintos

- **WHEN** se registran dos clientes con documentos diferentes
- **THEN** ambas fichas quedan almacenadas

### Requirement: Alta de cliente por personal

El sistema SHALL permitir a una cuenta con rol `RECEPCION` o `ADMIN` vigente dar de alta un cliente con nombre, documento y teléfono opcional, respondiendo `201`. SHALL responder `409` si el documento ya pertenece a otro cliente y `422` si el cuerpo no cumple el contrato.

#### Scenario: Alta exitosa

- **WHEN** una cuenta con rol `RECEPCION` o `ADMIN` vigente da de alta un cliente con un documento no registrado
- **THEN** la respuesta es `201` y la ficha queda almacenada

#### Scenario: Documento ya registrado

- **WHEN** el alta usa un documento que ya pertenece a otro cliente
- **THEN** la respuesta es `409` y no queda ninguna ficha nueva

#### Scenario: Cuerpo inválido

- **WHEN** el alta omite el nombre o el documento, o envía un campo no declarado
- **THEN** la respuesta es `422` y no queda ninguna ficha nueva

#### Scenario: Sin rol de personal

- **WHEN** una cuenta sin rol `RECEPCION` ni `ADMIN` vigente solicita el alta de un cliente
- **THEN** la respuesta es `403` y no queda ninguna ficha nueva

### Requirement: Consulta de cliente con sus vehículos

El sistema SHALL devolver con `200` la ficha de un cliente existente junto con sus vehículos vigentes, y SHALL responder `404` si el cliente no existe. La consulta SHALL requerir rol `RECEPCION` o `ADMIN` vigente.

#### Scenario: Cliente con vehículos

- **WHEN** una cuenta con rol `RECEPCION` o `ADMIN` vigente consulta un cliente que tiene vehículos vigentes
- **THEN** la respuesta es `200` e incluye la ficha y esos vehículos

#### Scenario: Cliente sin vehículos

- **WHEN** se consulta un cliente que no tiene vehículos vigentes
- **THEN** la respuesta es `200` con la ficha y una lista de vehículos vacía

#### Scenario: Vehículos dados de baja excluidos

- **WHEN** el cliente consultado tiene vehículos dados de baja
- **THEN** la respuesta no los incluye

#### Scenario: Cliente inexistente

- **WHEN** se consulta un identificador de cliente que no existe
- **THEN** la respuesta es `404`

#### Scenario: Sin rol de personal

- **WHEN** una cuenta sin rol `RECEPCION` ni `ADMIN` vigente consulta un cliente
- **THEN** la respuesta es `403`

### Requirement: Vehículo asociado a un cliente

El sistema SHALL persistir cada vehículo con identificador propio, referencia obligatoria a un cliente, patente, marca, modelo, año y una marca de baja opcional; la baja SHALL ser lógica y SHALL conservar la fila y sus datos.

#### Scenario: Vehículo recién registrado

- **WHEN** se registra un vehículo para un cliente existente
- **THEN** queda almacenado con su patente, marca, modelo, año y sin marca de baja

#### Scenario: Baja conserva los datos

- **WHEN** un vehículo se da de baja
- **THEN** la fila permanece almacenada con sus datos y con su marca de baja

### Requirement: Alta de vehículo para un cliente

El sistema SHALL registrar un vehículo para un cliente existente, respondiendo `201`, y SHALL responder `404` si el cliente no existe y `422` si falta la patente, la marca o el modelo. La operación SHALL requerir rol `RECEPCION` o `ADMIN` vigente.

#### Scenario: Alta exitosa

- **WHEN** una cuenta con rol `RECEPCION` o `ADMIN` vigente registra un vehículo para un cliente existente
- **THEN** la respuesta es `201` y el vehículo queda asociado a ese cliente

#### Scenario: Cliente inexistente

- **WHEN** se registra un vehículo para un identificador de cliente que no existe
- **THEN** la respuesta es `404` y no queda ningún vehículo

#### Scenario: Datos incompletos

- **WHEN** el alta omite la patente, la marca o el modelo, o envía un campo no declarado
- **THEN** la respuesta es `422` y no queda ningún vehículo

#### Scenario: Sin rol de personal

- **WHEN** una cuenta sin rol `RECEPCION` ni `ADMIN` vigente registra un vehículo
- **THEN** la respuesta es `403` y no queda ningún vehículo

### Requirement: Patente vigente única

El sistema SHALL garantizar que no existan dos vehículos vigentes con la misma patente, comparándola sin distinguir mayúsculas ni espacios circundantes, y SHALL responder `409` cuando la patente ya pertenece a un vehículo vigente. Un vehículo dado de baja SHALL liberar su patente.

#### Scenario: Patente ya vigente

- **WHEN** se registra un vehículo con una patente que ya pertenece a un vehículo vigente
- **THEN** la respuesta es `409` y no queda ningún vehículo nuevo

#### Scenario: Patente con distinta capitalización

- **WHEN** se registra un vehículo con una patente que difiere de una vigente sólo en mayúsculas o en espacios circundantes
- **THEN** la patente se considera repetida y la respuesta es `409`

#### Scenario: Patente liberada por una baja

- **WHEN** se registra un vehículo con la patente de un vehículo dado de baja
- **THEN** la respuesta es `201` y ambos vehículos quedan almacenados

### Requirement: Año del vehículo en rango

El sistema SHALL aceptar únicamente años de fabricación entre 1950 y 2100 inclusive, y SHALL rechazar con `422` cualquier valor fuera de ese rango.

#### Scenario: Año en los límites

- **WHEN** se registra un vehículo con año 1950 o con año 2100
- **THEN** la respuesta es `201`

#### Scenario: Año fuera de rango

- **WHEN** se registra un vehículo con un año anterior a 1950 o posterior a 2100
- **THEN** la respuesta es `422` y no queda ningún vehículo

### Requirement: Baja lógica de vehículo

El sistema SHALL dar de baja un vehículo vigente escribiendo su marca de baja, respondiendo `204` y conservando la fila, y SHALL responder `404` si el vehículo no existe o ya está dado de baja. La operación SHALL requerir rol `RECEPCION` o `ADMIN` vigente.

#### Scenario: Baja exitosa

- **WHEN** una cuenta con rol `RECEPCION` o `ADMIN` vigente da de baja un vehículo vigente sin órdenes abiertas
- **THEN** la respuesta es `204` y el vehículo deja de aparecer en las consultas
- **AND** la fila permanece almacenada

#### Scenario: Vehículo inexistente

- **WHEN** se da de baja un identificador de vehículo que no existe
- **THEN** la respuesta es `404`

#### Scenario: Baja repetida

- **WHEN** se da de baja un vehículo que ya estaba dado de baja
- **THEN** la respuesta es `404` y su marca de baja original se conserva

#### Scenario: Sin rol de personal

- **WHEN** una cuenta sin rol `RECEPCION` ni `ADMIN` vigente da de baja un vehículo
- **THEN** la respuesta es `403` y el vehículo permanece vigente

### Requirement: Baja rechazada con órdenes abiertas

El sistema SHALL rechazar con `409` la baja de un vehículo que tenga al menos una orden de trabajo en un estado que el catálogo no marca como final, y el vehículo SHALL permanecer vigente.

#### Scenario: Vehículo con una orden abierta

- **WHEN** se da de baja un vehículo que tiene una orden en un estado no final
- **THEN** la respuesta es `409` y el vehículo permanece vigente

#### Scenario: Órdenes sólo en estados finales

- **WHEN** se da de baja un vehículo cuyas órdenes están todas en estados finales
- **THEN** la respuesta es `204` y la baja se registra

#### Scenario: Cualquier estado no final bloquea la baja

- **WHEN** el vehículo tiene una orden en cualquiera de los estados no finales del catálogo
- **THEN** la baja se rechaza con `409`

### Requirement: Vehículos propios del cliente autenticado

El sistema SHALL devolver con `200` únicamente los vehículos vigentes vinculados a la ficha del cliente autenticado, y SHALL NOT devolver vehículos de otras fichas. SHALL responder `401` sin sesión y `403` si la cuenta autenticada no tiene ficha de cliente.

#### Scenario: Cliente con vehículos propios

- **WHEN** una cuenta con ficha de cliente consulta sus vehículos
- **THEN** la respuesta es `200` e incluye sólo los vehículos vigentes de su propia ficha

#### Scenario: No expone vehículos ajenos

- **WHEN** existen vehículos de otras fichas de cliente
- **THEN** la respuesta no los incluye

#### Scenario: Cliente sin vehículos

- **WHEN** la ficha del cliente autenticado no tiene vehículos vigentes
- **THEN** la respuesta es `200` con una lista vacía

#### Scenario: Cuenta sin ficha de cliente

- **WHEN** una cuenta autenticada sin ficha de cliente consulta sus vehículos
- **THEN** la respuesta es `403`

#### Scenario: Sin sesión

- **WHEN** se consulta la ruta de vehículos propios sin sesión
- **THEN** la respuesta es `401`
