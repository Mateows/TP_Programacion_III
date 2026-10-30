# Spec Delta

## Purpose

Define el ciclo de vida de la orden de trabajo del taller: alta con ítems de repuestos, listado y detalle, inicio por un mecánico, terminación con descuento atómico de stock, cancelación y consulta del catálogo de estados, con autorización por rol o por dueño del vehículo.

## ADDED Requirements

### Requirement: Orden de trabajo con ítems

El sistema SHALL persistir cada orden con vehículo, estado del catálogo, falla, mecánico asignado opcional, momento de creación y total no negativo; SHALL tener al menos un ítem, con cantidad y precio unitario positivos y un repuesto distinto por orden. El precio del ítem SHALL copiarse del repuesto y el total SHALL calcularlo el servidor.

#### Scenario: Orden recién creada

- **WHEN** se registra una orden con un vehículo vigente y al menos un ítem
- **THEN** queda almacenada con estado `PENDIENTE`, sin mecánico asignado, su falla, su momento de creación y el total calculado

#### Scenario: Ítems con precio copiado

- **WHEN** se registra una orden con dos repuestos de precios conocidos
- **THEN** cada ítem conserva el precio vigente del repuesto al momento del alta y el total es la suma de cantidad por precio unitario

#### Scenario: Repuesto repetido en la orden

- **WHEN** se intenta almacenar una orden con dos ítems del mismo repuesto
- **THEN** la operación se rechaza por violación de unicidad y no queda ninguna orden nueva

#### Scenario: Total no negativo

- **WHEN** se intenta almacenar una orden con total negativo
- **THEN** la operación se rechaza y la orden no queda almacenada

### Requirement: Historial de estados de la orden

El sistema SHALL dejar una línea de historial por cada transición de estado de una orden, con el estado de origen (nulo sólo en el alta), el estado de destino, la cuenta que la produjo y el momento. Una transición rechazada SHALL NOT dejar línea de historial.

#### Scenario: Alta deja la primera línea

- **WHEN** una orden se crea en estado `PENDIENTE`
- **THEN** queda una línea de historial con origen nulo y destino `PENDIENTE`

#### Scenario: Transición deja su línea

- **WHEN** una orden cambia de `PENDIENTE` a `EN_REPARACION`
- **THEN** queda una línea de historial con origen `PENDIENTE`, destino `EN_REPARACION` y la cuenta que la inició

#### Scenario: Transición rechazada no deja línea

- **WHEN** una transición se rechaza porque el estado no la permite
- **THEN** no queda ninguna línea de historial nueva

### Requirement: Alta de orden de trabajo

El sistema SHALL permitir a una cuenta con rol `ADMIN` o `RECEPCION` vigente crear una orden con vehículo, falla e ítems, respondiendo `201` con los precios copiados, el total y el historial. SHALL responder `409` si el vehículo o un repuesto no existe o está dado de baja, o si el catálogo de estados está vacío; `422` si el cuerpo no cumple el contrato; `403` sin rol habilitado y `401` sin sesión.

#### Scenario: Alta exitosa

- **WHEN** una cuenta con rol `ADMIN` o `RECEPCION` vigente crea una orden con un vehículo vigente y uno o más ítems válidos
- **THEN** la respuesta es `201`, la orden nace `PENDIENTE`, con el total calculado y la primera línea de historial

#### Scenario: Cuerpo inválido

- **WHEN** el alta envía una falla ausente, una lista de ítems vacía o una cantidad no positiva
- **THEN** la respuesta es `422` y no queda ninguna orden nueva

#### Scenario: Ítem repetido

- **WHEN** el alta envía dos ítems del mismo repuesto
- **THEN** la respuesta es `422` y no queda ninguna orden nueva

#### Scenario: Campo no declarado

- **WHEN** el alta envía un precio, un total, un estado, un mecánico o cualquier campo que el contrato no declara
- **THEN** la respuesta es `422` y no queda ninguna orden nueva

#### Scenario: Vehículo inexistente o dado de baja

- **WHEN** el alta referencia un vehículo que no existe o está dado de baja
- **THEN** la respuesta es `409` y no queda ninguna orden nueva

#### Scenario: Repuesto inexistente o dado de baja

- **WHEN** el alta referencia un repuesto que no existe o está dado de baja
- **THEN** la respuesta es `409` y no queda ninguna orden nueva

#### Scenario: Catálogo de estados vacío

- **WHEN** el alta se intenta con el catálogo de estados vacío
- **THEN** la respuesta es `409` y no queda ninguna orden nueva

#### Scenario: Sin rol habilitado

- **WHEN** una cuenta sin rol `ADMIN` ni `RECEPCION` vigente intenta crear una orden
- **THEN** la respuesta es `403` y no queda ninguna orden nueva

#### Scenario: Sin sesión

- **WHEN** se intenta crear una orden sin sesión
- **THEN** la respuesta es `401`

### Requirement: Listado de órdenes

