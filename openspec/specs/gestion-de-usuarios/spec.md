# gestion-de-usuarios Specification

## Purpose

Define las cuentas de acceso del taller y su trazabilidad: usuarios con credenciales propias, roles otorgados con vigencia y revocación, intentos de acceso y eventos de seguridad auditables.

## Requirements

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

### Requirement: Alta de personal por administrador

El sistema SHALL permitir a un administrador crear una cuenta de personal con correo, nombre y contraseña provisoria, respondiendo `201`. La cuenta SHALL quedar activa, con el cambio de contraseña pendiente y sin roles asignados. La contraseña SHALL NOT devolverse en la respuesta ni SHALL emitirse cookie de sesión.

#### Scenario: Alta exitosa

- **WHEN** un administrador crea una cuenta con un correo no registrado, un nombre y una contraseña válida
- **THEN** la respuesta es `201` y la cuenta queda activa, con el cambio de contraseña pendiente y sin ninguna asignación de rol
- **AND** la respuesta no incluye la contraseña ni una cookie de sesión

#### Scenario: Correo ya registrado

- **WHEN** un administrador intenta crear una cuenta con un correo que ya pertenece a otra cuenta
- **THEN** la respuesta es `409` y no queda ninguna cuenta nueva

#### Scenario: Contraseña fuera del límite

- **WHEN** la contraseña provisoria está vacía o su representación UTF-8 excede 72 bytes
- **THEN** la respuesta es `422` y no queda ninguna cuenta nueva

#### Scenario: El alta no acepta roles

- **WHEN** la solicitud de alta incluye un campo de roles
- **THEN** la respuesta es `422` y no queda ninguna cuenta nueva

#### Scenario: Sin rol de administrador

- **WHEN** una cuenta sin rol `ADMIN` vigente solicita el alta de personal
- **THEN** la respuesta es `403` y no queda ninguna cuenta nueva

### Requirement: Roles asignables por la administración

El sistema SHALL aceptar únicamente los roles `ADMIN`, `RECEPCION` y `MECANICO` en las operaciones de administración de roles, y SHALL rechazar con `422` cualquier otro valor. El rol `CLIENTE` queda reservado al auto-registro.

#### Scenario: Rol de personal aceptado

- **WHEN** un administrador asigna uno de los roles `ADMIN`, `RECEPCION` o `MECANICO`
- **THEN** la operación se acepta

#### Scenario: Rol de cliente rechazado

- **WHEN** un administrador intenta asignar el rol `CLIENTE`
- **THEN** la respuesta es `422` y no se crea ninguna asignación

#### Scenario: Rol desconocido

- **WHEN** un administrador intenta asignar un rol que no pertenece al catálogo
- **THEN** la respuesta es `422` y no se crea ninguna asignación

### Requirement: Asignación de rol con vencimiento opcional

El sistema SHALL crear una asignación de rol para un usuario existente, con vencimiento opcional, respondiendo `201` y registrando como otorgante al administrador actuante. SHALL responder `404` si el usuario no existe, `422` si el vencimiento no es futuro o carece de zona horaria, y `409` si el usuario ya tiene una asignación abierta de ese rol.

#### Scenario: Asignación sin vencimiento

- **WHEN** un administrador asigna un rol sin indicar vencimiento
- **THEN** la respuesta es `201` y la asignación queda abierta y sin vencimiento

#### Scenario: Asignación con vencimiento futuro

- **WHEN** un administrador asigna un rol con un vencimiento futuro y con zona horaria
- **THEN** la respuesta es `201` y la asignación conserva ese vencimiento

#### Scenario: Vencimiento en el pasado

- **WHEN** un administrador asigna un rol con un vencimiento anterior al instante de la operación
- **THEN** la respuesta es `422` y no se crea ninguna asignación

#### Scenario: Vencimiento sin zona horaria

- **WHEN** un administrador asigna un rol con un vencimiento sin zona horaria
- **THEN** la respuesta es `422` y no se crea ninguna asignación

#### Scenario: Rol ya asignado

- **WHEN** un administrador asigna un rol que el usuario ya tiene en una asignación abierta
- **THEN** la respuesta es `409` y no se crea ninguna asignación nueva

#### Scenario: Usuario inexistente

- **WHEN** un administrador asigna un rol a un identificador de usuario que no existe
- **THEN** la respuesta es `404` y no se crea ninguna asignación

### Requirement: Reasignación de un rol vencido

El sistema SHALL, al asignar un rol cuya asignación abierta está vencida, cerrar esa asignación con su marca de revocación y crear una nueva, respondiendo `201`. La asignación anterior SHALL conservarse.

#### Scenario: Reasignación de un rol vencido

- **WHEN** un administrador asigna un rol cuya asignación abierta ya está vencida
- **THEN** la respuesta es `201`, la asignación anterior queda revocada y la nueva queda abierta

#### Scenario: Historial conservado

- **WHEN** se reasigna un rol vencido
- **THEN** la consulta de roles del usuario devuelve tanto la asignación anterior como la nueva

### Requirement: Revocación de rol sin borrar la fila

El sistema SHALL revocar una asignación abierta escribiendo su marca de revocación, sin borrar la fila, respondiendo `200`. SHALL responder `404` si el usuario no existe o no tiene una asignación abierta de ese rol.

#### Scenario: Revocación exitosa

- **WHEN** un administrador revoca un rol que el usuario tiene en una asignación abierta
- **THEN** la respuesta es `200` y la asignación queda con su marca de revocación
- **AND** la fila permanece almacenada

