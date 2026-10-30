# Spec Delta

## ADDED Requirements

### Requirement: Roles vigentes resueltos en cada petición

El sistema SHALL determinar los permisos de una petición autenticada consultando las asignaciones de rol vigentes de la cuenta en ese momento. Una asignación SHALL contar como vigente cuando no tiene revocación y su vencimiento, si existe, no es anterior al instante de la consulta. Los roles incluidos en el token SHALL ser solo informativos.

#### Scenario: Rol revocado durante la sesión

- **WHEN** una cuenta con sesión abierta pierde la vigencia de un rol por revocación
- **THEN** la siguiente petición que exija ese rol responde `403`
- **AND** no es necesario esperar el vencimiento del token

#### Scenario: Rol vencido

- **WHEN** una asignación tiene fecha de vencimiento anterior al instante de la consulta
- **THEN** ese rol no cuenta para los permisos de la petición

#### Scenario: Rol otorgado durante la sesión

- **WHEN** se otorga un rol a una cuenta con sesión abierta
- **THEN** la siguiente petición reconoce el rol sin necesidad de emitir un token nuevo

#### Scenario: Rol ausente del token pero vigente en la base

- **WHEN** el token de la sesión no incluye un rol que la cuenta tiene vigente en la base
- **THEN** la petición que exija ese rol se acepta

#### Scenario: Rol incluido en el token pero no vigente en la base

- **WHEN** el token de la sesión incluye un rol que la cuenta ya no tiene vigente en la base
- **THEN** la petición que exija ese rol responde `403`
