# Design

## Context

Ver `proposal.md` — Why. El punto de partida relevante para el diseño:

- `app/core/security.py` ya expone `hash_password`, `verify_password`, `create_access_token` y `decode_access_token`; `iat` se emite con `int(time.time())`, es decir, truncado a segundos.
- `app/core/dependencies.py` devuelve el payload del JWT y lee los roles del claim `roles`; no consulta la base.
- `app/core/unit_of_work.py` y `app/core/repository.py` ya implementan el patrón UoW y el repositorio base con `flush()` sin `commit()`.
- `app/modules/usuarios/models.py` define `Usuario`, `AsignacionRol`, `IntentoAcceso` y `EventoSeguridad`; no hay relaciones ORM declaradas.
- `app/core/database.py` publica `get_session` y deja la fábrica de sesiones en `app.state.session_factory`.
- `app/main.py` separa `router_abierto` de `router_protegido`; este último aplica `require_password_change` a todas sus rutas.
- La suite de pruebas es síncrona y envuelve cada flujo async con `asyncio.run`; no hay `pytest-asyncio` instalado y no se va a agregar.

## Goals / Non-Goals

**Goals:**

- Implementar los cinco endpoints de `/auth` con la estructura de seis capas del proyecto.
- Corregir la emisión de `iat` para que la invalidación por cambio de contraseña sea exacta y no dependa de truncamientos.
- Hacer que la autorización use los roles vigentes en la base, sin cambiar el esquema de datos.
- Mantener el registro de intentos aunque la petición falle, sin extender el bloqueo con las respuestas `429`.

**Non-Goals:**

- Migraciones y `seed.py`: se unifican en C-09.
- Ficha `Cliente` y validación de documento único: dependen de C-05.
- Endpoints de administración de usuarios y roles: son de C-04.
- Revocación activa de sesiones o lista negra de tokens: el proyecto invalida por marca temporal, no por almacén de sesiones.
- Refresh tokens: la vigencia se renueva sólo con un login o un cambio de contraseña.

## Decisions

### 1. Ubicación del módulo y reparto de responsabilidades

Se crea `app/modules/auth/` con `router.py`, `service.py`, `repository.py` y `schemas.py`. Los modelos siguen en `app/modules/usuarios/models.py` porque describen tablas del dominio de usuarios; el módulo `auth` los consume pero no los redefine.

Repositorios: `UsuarioRepository`, `AsignacionRolRepository`, `IntentoAccesoRepository` y `EventoSeguridadRepository`, todos sobre `BaseRepository`. El servicio recibe un `UnitOfWork` ya construido por el router y lo abre con `async with`.

**Alternativa descartada:** un único `AuthRepository` que mezcle las cuatro tablas. Se descartó porque rompe la granularidad por entidad que ya usan los repositorios existentes y dificulta las pruebas.

### 2. Precisión de `iat` y comparación con `password_cambiada_en`

`create_access_token` pasa a usar `time.time()` sin `int()`: `iat` y `exp` viajan como números con fracción de segundo (NumericDate admite valores no enteros). `password_cambiada_en` se escribe desde el reloj de la aplicación con `datetime.now(UTC)`, no con `func.now()` del servidor, para que ambos valores provengan de la misma fuente.

La validación compara `float(payload["iat"]) < password_cambiada_en.timestamp()`. Si el valor es menor, el token es anterior al cambio y se rechaza con `401`. El cambio de contraseña fija `password_cambiada_en` **antes** de emitir el token nuevo, de modo que el `iat` de ese token es mayor o igual y la sesión del propio cambio sigue válida.

**Alternativa descartada:** truncar ambos valores a segundos. Se descartó porque es exactamente el defecto actual: un token emitido en el mismo segundo que el cambio quedaría ambiguo. También se descartó guardar un contador de versión de sesión en la tabla, porque agrega una columna que C-02 no definió y obliga a migración.

**Riesgo asumido:** si el reloj de la aplicación retrocede entre el cambio y la emisión, el token nuevo podría quedar inválido. Se mitiga emitiendo el token con el mismo instante ya calculado, no con una segunda lectura del reloj.

### 3. Cookie de sesión y montaje de rutas