#### Scenario: Rol no asignado

- **WHEN** un administrador revoca un rol que el usuario no tiene en una asignación abierta
- **THEN** la respuesta es `404` y no se modifica ninguna asignación

#### Scenario: Revocación repetida

- **WHEN** un administrador revoca por segunda vez un rol ya revocado
- **THEN** la respuesta es `404` y la asignación conserva su marca original

### Requirement: Autoprotección del administrador

El sistema SHALL rechazar con `409` la revocación de una asignación `ADMIN` abierta del propio administrador actuante, aunque existan otros administradores vigentes.

#### Scenario: Intento de revocarse el propio rol ADMIN

- **WHEN** un administrador intenta revocar su propia asignación `ADMIN` abierta
- **THEN** la respuesta es `409` y la asignación permanece sin cambios

#### Scenario: Revocación de un rol propio que no es ADMIN

- **WHEN** un administrador revoca su propia asignación de otro rol
- **THEN** la revocación se acepta

#### Scenario: Revocación del ADMIN de otro usuario

- **WHEN** un administrador revoca la asignación `ADMIN` de otra cuenta
- **THEN** la revocación se acepta si no deja el sistema sin administradores vigentes

### Requirement: Al menos un administrador vigente

El sistema SHALL rechazar con `409` toda revocación que dejaría el sistema sin administradores vigentes. Una asignación `ADMIN` SHALL contar como vigente cuando no está revocada, su vencimiento no es anterior al instante de la operación y su cuenta está activa.

#### Scenario: Último administrador vigente

- **WHEN** una revocación dejaría cero asignaciones `ADMIN` vigentes
- **THEN** la respuesta es `409` y la asignación permanece sin cambios

#### Scenario: Queda otro administrador vigente

- **WHEN** una revocación deja al menos una asignación `ADMIN` vigente en otra cuenta
- **THEN** la revocación se acepta

#### Scenario: Administrador con cuenta inactiva

- **WHEN** la única otra asignación `ADMIN` pertenece a una cuenta inactiva
- **THEN** esa asignación no cuenta como administrador vigente y la revocación responde `409`

### Requirement: Consulta de roles de un usuario

El sistema SHALL devolver con `200` las asignaciones de rol de un usuario existente, incluidas las revocadas y las vencidas, ordenadas por fecha de inicio descendente, con su vencimiento y su marca de revocación. SHALL responder `404` si el usuario no existe.

#### Scenario: Usuario con historial de roles

- **WHEN** un administrador consulta los roles de un usuario que tuvo asignaciones revocadas
- **THEN** la respuesta es `200` e incluye las asignaciones abiertas, vencidas y revocadas

#### Scenario: Usuario sin roles

- **WHEN** un administrador consulta los roles de un usuario sin asignaciones
- **THEN** la respuesta es `200` con una lista vacía

#### Scenario: Usuario inexistente

- **WHEN** un administrador consulta los roles de un identificador de usuario que no existe
- **THEN** la respuesta es `404`

### Requirement: Auditoría de cambios de rol

El sistema SHALL registrar un evento de seguridad por cada alta de personal, asignación de rol y revocación de rol, identificando al administrador actuante como actor, dentro de la misma transacción que la operación auditada. El evento SHALL NOT quedar registrado si la operación no se confirma.

#### Scenario: Alta de personal auditada

- **WHEN** un administrador crea una cuenta de personal
- **THEN** queda un evento de seguridad cuyo actor identifica a ese administrador y cuya acción identifica el alta

#### Scenario: Asignación de rol auditada

- **WHEN** un administrador asigna un rol
- **THEN** queda un evento de seguridad cuyo actor identifica a ese administrador y cuya acción identifica la asignación

#### Scenario: Revocación de rol auditada

- **WHEN** un administrador revoca un rol
- **THEN** queda un evento de seguridad cuyo actor identifica a ese administrador y cuya acción identifica la revocación

#### Scenario: Operación rechazada sin evento

- **WHEN** una operación de alta o de roles se rechaza por una regla de negocio
- **THEN** no queda ningún evento de seguridad de esa operación

### Requirement: Consulta paginada de eventos de seguridad

El sistema SHALL devolver con `200` los eventos de seguridad paginados, del más reciente al más antiguo, con el total de eventos y la cantidad de páginas. SHALL aceptar `page` desde 1 y `size` entre 1 y 100 con 20 por defecto, y responder `422` fuera de rango o cuando la página solicitada supera la última.

#### Scenario: Consulta con valores por defecto

- **WHEN** un administrador consulta los eventos sin indicar paginación
- **THEN** la respuesta es `200` con hasta 20 eventos de la primera página
- **AND** incluye el total de eventos y la cantidad de páginas

#### Scenario: Página fuera de rango

- **WHEN** la página solicitada supera la última disponible
- **THEN** la respuesta es `422`

#### Scenario: Tamaño de página inválido

- **WHEN** `size` es menor que 1 o mayor que 100
- **THEN** la respuesta es `422`

#### Scenario: Orden estable entre eventos simultáneos

- **WHEN** dos eventos comparten la misma marca temporal
- **THEN** el orden entre ellos es determinista y no se repite ni se omite un evento entre páginas

#### Scenario: Sin rol de administrador

- **WHEN** una cuenta sin rol `ADMIN` vigente consulta los eventos
- **THEN** la respuesta es `403`
