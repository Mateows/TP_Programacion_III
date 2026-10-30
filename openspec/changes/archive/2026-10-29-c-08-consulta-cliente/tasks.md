# Tasks

## 1. Contratos y consulta de repositorio

- [x] 1.1 Definir el schema de respuesta paginada de `GET /mis-ordenes`, reutilizando únicamente campos compatibles del dominio y verificando que el contrato no acepte identificadores de alcance del cliente.
- [x] 1.2 Implementar en el repositorio de órdenes la consulta paginada filtrada por la ficha de cliente autenticada, incluyendo órdenes de vehículos dados de baja, aplicando carga anticipada y verificando el filtro con una prueba unitaria de aislamiento.
- [x] 1.3 Agregar al service la resolución de la ficha de cliente y el manejo explícito de ausencia de ficha como `403`, verificando que nunca se ejecute una consulta sin filtro de ownership.

## 2. Ruta y pruebas de comportamiento

- [x] 2.1 Exponer `GET /mis-ordenes` en el router de órdenes con autenticación estándar, parámetros de paginación y traducción de errores `401`, `403` y `422`; verificar el contrato mediante pruebas de integración.
- [x] 2.2 Cubrir con pruebas de integración cliente con órdenes, cliente sin órdenes, órdenes ajenas, vehículo dado de baja, ausencia de sesión, ficha inexistente, página fuera de rango y tamaños inválidos.
- [x] 2.3 Ejecutar las pruebas unitarias y de integración del módulo de órdenes y verificar que las rutas existentes de C-07 mantienen sus respuestas y permisos.

## Workflow follow-up

- Archive the change after review and successful validation.