El sistema SHALL devolver con `200` una página de órdenes, con filtro opcional por estado del catálogo, página desde 1 y tamaño entre 1 y 100 con valor por omisión 20. SHALL responder `422` si el estado no existe en el catálogo, si la página supera la última o si el tamaño está fuera de rango. La consulta SHALL requerir rol `ADMIN`, `RECEPCION` o `MECANICO` vigente.

#### Scenario: Página por omisión

- **WHEN** una cuenta con rol `ADMIN`, `RECEPCION` o `MECANICO` vigente consulta las órdenes sin parámetros
- **THEN** la respuesta es `200` con la primera página de hasta 20 órdenes e incluye `items`, `total`, `page`, `size` y `pages`

#### Scenario: Filtro por estado

- **WHEN** la consulta incluye un estado existente en el catálogo
- **THEN** la respuesta es `200` e incluye sólo las órdenes en ese estado

#### Scenario: Estado no declarado

- **WHEN** la consulta incluye un estado que no existe en el catálogo
- **THEN** la respuesta es `422`

#### Scenario: Página fuera del rango

- **WHEN** la consulta pide una página posterior a la última disponible
- **THEN** la respuesta es `422`

#### Scenario: Tamaño de página fuera del rango

- **WHEN** la consulta pide un tamaño menor que 1 o mayor que 100
- **THEN** la respuesta es `422`

#### Scenario: Sin rol habilitado

- **WHEN** una cuenta autenticada sin rol `ADMIN`, `RECEPCION` ni `MECANICO` vigente consulta las órdenes
- **THEN** la respuesta es `403`

#### Scenario: Sin sesión

- **WHEN** se consulta el listado sin sesión
- **THEN** la respuesta es `401`

### Requirement: Detalle de orden

El sistema SHALL devolver con `200` el detalle de una orden con su vehículo, su cliente, sus ítems con repuesto, su historial de estados y su mecánico asignado, a una cuenta de personal con rol `ADMIN`, `RECEPCION` o `MECANICO` vigente o al cliente dueño del vehículo. SHALL responder `403` si la cuenta está autenticada pero no es personal ni dueña, y `404` si la orden no existe.

#### Scenario: Personal consulta cualquier orden

- **WHEN** una cuenta con rol `ADMIN`, `RECEPCION` o `MECANICO` vigente consulta una orden existente
- **THEN** la respuesta es `200` e incluye vehículo, cliente, ítems, historial y mecánico asignado

#### Scenario: Dueño consulta su orden

- **WHEN** un cliente autenticado consulta una orden de un vehículo de su ficha
- **THEN** la respuesta es `200` con el detalle de la orden

#### Scenario: Cuenta sin permiso sobre la orden

- **WHEN** una cuenta autenticada que no es personal ni dueña del vehículo consulta la orden
- **THEN** la respuesta es `403`

#### Scenario: Orden inexistente

- **WHEN** se consulta un identificador que no corresponde a ninguna orden
- **THEN** la respuesta es `404`

#### Scenario: Sin sesión

- **WHEN** se consulta el detalle sin sesión
- **THEN** la respuesta es `401`

### Requirement: Inicio de orden

El sistema SHALL permitir a una cuenta con rol `MECANICO` vigente iniciar una orden en estado `PENDIENTE`, pasándola a `EN_REPARACION` y asignándole esa cuenta, y SHALL responder `200` con la orden actualizada. SHALL responder `403` sin rol `MECANICO`, `404` si la orden no existe y `409` si su estado no permite iniciarla.

#### Scenario: Inicio exitoso

- **WHEN** una cuenta con rol `MECANICO` vigente inicia una orden `PENDIENTE`
- **THEN** la respuesta es `200`, la orden pasa a `EN_REPARACION` y queda asignada a esa cuenta

#### Scenario: Orden en otro estado

- **WHEN** se intenta iniciar una orden que no está `PENDIENTE`
- **THEN** la respuesta es `409` y la orden conserva su estado y su asignación

#### Scenario: Sin rol de mecánico

- **WHEN** una cuenta autenticada sin rol `MECANICO` vigente intenta iniciar una orden
- **THEN** la respuesta es `403` y la orden no cambia

#### Scenario: Orden inexistente

- **WHEN** se intenta iniciar un identificador que no corresponde a ninguna orden
- **THEN** la respuesta es `404`

#### Scenario: Sin sesión

- **WHEN** se intenta iniciar una orden sin sesión
- **THEN** la respuesta es `401`

### Requirement: Terminación de orden

El sistema SHALL permitir terminar una orden en estado `EN_REPARACION` al mecánico asignado o a una cuenta con rol `ADMIN` vigente, pasándola a `TERMINADA` y respondiendo `200`. SHALL responder `403` si la cuenta no es el mecánico asignado ni `ADMIN`, `404` si la orden no existe y `409` si su estado no permite terminarla.

#### Scenario: Mecánico asignado termina

- **WHEN** el mecánico asignado termina una orden `EN_REPARACION`
- **THEN** la respuesta es `200` y la orden pasa a `TERMINADA`

#### Scenario: Administrador termina

