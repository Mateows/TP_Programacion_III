# Spec Delta

## Purpose

Define cómo una persona acredita su identidad ante el sistema y mantiene una sesión: registro, inicio y cierre de sesión, consulta de la sesión propia, cambio de contraseña, emisión y vigencia del token, y límite de intentos fallidos.

## ADDED Requirements

### Requirement: Registro de cuenta de cliente

El sistema SHALL crear, en una sola operación atómica, la cuenta de usuario y su asignación de rol `CLIENTE` cuando el registro recibe correo, nombre y contraseña válidos; SHALL responder `201` y dejar la sesión iniciada. Si la cuenta o la asignación no se pueden crear, no SHALL quedar ninguna de las dos almacenada.

#### Scenario: Registro exitoso

- **WHEN** se solicita el registro con un correo no registrado, un nombre y una contraseña válida
- **THEN** se almacenan la cuenta con su hash de contraseña y la asignación del rol `CLIENTE`
- **AND** la respuesta es `201` e incluye la cookie de sesión

#### Scenario: Correo ya registrado

- **WHEN** se solicita el registro con un correo que ya pertenece a una cuenta
- **THEN** la respuesta es `409` y no queda ninguna cuenta ni asignación nueva

#### Scenario: Fallo al crear la asignación de rol

- **WHEN** la cuenta se crea pero la asignación del rol `CLIENTE` falla
- **THEN** ninguna de las dos filas queda almacenada

### Requirement: Contraseña de 1 a 72 bytes

El sistema SHALL aceptar únicamente contraseñas cuya representación UTF-8 tenga entre 1 y 72 bytes, y SHALL rechazar con `422` cualquier contraseña vacía o que exceda ese tamaño.

#### Scenario: Contraseña en el límite

- **WHEN** se recibe una contraseña cuya representación UTF-8 ocupa exactamente 72 bytes
- **THEN** la contraseña se acepta

#### Scenario: Contraseña que excede el límite

- **WHEN** se recibe una contraseña cuya representación UTF-8 ocupa 73 bytes o más
- **THEN** la respuesta es `422` y no se almacena ni modifica ninguna cuenta

#### Scenario: Contraseña vacía

- **WHEN** se recibe una contraseña vacía
- **THEN** la respuesta es `422`

### Requirement: Token entregado solo en cookie de sesión

El sistema SHALL entregar el token de acceso únicamente en la cookie `access_token`, marcada `HttpOnly` y `SameSite=Lax`, con `Max-Age` igual a la vigencia del token. El cuerpo de la respuesta SHALL NOT contener el token y la API SHALL NOT aceptar `Authorization: Bearer` como credencial.

#### Scenario: Inicio de sesión exitoso

- **WHEN** un inicio de sesión se verifica correctamente
- **THEN** la respuesta incluye `Set-Cookie` con la cookie `access_token` marcada `HttpOnly` y `SameSite=Lax`
- **AND** `Max-Age` coincide con la vigencia configurada del token

#### Scenario: Token ausente del cuerpo

- **WHEN** un inicio de sesión se verifica correctamente
- **THEN** el cuerpo contiene el mensaje, el indicador de cambio de contraseña pendiente y los segundos de vigencia
- **AND** el cuerpo no contiene el token

#### Scenario: Credencial enviada por header

- **WHEN** una petición protegida envía el token en `Authorization` y no envía la cookie de sesión
- **THEN** la respuesta es `401`

### Requirement: Inicio de sesión con credenciales válidas

El sistema SHALL iniciar sesión cuando el correo corresponde a una cuenta activa y la contraseña coincide con su hash, respondiendo `200`, entregando la cookie de sesión y registrando el intento como exitoso.

#### Scenario: Credenciales válidas

- **WHEN** se inicia sesión con el correo de una cuenta activa y su contraseña correcta
- **THEN** la respuesta es `200` con la cookie de sesión
- **AND** el intento queda registrado como exitoso

#### Scenario: Cuenta inactiva

- **WHEN** se inicia sesión con el correo de una cuenta inactiva y su contraseña correcta
- **THEN** la respuesta es `401`, sin cookie de sesión
- **AND** el intento queda registrado como no exitoso

