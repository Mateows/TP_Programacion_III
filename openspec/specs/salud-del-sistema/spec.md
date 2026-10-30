# salud-del-sistema Specification

## Purpose

Exponer sondas de salud y monitoreo para verificar la disponibilidad operativa del servicio y su conectividad con la base de datos sin requerir autenticación. Permiten a la infraestructura (orquestadores, balanceadores) distinguir entre un proceso caído y uno con dependencias no disponibles.

## Requirements

### Requirement: Health check de actividad (liveness)

El sistema SHALL responder `GET /health/live` con `200` y un cuerpo de confirmación de actividad sin interactuar con la base de datos ni requerir autenticación.

#### Scenario: Petición exitosa de liveness

- **WHEN** un cliente o sonda realiza `GET /health/live`
- **THEN** la respuesta es `200` con `{"status": "ok"}` y sin consulta a la base de datos

#### Scenario: Liveness no requiere cookie de sesión

- **WHEN** la petición llega sin cookie de sesión válida
- **THEN** la respuesta es igualmente `200`, porque la ruta pertenece al grupo abierto

#### Scenario: Liveness no bloquea por cambio de contraseña pendiente

- **WHEN** la dependencia de cambio obligatorio de contraseña está activa en el router protegido
- **THEN** la sonda `live` no se ve afectada porque vive en el router abierto

### Requirement: Health check de disponibilidad (readiness)

El sistema SHALL verificar la conectividad con la base de datos ejecutando `SELECT 1` asíncrono ante `GET /health/ready`. SHALL responder `200` si la base contesta o `503` si la conexión falla, sin propagar mensajes internos del motor (credenciales, host, traza).

#### Scenario: Base de datos disponible

- **WHEN** un cliente o sonda realiza `GET /health/ready` y la base de datos responde a la consulta de prueba
- **THEN** la respuesta es `200` con `{"status": "ready"}`

#### Scenario: Base de datos inaccesible

- **WHEN** la base de datos no contesta o lanza una excepción al ejecutar la consulta de prueba
- **THEN** la respuesta es `503 Service Unavailable` con un mensaje genérico que no incluye credenciales ni detalles internos del motor

#### Scenario: Readiness no requiere autenticación

- **WHEN** la petición llega sin cookie de sesión válida
- **THEN** la respuesta es `200` o `503` según la disponibilidad de la base, nunca `401`
