# Spec Delta

## Purpose

Define el catálogo de repuestos del taller y su inventario: altas, edición con historial de precios, búsqueda paginada, reposición y movimientos de stock de sólo agregado, y baja lógica, con el precio y las existencias siempre consistentes.

## ADDED Requirements

### Requirement: Repuesto del catálogo

El sistema SHALL persistir cada repuesto con identificador propio, código único entre los vigentes, descripción, precio mayor que cero con dos decimales, stock no negativo y una marca de baja opcional. Un repuesto dado de baja SHALL conservar la fila y sus datos.

#### Scenario: Repuesto recién registrado

- **WHEN** se registra un repuesto con un código no usado por otro repuesto vigente
- **THEN** queda almacenado con su código, descripción, precio y stock, y sin marca de baja

#### Scenario: Código repetido entre vigentes

- **WHEN** se intenta registrar un repuesto con el código de otro repuesto vigente
- **THEN** la operación se rechaza por violación de unicidad y no queda ningún repuesto nuevo

#### Scenario: Código liberado por una baja

- **WHEN** se registra un repuesto con el código de un repuesto dado de baja
- **THEN** el alta se acepta y ambos repuestos quedan almacenados

#### Scenario: Baja conserva los datos

- **WHEN** un repuesto se da de baja
- **THEN** la fila permanece almacenada con su código, descripción, precio y stock, y con su marca de baja

### Requirement: Listado de repuestos con búsqueda

El sistema SHALL devolver con `200` una página de repuestos vigentes, con búsqueda opcional por descripción sin distinguir mayúsculas, página desde 1, tamaño entre 1 y 100 con valor por omisión 20, y SHALL responder `422` si la página pedida supera la última. La consulta SHALL requerir rol `ADMIN`, `RECEPCION` o `MECANICO` vigente.

#### Scenario: Página por omisión

- **WHEN** una cuenta con rol `ADMIN`, `RECEPCION` o `MECANICO` vigente consulta el catálogo sin parámetros
- **THEN** la respuesta es `200` con la primera página de hasta 20 repuestos vigentes e incluye `items`, `total`, `page`, `size` y `pages`

#### Scenario: Búsqueda parcial por descripción

- **WHEN** la consulta incluye un texto que forma parte de la descripción de algunos repuestos, en cualquier combinación de mayúsculas y minúsculas
- **THEN** la respuesta es `200` e incluye sólo los repuestos vigentes cuya descripción contiene ese texto

#### Scenario: Búsqueda sin resultados

- **WHEN** la consulta incluye un texto que no forma parte de ninguna descripción
- **THEN** la respuesta es `200` con una lista vacía y `total` igual a cero

#### Scenario: Página fuera del rango

- **WHEN** la consulta pide una página posterior a la última disponible
- **THEN** la respuesta es `422`

#### Scenario: Tamaño de página fuera del rango

- **WHEN** la consulta pide un tamaño menor que 1 o mayor que 100
- **THEN** la respuesta es `422`

#### Scenario: Repuestos dados de baja excluidos

- **WHEN** el catálogo contiene repuestos dados de baja
- **THEN** el listado no los incluye y `total` no los cuenta

#### Scenario: Sin rol habilitado

- **WHEN** una cuenta autenticada sin rol `ADMIN`, `RECEPCION` ni `MECANICO` vigente consulta el catálogo
- **THEN** la respuesta es `403`

### Requirement: Alta de repuesto con stock inicial

El sistema SHALL permitir a una cuenta con rol `ADMIN` vigente dar de alta un repuesto con código, descripción, precio y stock inicial, respondiendo `201`. SHALL responder `409` si el código ya pertenece a un repuesto vigente y `422` si el cuerpo no cumple el contrato.

#### Scenario: Alta con stock inicial positivo

- **WHEN** una cuenta con rol `ADMIN` vigente da de alta un repuesto con stock inicial mayor que cero
- **THEN** la respuesta es `201`, el repuesto queda almacenado y se registra un movimiento de stock con el stock inicial y la cuenta que lo dio de alta

#### Scenario: Alta con stock inicial cero

- **WHEN** una cuenta con rol `ADMIN` vigente da de alta un repuesto con stock inicial cero
- **THEN** la respuesta es `201`, el repuesto queda almacenado con stock cero y no se registra ningún movimiento de stock

#### Scenario: Código ya registrado

- **WHEN** el alta usa el código de un repuesto vigente
- **THEN** la respuesta es `409` y no queda ningún repuesto nuevo

#### Scenario: Precio no positivo

