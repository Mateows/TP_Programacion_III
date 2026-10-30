# estados-de-orden Specification

## Purpose

Define el catálogo de estados por los que atraviesa una orden de trabajo, su orden de avance y cuáles estados cierran la orden, para que las reglas de transición y de baja de vehículos tengan una fuente única.

## Requirements

### Requirement: Catálogo de estados identificado por código

El sistema SHALL persistir cada estado de orden con un código textual como identificador único, una descripción y una posición de ordenamiento.

#### Scenario: Estado con código propio

- **WHEN** se almacena un estado con código `PENDIENTE`
- **THEN** queda identificado por ese código y no por un identificador numérico independiente

#### Scenario: Código repetido

- **WHEN** se intenta almacenar un estado con un código ya existente
- **THEN** la operación se rechaza por violación de unicidad y el estado previo permanece intacto

### Requirement: Posición única en el catálogo

El sistema SHALL garantizar que dos estados no compartan la misma posición de ordenamiento.

#### Scenario: Posición repetida

- **WHEN** se intenta almacenar un estado con una posición ya ocupada
- **THEN** la operación se rechaza por violación de unicidad

#### Scenario: Posiciones distintas

- **WHEN** se almacenan estados con posiciones diferentes
- **THEN** el catálogo puede ordenarse de forma determinista por posición

### Requirement: Indicador de estado final

El sistema SHALL distinguir los estados que cierran la orden de los que la mantienen abierta mediante un indicador booleano de estado final.

#### Scenario: Estado final

- **WHEN** una orden se encuentra en un estado marcado como final
- **THEN** la orden se considera cerrada para efectos de baja de vehículos y de nuevas transiciones

#### Scenario: Estado no final

- **WHEN** una orden se encuentra en un estado no marcado como final
- **THEN** la orden se considera abierta

### Requirement: Catálogo de solo lectura desde la API

El sistema SHALL exponer el catálogo de estados únicamente para consulta; ninguna operación de la API SHALL crear, modificar ni eliminar estados.

#### Scenario: Consulta del catálogo

- **WHEN** un cliente autenticado consulta los estados disponibles
- **THEN** recibe los estados almacenados con su código, descripción, posición e indicador de estado final

#### Scenario: Intento de escritura

- **WHEN** un cliente intenta crear, modificar o eliminar un estado por la API
- **THEN** la operación no está disponible y el catálogo permanece sin cambios

### Requirement: Estados iniciales del ciclo de vida

El sistema SHALL operar con los estados `PENDIENTE`, `EN_REPARACION`, `TERMINADA` y `CANCELADA`, en las posiciones 1 a 4 respectivamente, siendo `TERMINADA` y `CANCELADA` los únicos estados finales.

#### Scenario: Orden recién creada

- **WHEN** se crea una orden de trabajo
- **THEN** su estado es `PENDIENTE`, que no es final

#### Scenario: Orden en reparación

- **WHEN** un mecánico inicia una orden pendiente
- **THEN** su estado pasa a `EN_REPARACION`, que no es final

#### Scenario: Orden terminada o cancelada

- **WHEN** una orden pasa a `TERMINADA` o a `CANCELADA`
- **THEN** el estado correspondiente es final y la orden deja de contar como abierta
