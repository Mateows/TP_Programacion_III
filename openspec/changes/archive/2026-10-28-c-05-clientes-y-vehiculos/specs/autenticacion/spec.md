# Spec Delta

## MODIFIED Requirements

### Requirement: Registro de cuenta de cliente

El sistema SHALL crear, en una sola operación atómica, la cuenta de usuario, su asignación de rol `CLIENTE` y su ficha de cliente cuando el registro recibe correo, nombre, documento, teléfono opcional y contraseña válidos; SHALL responder `201` y dejar la sesión iniciada. Si alguna de las tres filas no se puede crear, no SHALL quedar ninguna almacenada.

#### Scenario: Registro exitoso

- **WHEN** se solicita el registro con un correo no registrado, un nombre, un documento no registrado y una contraseña válida
- **THEN** se almacenan la cuenta con su hash de contraseña, la asignación del rol `CLIENTE` y la ficha de cliente vinculada a esa cuenta
- **AND** la respuesta es `201` e incluye la cookie de sesión

#### Scenario: Correo ya registrado

- **WHEN** se solicita el registro con un correo que ya pertenece a una cuenta
- **THEN** la respuesta es `409` y no queda ninguna cuenta, asignación ni ficha nueva

#### Scenario: Documento ya registrado

- **WHEN** se solicita el registro con un documento que ya pertenece a un cliente del taller
- **THEN** la respuesta es `409` y no queda ninguna cuenta, asignación ni ficha nueva
- **AND** la ficha existente no se vincula a la cuenta solicitada

#### Scenario: Documento faltante

- **WHEN** se solicita el registro sin documento
- **THEN** la respuesta es `422` y no queda ninguna fila nueva

#### Scenario: Teléfono opcional

- **WHEN** se solicita el registro sin teléfono
- **THEN** el registro se acepta y la ficha queda almacenada sin teléfono

#### Scenario: Fallo al crear la asignación de rol

- **WHEN** la cuenta se crea pero la asignación del rol `CLIENTE` falla
- **THEN** ninguna de las tres filas queda almacenada

#### Scenario: Fallo al crear la ficha de cliente

- **WHEN** la cuenta y la asignación se crean pero la ficha de cliente falla
- **THEN** ninguna de las tres filas queda almacenada