- **WHEN** el alta envía un precio menor o igual que cero
- **THEN** la respuesta es `422` y no queda ningún repuesto nuevo

#### Scenario: Stock negativo

- **WHEN** el alta envía un stock inicial negativo
- **THEN** la respuesta es `422` y no queda ningún repuesto nuevo

#### Scenario: Precio con más de dos decimales

- **WHEN** el alta envía un precio con más de dos decimales
- **THEN** la respuesta es `422` y no queda ningún repuesto nuevo

#### Scenario: Campo no declarado

- **WHEN** el alta envía un campo que el contrato no declara
- **THEN** la respuesta es `422` y no queda ningún repuesto nuevo

#### Scenario: Sin rol de administración

- **WHEN** una cuenta sin rol `ADMIN` vigente intenta dar de alta un repuesto
- **THEN** la respuesta es `403` y no queda ningún repuesto nuevo

### Requirement: Edición parcial de repuesto

El sistema SHALL actualizar únicamente los campos enviados en un `PATCH` sobre un repuesto vigente, admitiendo descripción y precio, y respondiendo `200` con el repuesto actualizado. SHALL responder `404` si el repuesto no existe o está dado de baja, `422` si el cuerpo no cumple el contrato y `403` si la cuenta no tiene rol `ADMIN` vigente.

#### Scenario: Sólo cambia la descripción

- **WHEN** una cuenta con rol `ADMIN` vigente envía únicamente una descripción nueva
- **THEN** la respuesta es `200` y el repuesto conserva su precio y su stock

#### Scenario: Campos omitidos no cambian

- **WHEN** el `PATCH` omite la descripción o el precio
- **THEN** los campos omitidos conservan su valor anterior

#### Scenario: Intento de editar el stock

- **WHEN** el `PATCH` envía un stock
- **THEN** la respuesta es `422` y el stock no cambia

#### Scenario: Repuesto inexistente o dado de baja

- **WHEN** se edita un identificador que no corresponde a un repuesto vigente
- **THEN** la respuesta es `404` y no se modifica ninguna fila

#### Scenario: Sin rol de administración

- **WHEN** una cuenta sin rol `ADMIN` vigente intenta editar un repuesto
- **THEN** la respuesta es `403` y el repuesto no cambia

### Requirement: Historial de precios en el cambio

El sistema SHALL registrar una línea de historial de precios por cada cambio efectivo del precio de un repuesto, con el precio anterior, el precio nuevo, la cuenta que lo cambió y el momento, en la misma transacción que la actualización. Un `PATCH` que no cambia el precio SHALL NOT dejar línea de historial.

#### Scenario: Cambio de precio deja historial

- **WHEN** un `PATCH` cambia el precio por uno mayor que el vigente
- **THEN** la respuesta es `200` y queda una línea de historial con el precio anterior, el precio nuevo y la cuenta que lo cambió

#### Scenario: Precio igual no deja historial

- **WHEN** un `PATCH` envía el mismo precio que el repuesto ya tiene
- **THEN** la respuesta es `200`, el precio no cambia y no queda ninguna línea de historial nueva

#### Scenario: Fallo del historial revierte el precio

- **WHEN** el registro del historial de precios no se puede completar
- **THEN** el precio del repuesto conserva su valor anterior y no queda ninguna línea nueva

### Requirement: El precio del repuesto sólo aumenta

El sistema SHALL rechazar con `409` cualquier cambio de precio que no sea mayor que el precio vigente, conservando el precio anterior y sin dejar línea de historial.

#### Scenario: Precio menor al vigente

- **WHEN** un `PATCH` envía un precio menor que el vigente
- **THEN** la respuesta es `409`, el precio no cambia y no queda ninguna línea de historial nueva

#### Scenario: Mensaje sin detalle interno

- **WHEN** se rechaza un precio menor al vigente
- **THEN** el mensaje de la respuesta no nombra tablas, columnas ni restricciones

### Requirement: Reposición de stock

El sistema SHALL sumar la cantidad repuesta al stock de un repuesto vigente y registrar un movimiento de stock por esa cantidad, respondiendo `200`, y SHALL responder `404` si el repuesto no existe o está dado de baja y `422` si la cantidad no es mayor que cero. La operación SHALL requerir rol `ADMIN` vigente.

#### Scenario: Reposición exitosa

- **WHEN** una cuenta con rol `ADMIN` vigente repone una cantidad mayor que cero en un repuesto vigente
- **THEN** la respuesta es `200`, el stock aumenta en esa cantidad y queda un movimiento de stock por la misma cantidad y la misma cuenta

#### Scenario: Cantidad no positiva