- **WHEN** una cuenta con rol `ADMIN` vigente termina una orden `EN_REPARACION` asignada a otro mecánico
- **THEN** la respuesta es `200` y la orden pasa a `TERMINADA`

#### Scenario: Cuenta sin permiso sobre la orden

- **WHEN** una cuenta que no es el mecánico asignado ni `ADMIN` intenta terminar la orden
- **THEN** la respuesta es `403`, aunque el estado tampoco lo permita, y no se escribe nada

#### Scenario: Orden en otro estado

- **WHEN** una cuenta autorizada intenta terminar una orden que no está `EN_REPARACION`
- **THEN** la respuesta es `409` y la orden conserva su estado

#### Scenario: Orden inexistente

- **WHEN** se intenta terminar un identificador que no corresponde a ninguna orden
- **THEN** la respuesta es `404`

#### Scenario: Sin sesión

- **WHEN** se intenta terminar una orden sin sesión
- **THEN** la respuesta es `401`

### Requirement: Consumo de stock al terminar

Al terminar una orden, el sistema SHALL descontar del stock cada ítem, dejar un movimiento de stock por cada salida con la cantidad positiva, el motivo de consumo, la orden y la cuenta actuante, y dejar la línea de historial hacia `TERMINADA`, todo en una sola transacción. Si algún repuesto no alcanza, SHALL responder `409` sin ninguna escritura.

#### Scenario: Descuento y movimientos

- **WHEN** se termina una orden con dos ítems y stock suficiente en ambos repuestos
- **THEN** el stock de cada repuesto disminuye en la cantidad del ítem y queda un movimiento por cada salida, con la orden y la cuenta que terminó

#### Scenario: Historial de la terminación

- **WHEN** se termina una orden
- **THEN** queda una línea de historial con origen `EN_REPARACION`, destino `TERMINADA` y la cuenta que la terminó

#### Scenario: Stock insuficiente revierte todo

- **WHEN** se termina una orden y al menos un repuesto no tiene stock suficiente
- **THEN** la respuesta es `409`, ningún stock cambia, no queda ningún movimiento nuevo, no queda línea de historial nueva y la orden sigue `EN_REPARACION`

#### Scenario: Varios ítems, uno insuficiente

- **WHEN** una orden tiene un ítem con stock suficiente y otro sin stock suficiente
- **THEN** no se descuenta ninguno de los dos y no queda ningún movimiento nuevo

### Requirement: Cancelación de orden

El sistema SHALL permitir cancelar una orden en estado `PENDIENTE` a una cuenta con rol `ADMIN` o `RECEPCION` vigente o al cliente dueño del vehículo, pasándola a `CANCELADA` y respondiendo `200`. SHALL evaluar el permiso antes que el estado: `403` si la cuenta no es personal habilitado ni dueña, `409` si el estado no permite cancelar, `404` si la orden no existe.

#### Scenario: Personal cancela

- **WHEN** una cuenta con rol `ADMIN` o `RECEPCION` vigente cancela una orden `PENDIENTE`
- **THEN** la respuesta es `200`, la orden pasa a `CANCELADA` y queda la línea de historial con la cuenta

#### Scenario: Dueño cancela sin rol de personal

- **WHEN** un cliente autenticado dueño del vehículo cancela una orden `PENDIENTE` de ese vehículo
- **THEN** la respuesta es `200` y la orden pasa a `CANCELADA`

#### Scenario: Cuenta sin permiso sobre la orden

- **WHEN** una cuenta autenticada que no es personal habilitado ni dueña intenta cancelar la orden
- **THEN** la respuesta es `403` y la orden no cambia

#### Scenario: Permiso antes que estado

- **WHEN** una cuenta sin permiso intenta cancelar una orden que además no está `PENDIENTE`
- **THEN** la respuesta es `403` y no se revela ni se modifica el estado

#### Scenario: Orden en otro estado

- **WHEN** una cuenta autorizada intenta cancelar una orden que no está `PENDIENTE`
- **THEN** la respuesta es `409` y la orden conserva su estado

#### Scenario: Orden inexistente

- **WHEN** se intenta cancelar un identificador que no corresponde a ninguna orden
- **THEN** la respuesta es `404`

#### Scenario: Sin sesión

- **WHEN** se intenta cancelar una orden sin sesión
- **THEN** la respuesta es `401`

### Requirement: Consulta del catálogo de estados de orden

El sistema SHALL devolver con `200` el catálogo de estados ordenado por posición, con código, descripción, posición e indicador de estado final, a cualquier cuenta autenticada, y SHALL responder `401` sin sesión. La API SHALL NOT permitir crear, modificar ni eliminar estados.

#### Scenario: Catálogo ordenado

- **WHEN** una cuenta autenticada consulta los estados
- **THEN** la respuesta es `200` con los estados ordenados por posición y con `TERMINADA` y `CANCELADA` marcadas como finales

#### Scenario: Sin sesión

- **WHEN** se consulta el catálogo sin sesión
- **THEN** la respuesta es `401`