### Requirement: Respuesta uniforme ante credenciales inválidas

El sistema SHALL responder con el mismo estado `401` y el mismo cuerpo cuando el correo no existe, cuando la contraseña no coincide y cuando la cuenta está inactiva. Cuando el correo no existe SHALL verificar la contraseña contra un hash ficticio, para no revelar la existencia de la cuenta ni acortar el tiempo de respuesta.

#### Scenario: Correo inexistente

- **WHEN** se inicia sesión con un correo que no corresponde a ninguna cuenta
- **THEN** la respuesta es `401` con el cuerpo genérico de credenciales inválidas
- **AND** la contraseña se verifica contra el hash ficticio

#### Scenario: Contraseña incorrecta

- **WHEN** se inicia sesión con el correo de una cuenta existente y una contraseña que no coincide
- **THEN** la respuesta es `401` con el mismo cuerpo genérico

#### Scenario: Comparación de respuestas

- **WHEN** se comparan las respuestas de un correo inexistente y de una contraseña incorrecta
- **THEN** ambas tienen el mismo estado y el mismo cuerpo

### Requirement: Límite de intentos fallidos por correo y dirección

El sistema SHALL rechazar el inicio de sesión con `429` y `Retry-After` cuando existan cinco intentos fallidos del mismo correo desde la misma dirección en los últimos 60 segundos, sin verificar la contraseña ni emitir cookie. Un inicio de sesión exitoso SHALL reiniciar el conteo de fallos.

#### Scenario: Sexto intento dentro de la ventana

- **WHEN** ya hay cinco fallos del mismo correo desde la misma dirección en los últimos 60 segundos y se intenta un nuevo inicio de sesión
- **THEN** la respuesta es `429` con `Retry-After`
- **AND** no se verifica la contraseña ni se emite cookie

#### Scenario: Quinto fallo

- **WHEN** se produce el quinto fallo del mismo correo desde la misma dirección dentro de la ventana
- **THEN** la contraseña se verifica y la respuesta es `401`

#### Scenario: Inicio de sesión exitoso reinicia el conteo

- **WHEN** un inicio de sesión se verifica correctamente después de fallos previos
- **THEN** los fallos anteriores dejan de contar para el límite
- **AND** los registros previos permanecen almacenados

#### Scenario: Fallo fuera de la ventana

- **WHEN** el fallo más antiguo del mismo correo y dirección ocurrió hace más de 60 segundos
- **THEN** ese fallo no cuenta para el límite

### Requirement: Registro de intentos de acceso

El sistema SHALL registrar cada intento de inicio de sesión con su marca temporal, el correo declarado, la dirección IP de origen y el resultado, en una transacción independiente que se confirma aunque la petición termine en error. Las respuestas `429` SHALL NOT agregar un nuevo fallo al conteo.

#### Scenario: Intento fallido persistido

- **WHEN** un inicio de sesión falla por contraseña incorrecta
- **THEN** el intento queda almacenado como no exitoso con correo, dirección y marca temporal

#### Scenario: Intento exitoso persistido

- **WHEN** un inicio de sesión se verifica correctamente
- **THEN** el intento queda almacenado como exitoso con correo, dirección y marca temporal

#### Scenario: Respuesta de límite excedido

- **WHEN** el inicio de sesión se rechaza con `429`
- **THEN** no se agrega un nuevo intento fallido que prolongue el bloqueo

#### Scenario: Error posterior al registro

- **WHEN** la petición falla después de registrar el intento
- **THEN** el intento registrado permanece almacenado

### Requirement: Consulta de la sesión propia

El sistema SHALL devolver, para una sesión válida, la cuenta autenticada con su identificador, correo, nombre, indicador de actividad, indicador de cambio de contraseña pendiente, los roles vigentes en la base y los roles informativos del token. Sin sesión válida SHALL responder `401`.

#### Scenario: Sesión válida

- **WHEN** se consulta la sesión propia con una cookie de sesión válida
- **THEN** la respuesta incluye los datos de la cuenta, sus roles vigentes y los roles del token

#### Scenario: Sin cookie de sesión

- **WHEN** se consulta la sesión propia sin cookie de sesión
- **THEN** la respuesta es `401`

#### Scenario: Token vencido