La cookie se llama `access_token`, se marca `HttpOnly`, `SameSite=Lax`, `path="/"`, `Max-Age` igual a `JWT_EXPIRES_MINUTES * 60` y `Secure` según `COOKIE_SECURE` (falso en desarrollo, verdadero en despliegue con TLS). El token nunca se escribe en el cuerpo ni se lee de `Authorization`.

Todo el router `/auth` se monta en `router_abierto` con dependencias por ruta: `registro`, `login` y `logout` sin dependencia; `yo` y `cambiar-password` con `Depends(get_current_user)`. No se monta en `router_protegido` porque ese router aplica `require_password_change` a nivel de grupo y dejaría a un usuario con cambio pendiente sin acceso a `/auth/yo` ni a `/auth/cambiar-password`, contra RN-06.

**Alternativa descartada:** montar `/auth/yo` y `/auth/cambiar-password` en `router_protegido` y exceptuar la ruta de cambio. Se descartó porque obliga a una excepción dentro del router de grupo y vuelve implícita una regla que en la KB es explícita.

### 4. Dependencia de usuario autenticado

`get_current_user` deja de devolver el payload y devuelve un objeto `UsuarioAutenticado` con la cuenta cargada, los roles vigentes y los roles informativos del token. El flujo es:

1. Leer la cookie; sin cookie → `401`.
2. Decodificar y verificar firma y `exp`; inválido → `401`.
3. Cargar la cuenta por `sub`; inexistente o `activo` falso → `401`.
4. Comparar `iat` con `password_cambiada_en`; anterior → `401`.
5. Consultar `asignacion_rol` para los roles vigentes.

`require_password_change` pasa a leer `debe_cambiar_password` de la cuenta cargada y no del claim, para que el estado de la base mande. `get_active_roles` se reemplaza por la consulta a `asignacion_rol` con `revocada_en IS NULL` y `vence_en IS NULL OR vence_en > ahora`.

La consulta de roles se hace en cada petición autenticada: son dos consultas por petición (cuenta y roles). Se acepta el costo porque RN-04 exige que una revocación tenga efecto inmediato.

**Alternativa descartada:** cachear los roles por token. Se descartó porque una revocación quedaría sin efecto hasta que expire la caché.

### 5. Límite de intentos y reinicio por éxito

`IntentoAccesoRepository` expone `contar_fallos_recientes(email, ip, desde)` y `ultimo_exito(email, ip, desde)`. El servicio cuenta los fallos de la ventana de 60 segundos que sean posteriores al último inicio de sesión exitoso de ese correo y dirección; si el conteo es cinco o más, responde `429` con `Retry-After` calculado sobre el fallo más antiguo que todavía cuenta, sin ejecutar bcrypt.

Los fallos previos no se borran: siguen en la tabla y dejan de contar por la posición del último éxito. Las respuestas `429` no insertan fila, para que reintentar no renueve el bloqueo indefinidamente.

**Alternativa descartada:** borrar o marcar los intentos al iniciar sesión. Se descartó porque `intento_acceso` es un registro de auditoría y RN-08 pide conservar los fallos.

### 6. Registro de intentos en transacción independiente

El servicio de login recibe un `SessionFactory` y un `UnitOfWork` de la petición. Al terminar la verificación, abre una sesión propia con la fábrica y confirma el `IntentoAcceso` en su propio `UnitOfWork` dentro de un `try/finally`, de modo que el registro sobreviva a cualquier error posterior de la petición. La sesión de la petición no se reutiliza para esta escritura. Sólo se absorben los fallos operativos esperados de la base (`OperationalError`, `InterfaceError`, `TimeoutError` de SQLAlchemy) y `ConflictoDeIntegridad`, que se registran en el log; cualquier otro error es un defecto del programa y se propaga en lugar de silenciarse.

**Alternativa descartada:** registrar el intento en el UoW de la petición. Se descartó porque un error posterior revierte la transacción y el intento fallido nunca llegaría a contar para el límite.

### 7. Hash ficticio para correo inexistente

Se usa un hash bcrypt válido de un secreto aleatorio, calculado una sola vez por proceso y cacheado en un módulo, con un `asyncio.Lock` para evitar cálculos concurrentes. Se calcula con `BCRYPT_COST` de la configuración para que el costo de verificación sea el mismo que el de una cuenta real.

**Alternativa descartada:** una constante literal en el código. Se descartó porque su costo queda fijado y puede diferir del configurado, delatando por tiempo la existencia del correo. **Alternativa descartada:** calcularlo al importar el módulo, porque bloquea el arranque y cada import en pruebas paga el costo.