- **WHEN** se repone una cantidad menor o igual que cero
- **THEN** la respuesta es `422` y el stock no cambia

#### Scenario: Repuesto inexistente o dado de baja

- **WHEN** se repone un identificador que no corresponde a un repuesto vigente
- **THEN** la respuesta es `404` y el stock no cambia

#### Scenario: Sin rol de administración

- **WHEN** una cuenta sin rol `ADMIN` vigente intenta reponer stock
- **THEN** la respuesta es `403` y el stock no cambia

### Requirement: Movimientos de stock de sólo agregado

El sistema SHALL registrar un movimiento por cada variación del stock de un repuesto, con el repuesto, la cantidad positiva, el motivo, la cuenta que lo produjo y el momento, y SHALL NOT modificarlos ni borrarlos. La consulta de movimientos de un repuesto SHALL responder `200` con los movimientos del más reciente al más antiguo y `404` si el repuesto no existe.

#### Scenario: El alta con stock deja movimiento

- **WHEN** se da de alta un repuesto con stock inicial mayor que cero
- **THEN** queda un movimiento con esa cantidad, el motivo de stock inicial y la cuenta que dio el alta

#### Scenario: La reposición deja movimiento

- **WHEN** se repone stock de un repuesto
- **THEN** queda un movimiento con la cantidad repuesta, el motivo de reposición y la cuenta que repuso

#### Scenario: Consulta ordenada

- **WHEN** una cuenta con rol `ADMIN` vigente consulta los movimientos de un repuesto con varios movimientos
- **THEN** la respuesta es `200` y los devuelve del más reciente al más antiguo

#### Scenario: Repuesto inexistente

- **WHEN** se consultan los movimientos de un identificador que no corresponde a un repuesto vigente
- **THEN** la respuesta es `404`

#### Scenario: Sin rol de administración

- **WHEN** una cuenta sin rol `ADMIN` vigente consulta los movimientos de un repuesto
- **THEN** la respuesta es `403`

#### Scenario: Sin sesión

- **WHEN** se consultan los movimientos de un repuesto sin sesión
- **THEN** la respuesta es `401`

### Requirement: Consulta del historial de precios

El sistema SHALL devolver con `200` el historial de precios de un repuesto, del más reciente al más antiguo, con el precio anterior, el precio nuevo, la cuenta y el momento de cada cambio, y SHALL responder `404` si el repuesto no existe. La consulta SHALL requerir rol `ADMIN` vigente.

#### Scenario: Historial con cambios

- **WHEN** una cuenta con rol `ADMIN` vigente consulta el historial de un repuesto que tuvo cambios de precio
- **THEN** la respuesta es `200` e incluye una línea por cambio, del más reciente al más antiguo

#### Scenario: Historial vacío

- **WHEN** se consulta el historial de un repuesto que nunca cambió de precio
- **THEN** la respuesta es `200` con una lista vacía

#### Scenario: Repuesto inexistente

- **WHEN** se consulta el historial de un identificador que no corresponde a un repuesto vigente
- **THEN** la respuesta es `404`

#### Scenario: Sin rol de administración

- **WHEN** una cuenta sin rol `ADMIN` vigente consulta el historial de precios
- **THEN** la respuesta es `403`

### Requirement: Baja lógica de repuesto

El sistema SHALL dar de baja un repuesto vigente escribiendo su marca de baja, respondiendo `204` sin cuerpo y conservando la fila, y SHALL responder `404` si el repuesto no existe o ya está dado de baja. La operación SHALL requerir rol `ADMIN` vigente.

#### Scenario: Baja exitosa

- **WHEN** una cuenta con rol `ADMIN` vigente da de baja un repuesto vigente
- **THEN** la respuesta es `204` sin cuerpo, el repuesto deja de aparecer en el catálogo y la fila permanece almacenada

#### Scenario: Baja repetida

- **WHEN** se da de baja un repuesto que ya estaba dado de baja
- **THEN** la respuesta es `404` y su marca de baja original se conserva

#### Scenario: Repuesto dado de baja fuera de las operaciones

- **WHEN** se intenta editar, reponer o consultar los movimientos o precios de un repuesto dado de baja
- **THEN** la respuesta es `404`

#### Scenario: Movimientos e historial conservados

- **WHEN** se da de baja un repuesto que tenía movimientos e historial de precios
- **THEN** esas filas permanecen almacenadas con su referencia al repuesto y no se modifican

#### Scenario: Sin rol de administración

- **WHEN** una cuenta sin rol `ADMIN` vigente intenta dar de baja un repuesto
- **THEN** la respuesta es `403` y el repuesto permanece vigente
