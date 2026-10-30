# Design

## Context

La autenticación ya identifica al usuario y las órdenes de C-07 relacionan cada orden con un vehículo y su cliente. La consulta nueva debe derivar el alcance desde la sesión, conservar el acceso histórico a órdenes de vehículos dados de baja y mantener las reglas existentes de paginación, carga anticipada y Unit of Work.

## Goals / Non-Goals

**Goals:**

- Agregar una ruta de sólo lectura para consultar las órdenes propias del cliente.
- Garantizar el aislamiento por relación usuario → ficha de cliente → vehículo → orden.
- Reutilizar los contratos de respuesta y mecanismos de paginación del módulo de órdenes cuando sean compatibles.
- Resolver la consulta con un número fijo de consultas y carga anticipada suficiente para evitar N+1. En este proyecto la carga anticipada se implementa con `JOIN` explícitos porque los modelos son planos y no declaran `Relationship`.

**Non-Goals:**

- No modificar `GET /ordenes`, `GET /ordenes/{id}` ni `GET /estados-orden`.
- No permitir que el cliente filtre por otro `cliente_id`, `usuario_id` o vehículo arbitrario.
- No agregar filtros de estado, búsqueda, ordenamiento ni nuevas tablas en este change.
- No cambiar las reglas de cancelación o transición de órdenes.

## Decisions

### Derivar el alcance de la sesión

La ruta recibirá la identidad autenticada desde la dependencia estándar y buscará la ficha de cliente vinculada al usuario. La consulta de órdenes se limitará por la relación con esa ficha, sin confiar en identificadores enviados por el cliente. Esto evita enumeración o acceso horizontal a datos.

### Conservar órdenes históricas

La relación de ownership se evaluará por `cliente_id` del vehículo, no por el estado de vigencia del vehículo. Así, una baja lógica no elimina del historial las órdenes que el cliente necesita consultar.

### Mantener la paginación existente

Se usarán los mismos límites públicos de página y tamaño que el listado general: página desde 1, tamaño entre 1 y 100, valor por omisión 20 y `422` cuando la página supera la última. La respuesta conservará los metadatos `items`, `total`, `page`, `size` y `pages`.

### Separar autorización de ausencia de ficha

La ausencia de sesión produce `401` mediante la dependencia estándar. Una cuenta autenticada sin ficha de cliente no puede usar la consulta propia y produce `403`, sin convertir esa ausencia en una consulta sin filtro.

### Reutilizar capas existentes

La implementación se incorporará al módulo de órdenes siguiendo Router → Service → UoW → Repository → Models → Schemas. El repositorio debe aplicar el filtro de ownership y carga anticipada en la consulta; no se agregará `commit()` ni lógica de autorización al repositorio.

## Risks / Trade-offs

- [Riesgo] El cliente podría obtener demasiados datos si se reutiliza sin cuidado el DTO del detalle de orden → [Mitigación] definir o adaptar un schema de salida específico para `mis-ordenes` y verificar que no incluya datos internos innecesarios.
- [Riesgo] La consulta podría introducir N+1 al cargar vehículo, cliente o estado → [Mitigación] usar `JOIN` explícitos como estrategia de carga anticipada y tests que inspeccionen el número esperado de consultas.
- [Riesgo] Una cuenta válida puede no tener ficha por datos inconsistentes → [Mitigación] responder `403` explícito y no ejecutar una consulta de órdenes sin filtro de cliente.
