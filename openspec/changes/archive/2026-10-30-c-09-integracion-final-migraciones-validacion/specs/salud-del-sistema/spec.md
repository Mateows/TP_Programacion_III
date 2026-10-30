# Spec Delta

## Purpose

Define las sondas de salud y monitoreo del sistema (liveness y readiness) para verificar la disponibilidad del servicio y su conectividad con la base de datos sin requerir autenticación.

## ADDED Requirements

### Requirement: Health check de actividad (live)
El sistema SHALL responder con estado `200` y confirmación de actividad operativa ante peticiones `GET /health/live`. Esta operación SHALL NOT interactuar con la base de datos ni requerir autenticación.

#### Scenario: Petición exitosa de liveness
- **WHEN** un cliente o sonda realiza una petición `GET /health/live`
- **THEN** el sistema responde `200 OK` con un cuerpo que indica disponibilidad sin consultar la base de datos

### Requirement: Health check de disponibilidad (ready)
El sistema SHALL verificar la conectividad con la base de datos ejecutando una consulta asíncrona de prueba (`SELECT 1`) ante peticiones `GET /health/ready` sin requerir autenticación previa. SHALL responder `200` si la base responde correctamente y `503` si la conexión falla o se encuentra inaccesible.

#### Scenario: Base de datos disponible y lista
- **WHEN** un cliente o sonda realiza una petición `GET /health/ready` y la base de datos responde exitosamente
- **THEN** el sistema responde `200 OK`

#### Scenario: Base de datos inaccesible o desconectada
- **WHEN** un cliente o sonda realiza una petición `GET /health/ready` y la base de datos no contesta o falla la consulta
- **THEN** el sistema responde `503 Service Unavailable`