### 8. Validación de contraseñas

Todos los schemas de entrada usan Pydantic V2 con `extra="forbid"` y un `field_validator` que exige entre 1 y 72 bytes en UTF-8 (`len(valor.encode("utf-8"))`). El límite se aplica en registro, login y cambio de contraseña. Se valida con bytes y no con caracteres porque bcrypt trunca a 72 bytes y un texto con acentos puede excederlo con menos caracteres.

### 9. Alcance del registro

`POST /auth/registro` crea `Usuario` y `AsignacionRol` con rol `CLIENTE` en la misma unidad de trabajo. No crea ficha de `Cliente` porque el modelo no existe hasta C-05, y no valida documento porque ese campo tampoco existe. C-05 deberá extender el registro para crear la ficha en la misma transacción.

Esta limitación es deliberada y queda registrada para que no se interprete como un olvido: el flujo completo de la KB (`07_flujos_principales.md`, Flujo 1) se cierra en C-05.

### 10. Eventos de seguridad

El alta de cuenta y el cambio de contraseña escriben un `EventoSeguridad` con actor `SISTEMA` dentro del mismo `UnitOfWork` que la operación, para que el evento exista sólo si la operación se confirma. Las acciones se nombran con constantes (`REGISTRO_USUARIO`, `CAMBIO_PASSWORD`) para que C-04 y C-09 las reutilicen.

### 11. Configuración nueva

`Settings` incorpora `COOKIE_SECURE: bool = False`, `JWT_EXPIRES_MINUTES: int = 30`, `LOGIN_MAX_INTENTOS: int = 5` y `LOGIN_VENTANA_SEGUNDOS: int = 60`. Ninguno es secreto, por lo que pueden tener valor por defecto sin violar la regla de secretos. `extra="forbid"` sigue vigente.

### 12. Estrategia de pruebas

Las pruebas siguen el patrón existente: funciones síncronas que envuelven el flujo con `asyncio.run` y usan `SesionFalsa` para repositorios y servicios. Para los endpoints se usa `httpx.AsyncClient` con `ASGITransport` y se sobrescriben las dependencias de sesión y de usuario; `httpx` ya está instalado en el entorno virtual. No se agregan dependencias de prueba.

## Risks / Trade-offs

- **Dos consultas por petición autenticada** → Mitigación: son consultas por clave primaria e índice; se acepta el costo porque RN-04 exige vigencia inmediata. Si el volumen lo justificara, se evaluaría una caché con invalidación explícita, fuera del alcance de C-03.
- **Reloj de la aplicación como fuente de verdad de `iat` y `password_cambiada_en`** → Mitigación: un solo reloj para ambos valores y emisión del token con el instante ya calculado; en despliegue, sincronización NTP.
- **Registro de intentos en sesión separada** → Mitigación: la escritura se hace en `finally` y con su propio `UnitOfWork`; si falla por un error operativo de la base (`OperationalError`, `InterfaceError`, `TimeoutError`) o un conflicto de integridad, se registra en el log y la respuesta al cliente no cambia. Un error inesperado se propaga para no ocultar defectos.
- **`COOKIE_SECURE=False` por defecto** → Mitigación: el despliegue con TLS debe definirlo en `true`; se documenta en la configuración y en las variables de entorno.
- **El registro no crea la ficha de cliente** → Mitigación: queda explícito en el proposal y en este diseño; C-05 lo completa antes de exponer el flujo al cliente final.
- **Sin refresh token, la sesión dura lo que dure el token** → Mitigación: es el comportamiento pedido por la KB; el usuario vuelve a iniciar sesión al vencer.

## Migration Plan

No hay migraciones en este change. El esquema ya existe desde C-02 y las columnas necesarias (`password_cambiada_en`, `revocado_en`, `vence_en`, `intento_acceso`) están definidas. C-09 generará la revisión de Alembic que crea todas las tablas.

Despliegue: agregar `COOKIE_SECURE` al entorno de producción y reiniciar la aplicación. Rollback: revertir el código; no hay cambios de datos ni de esquema que deshacer.

## Open Questions

Ninguna que afecte el alcance, los specs o el desglose de tareas. Las decisiones sobre la ficha de cliente y la validación de documento quedan explícitamente diferidas a C-05.
