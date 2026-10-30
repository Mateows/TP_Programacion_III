# Spec Delta

## Purpose

Define los contratos de acceso a datos que todos los módulos comparten: transacciones atómicas, escrituras que no confirman por sí solas, borrado lógico, lecturas con carga anticipada y un catálogo de solo lectura.

## ADDED Requirements

### Requirement: Transacción atómica por unidad de trabajo

El sistema SHALL agrupar las operaciones de escritura de una unidad de trabajo en una sola transacción: al salir correctamente se confirman todas juntas y ante cualquier excepción se revierte el conjunto completo.

#### Scenario: Salida exitosa

- **WHEN** una unidad de trabajo termina sin excepciones
- **THEN** todas las escrituras realizadas dentro del bloque quedan confirmadas de forma conjunta

#### Scenario: Excepción durante el bloque

- **WHEN** una operación lanza una excepción dentro de la unidad de trabajo
- **THEN** ninguna de las escrituras del bloque queda confirmada
- **AND** la excepción se propaga a quien invocó la unidad de trabajo

#### Scenario: Varias escrituras relacionadas

- **WHEN** una unidad de trabajo crea varias filas relacionadas y una de ellas falla
- **THEN** no queda ninguna de las filas creadas en ese bloque

### Requirement: Los repositorios no confirman transacciones

El sistema SHALL limitar los repositorios a enviar los cambios pendientes a la base sin confirmarlos; la confirmación SHALL ser responsabilidad exclusiva de la unidad de trabajo.

#### Scenario: Escritura desde un repositorio

- **WHEN** un repositorio crea o modifica una fila
- **THEN** el cambio queda visible dentro de la transacción en curso pero no confirmado
- **AND** si la unidad de trabajo se revierte, el cambio no persiste

#### Scenario: Reutilización de un repositorio fuera de una unidad de trabajo

- **WHEN** un repositorio se usa sin una unidad de trabajo que confirme
- **THEN** sus escrituras no quedan confirmadas por el propio repositorio

### Requirement: La unidad de trabajo no cierra la sesión que no creó

El sistema SHALL liberar únicamente los recursos que la unidad de trabajo creó; cuando recibe una sesión existente, SHALL dejarla abierta y utilizable al finalizar el bloque.

#### Scenario: Sesión recibida de una dependencia

- **WHEN** la unidad de trabajo se construye sobre una sesión entregada por la capa que la invoca
- **THEN** al terminar el bloque la sesión sigue abierta y puede reutilizarse

#### Scenario: Sesión propia

- **WHEN** la unidad de trabajo crea su propia sesión
- **THEN** la libera al terminar el bloque

### Requirement: Borrado lógico de entidades descartables

El sistema SHALL dar de baja las entidades que admiten borrado lógico marcando una fecha de baja y conservando la fila, sin eliminarla físicamente.

#### Scenario: Baja de una entidad

- **WHEN** se da de baja una entidad que admite borrado lógico
- **THEN** la fila permanece almacenada con su marca de baja
- **AND** la entidad deja de aparecer en las consultas habituales

#### Scenario: Consulta habitual

- **WHEN** se listan o buscan entidades de un tipo con borrado lógico
- **THEN** los resultados excluyen las entidades dadas de baja

#### Scenario: Consulta explícita incluyendo dadas de baja

- **WHEN** se solicita una entidad por identificador incluyendo las dadas de baja
- **THEN** la entidad se devuelve aunque tenga marca de baja

#### Scenario: Baja repetida

- **WHEN** se intenta dar de baja una entidad que ya tiene marca de baja
- **THEN** la operación no altera la marca existente

### Requirement: Lecturas con carga anticipada

El sistema SHALL cargar en la misma operación de lectura las relaciones que el repositorio declara como necesarias, sin dejar relaciones pendientes de carga diferida.

#### Scenario: Lectura de una entidad con relaciones

- **WHEN** un repositorio devuelve una entidad junto con relaciones declaradas
- **THEN** las relaciones ya están cargadas al recibir el resultado
- **AND** acceder a ellas no dispara consultas adicionales

#### Scenario: Listado de entidades con relaciones

- **WHEN** un repositorio devuelve un listado de entidades con relaciones declaradas
- **THEN** el número de consultas no crece con la cantidad de filas devueltas

### Requirement: Catálogo consultado mediante repositorio de solo lectura

El sistema SHALL acceder al catálogo de estados mediante un repositorio de solo lectura que no ofrece operaciones de escritura y que lo identifica por su código.

#### Scenario: Lectura del catálogo

- **WHEN** un servicio necesita los estados disponibles
- **THEN** obtiene las filas del catálogo mediante operaciones de lectura

#### Scenario: Intento de escritura sobre el catálogo

- **WHEN** un servicio intenta escribir en el catálogo a través de su repositorio
- **THEN** la operación no está disponible

### Requirement: Los errores de integridad no exponen el esquema

El sistema SHALL traducir los rechazos de integridad de la base a un error de dominio comprensible, sin propagar nombres de tablas, columnas, restricciones ni sentencias.

#### Scenario: Violación de unicidad

- **WHEN** una escritura viola una restricción de unicidad
- **THEN** quien invoca recibe un error de dominio identificable
- **AND** el mensaje no contiene detalles internos del esquema

#### Scenario: Violación de clave foránea o de verificación

- **WHEN** una escritura viola una clave foránea o una restricción de verificación
- **THEN** quien invoca recibe un error de dominio identificable
- **AND** el mensaje no contiene detalles internos del esquema
