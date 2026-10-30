# Spec Delta

## Purpose

Define las cuentas de acceso del taller y su trazabilidad: usuarios con credenciales propias, roles otorgados con vigencia y revocación, intentos de acceso y eventos de seguridad auditables.

## ADDED Requirements

### Requirement: Cuenta de usuario persistente

El sistema SHALL persistir cada cuenta de usuario con identificador propio, correo, nombre, hash de contraseña, indicador de actividad, indicador de cambio de contraseña pendiente y la marca temporal del último cambio de contraseña.

#### Scenario: Alta de una cuenta

- **WHEN** se registra un usuario con correo, nombre y contraseña
- **THEN** queda almacenada una cuenta con su hash de contraseña, `activo` en verdadero y `debe_cambiar_password` en falso
- **AND** la marca de último cambio de contraseña queda registrada como fecha con zona horaria

#### Scenario: Cuenta con cambio de contraseña pendiente

- **WHEN** una cuenta se crea con la obligación de cambiar la contraseña
- **THEN** la cuenta conserva ese indicador hasta que la contraseña se cambie
- **AND** la marca de último cambio de contraseña puede permanecer vacía

### Requirement: Correo de usuario único

El sistema SHALL garantizar que no existan dos cuentas con el mismo correo.

#### Scenario: Correo repetido

- **WHEN** se intenta registrar una cuenta con un correo ya existente
- **THEN** la operación se rechaza por violación de unicidad
- **AND** no queda ninguna cuenta nueva almacenada

#### Scenario: Correos distintos

- **WHEN** se registran dos cuentas con correos diferentes
- **THEN** ambas cuentas quedan almacenadas

### Requirement: Roles asignados con vigencia

El sistema SHALL representar los roles como asignaciones independientes de cada usuario, con rol, fecha de otorgamiento, vencimiento opcional, revocación opcional y quién la otorgó; la cuenta de usuario no SHALL tener un campo de rol propio.

#### Scenario: Asignación abierta

- **WHEN** se otorga un rol a un usuario sin fecha de vencimiento ni revocación
- **THEN** la asignación queda abierta y el rol cuenta como vigente para ese usuario

#### Scenario: Asignación vencida

- **WHEN** una asignación tiene fecha de vencimiento anterior al momento de la consulta
- **THEN** el rol no cuenta como vigente para ese usuario

#### Scenario: Asignación revocada

- **WHEN** una asignación tiene fecha de revocación registrada
- **THEN** el rol no cuenta como vigente para ese usuario aunque no haya vencido

### Requirement: Una sola asignación abierta por rol

El sistema SHALL impedir que un mismo usuario tenga más de una asignación abierta para el mismo rol, entendiendo por abierta toda asignación sin fecha de revocación.

#### Scenario: Rol ya asignado

- **WHEN** se intenta otorgar a un usuario un rol que ya tiene asignado sin revocar
- **THEN** la operación se rechaza por violación de unicidad
- **AND** la asignación previa permanece intacta

#### Scenario: Rol revocado y vuelto a otorgar

- **WHEN** un usuario tiene un rol revocado y se le otorga el mismo rol nuevamente
- **THEN** la nueva asignación queda abierta y la revocada se conserva como historial

### Requirement: Catálogo cerrado de roles

El sistema SHALL aceptar únicamente los roles `ADMIN`, `RECEPCION`, `MECANICO` y `CLIENTE` en las asignaciones.

#### Scenario: Rol válido

- **WHEN** se otorga cualquiera de los cuatro roles admitidos
- **THEN** la asignación se almacena correctamente

#### Scenario: Rol desconocido

- **WHEN** se intenta otorgar un rol fuera del catálogo
- **THEN** la operación se rechaza y no queda ninguna asignación almacenada

### Requirement: Registro de intentos de acceso

El sistema SHALL registrar cada intento de acceso con la marca temporal, el correo declarado, la dirección IP de origen y el resultado de la verificación, para permitir el conteo de fallos por correo y dirección dentro de una ventana de tiempo.

#### Scenario: Intento fallido registrado

- **WHEN** un acceso falla por contraseña incorrecta
- **THEN** queda un registro con el correo, la IP, la marca temporal y resultado fallido

#### Scenario: Intento exitoso registrado

- **WHEN** un acceso se verifica correctamente
- **THEN** queda un registro con el correo, la IP, la marca temporal y resultado exitoso

#### Scenario: Conteo por correo y dirección

- **WHEN** se consultan los intentos fallidos de un correo desde una dirección en una ventana de tiempo
- **THEN** la consulta puede resolverse usando el correo, la dirección y la marca temporal como criterio de búsqueda

### Requirement: Registro de eventos de seguridad

El sistema SHALL registrar eventos de seguridad con marca temporal, actor y acción, donde el actor es un identificador textual que puede representar a un usuario o al propio sistema y no requiere una cuenta existente.

#### Scenario: Evento originado por el sistema

- **WHEN** el sistema realiza una acción auditable sin intervención de una persona
- **THEN** el evento se registra con el actor `SISTEMA` y la acción correspondiente

#### Scenario: Evento originado por una persona

- **WHEN** una persona realiza una acción auditable
- **THEN** el evento se registra con el actor textual que la identifica y la acción correspondiente

### Requirement: Fechas con zona horaria

El sistema SHALL almacenar todas las marcas temporales de cuentas, asignaciones, intentos de acceso y eventos de seguridad como fechas con zona horaria.

#### Scenario: Persistencia de una marca temporal

- **WHEN** se guarda cualquier marca temporal de estas entidades
- **THEN** al recuperarla conserva su zona horaria y no se interpreta como hora local ambigua