- **WHEN** se consulta la sesión propia con un token vencido
- **THEN** la respuesta es `401`

### Requirement: Cierre de sesión

El sistema SHALL eliminar la cookie de sesión al solicitar el cierre, respondiendo `200` incluso cuando no haya una sesión válida.

#### Scenario: Cierre con sesión activa

- **WHEN** se solicita el cierre con una cookie de sesión válida
- **THEN** la respuesta es `200` e indica el borrado de la cookie

#### Scenario: Cierre sin sesión

- **WHEN** se solicita el cierre sin cookie de sesión
- **THEN** la respuesta es `200` e indica el borrado de la cookie

### Requirement: Cambio de contraseña autenticado

El sistema SHALL permitir cambiar la contraseña a una cuenta con sesión válida cuando la contraseña actual coincide y la nueva cumple el límite de tamaño. La operación SHALL actualizar el hash y la marca del último cambio, quitar el cambio pendiente y dejar la sesión iniciada con un token nuevo.

#### Scenario: Cambio exitoso

- **WHEN** una cuenta con sesión válida envía su contraseña actual correcta y una nueva válida
- **THEN** la respuesta es `200` e incluye una cookie de sesión nueva
- **AND** la cuenta queda con el hash nuevo y sin cambio de contraseña pendiente

#### Scenario: Contraseña actual incorrecta

- **WHEN** la contraseña actual enviada no coincide
- **THEN** la respuesta es `401` y la cuenta no cambia

#### Scenario: Nueva contraseña fuera del límite

- **WHEN** la nueva contraseña está vacía o excede 72 bytes UTF-8
- **THEN** la respuesta es `422` y la cuenta no cambia

#### Scenario: Cambio pendiente

- **WHEN** una cuenta con cambio de contraseña pendiente cambia su contraseña
- **THEN** la operación se permite y el indicador de cambio pendiente queda en falso

### Requirement: Invalidación de sesiones anteriores al cambio de contraseña

El sistema SHALL rechazar con `401` todo token emitido antes de la marca del último cambio de contraseña de su cuenta y SHALL aceptar el token emitido por el propio cambio, incluso si ambos ocurren en el mismo segundo.

#### Scenario: Token emitido antes del cambio

- **WHEN** se usa un token cuya marca de emisión es anterior al último cambio de contraseña
- **THEN** la respuesta es `401`

#### Scenario: Token emitido por el propio cambio

- **WHEN** se usa el token devuelto por la operación de cambio de contraseña
- **THEN** la petición se acepta

#### Scenario: Token emitido después del cambio

- **WHEN** se usa un token emitido después del último cambio de contraseña
- **THEN** la petición se acepta

#### Scenario: Cambio y token en el mismo segundo

- **WHEN** el cambio de contraseña y la emisión del token nuevo coinciden en el segundo
- **THEN** el token anterior se rechaza y el token nuevo se acepta

### Requirement: Invalidación por cuenta inactiva

El sistema SHALL rechazar con `401` cualquier petición autenticada cuya cuenta haya dejado de estar activa, aunque el token siga vigente.

#### Scenario: Cuenta desactivada después de emitir el token

- **WHEN** una cuenta se marca como inactiva y se usa un token emitido antes de esa marca
- **THEN** la respuesta es `401`

#### Scenario: Cuenta activa

- **WHEN** la cuenta del token sigue activa
- **THEN** la petición se acepta

### Requirement: Registro de eventos de seguridad de la cuenta

El sistema SHALL registrar un evento de seguridad con actor `SISTEMA` en cada alta de cuenta y en cada cambio de contraseña, conservando el registro aunque la cuenta se modifique o se dé de baja.

#### Scenario: Alta de cuenta

- **WHEN** se registra una cuenta
- **THEN** queda un evento de seguridad con actor `SISTEMA` que identifica la operación de alta

#### Scenario: Cambio de contraseña

- **WHEN** una cuenta cambia su contraseña
- **THEN** queda un evento de seguridad con actor `SISTEMA` que identifica la operación de cambio

#### Scenario: Evento independiente de la cuenta

- **WHEN** la cuenta asociada al evento se modifica o se da de baja
- **THEN** el evento permanece almacenado
