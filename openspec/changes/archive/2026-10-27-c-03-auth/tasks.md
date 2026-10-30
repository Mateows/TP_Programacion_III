# Tasks

## 1. Configuración y utilidades de seguridad

- [x] 1.1 Agregar a `Settings` los campos `COOKIE_SECURE`, `JWT_EXPIRES_MINUTES`, `LOGIN_MAX_INTENTOS` y `LOGIN_VENTANA_SEGUNDOS`; verificar que `Settings()` carga con el `.env` actual y que `extra="forbid"` sigue rechazando claves desconocidas.
- [x] 1.2 Escribir primero la prueba de `create_access_token` que exige `iat` con fracción de segundo y verificarla en RED; cambiar la emisión de `int(time.time())` a `time.time()` y confirmar GREEN con la prueba y con `decode_access_token`.
- [x] 1.3 Escribir primero la prueba del hash ficticio (mismo valor entre llamadas, verificación siempre falsa); implementar el hash cacheado por proceso con `asyncio.Lock` y costo `BCRYPT_COST`, y confirmar GREEN.
- [x] 1.4 Escribir primero la prueba de comparación de `iat` contra `password_cambiada_en` (anterior rechazado, igual aceptado, posterior aceptado); implementar el helper de comparación sin truncar y confirmar GREEN.

## 2. Schemas del módulo auth

- [x] 2.1 Escribir primero las pruebas del validador de contraseña (72 bytes aceptados, 73 rechazados, vacía rechazada, acentos medidos en bytes); implementar el `field_validator` de Pydantic V2 y confirmar GREEN.
- [x] 2.2 Definir `RegistroRequest`, `LoginRequest`, `CambioPasswordRequest`, `SesionResponse` y `MensajeSesionResponse` con `extra="forbid"`; verificar con pruebas que un campo desconocido produce error de validación y que ningún schema de respuesta declara un campo de token.

## 3. Repositorios del módulo auth

- [x] 3.1 Escribir primero las pruebas de `UsuarioRepository.buscar_por_email` y `AsignacionRolRepository.listar_vigentes` (filtros de revocación y vencimiento, sin `commit`); implementarlos sobre `BaseRepository` y confirmar GREEN con `SesionFalsa`.
- [x] 3.2 Escribir primero las pruebas de `IntentoAccesoRepository` (`contar_fallos_recientes`, `ultimo_exito`, `registrar`) y confirmar RED; implementar las consultas con la ventana temporal y el índice existente, y confirmar GREEN.
- [x] 3.3 Escribir primero la prueba de `EventoSeguridadRepository.registrar` (actor y acción persistidos, sin `commit`); implementarlo y confirmar GREEN.

## 4. Servicio de registro

- [x] 4.1 Escribir primero la prueba del registro exitoso (usuario con hash, asignación `CLIENTE`, evento `SISTEMA`, una sola confirmación del UoW) y confirmarla en RED; implementar `registrar_cuenta` en el servicio y confirmar GREEN.
- [x] 4.2 Escribir primero la prueba de correo duplicado (se propaga el conflicto de integridad y el UoW revierte sin dejar filas); implementar la traducción a error de dominio y confirmar GREEN.
- [x] 4.3 Escribir primero la prueba de fallo al crear la asignación (ninguna fila queda confirmada); ajustar el servicio para que usuario y rol compartan la misma unidad de trabajo y confirmar GREEN.

## 5. Servicio de inicio de sesión

- [x] 5.1 Escribir primero la prueba del límite de intentos (cinco fallos en 60 segundos → `429` con `retry_after`, sin llamar a `verify_password`); implementar el conteo y confirmar GREEN.
- [x] 5.2 Escribir primero la prueba de reinicio del conteo tras un inicio de sesión exitoso y la de fallos fuera de la ventana; implementar la consulta contra el último éxito y confirmar GREEN.
- [x] 5.3 Escribir primero las pruebas de credenciales inválidas (correo inexistente usa hash ficticio, contraseña incorrecta y cuenta inactiva devuelven el mismo error); implementar la verificación uniforme y confirmar GREEN.
- [x] 5.4 Escribir primero la prueba del inicio de sesión exitoso (token con `sub`, `iat`, `exp`, roles vigentes y `debe_cambiar_password`); implementar la emisión y confirmar GREEN.
- [x] 5.5 Escribir primero la prueba de que el intento se confirma en una sesión propia aunque la petición falle después; implementar el registro con `SessionFactory` y `UnitOfWork` independientes en `finally` y confirmar GREEN.
- [x] 5.6 Escribir primero la prueba de que una respuesta `429` no agrega un intento fallido; ajustar el orden del servicio y confirmar GREEN.

## 6. Servicio de sesión y cambio de contraseña

- [x] 6.1 Escribir primero la prueba de consulta de la sesión propia (datos de la cuenta, roles vigentes y roles informativos del token); implementar el servicio de consulta y confirmar GREEN.
- [x] 6.2 Escribir primero la prueba del cambio de contraseña exitoso (hash nuevo, `password_cambiada_en` con reloj de la aplicación, `debe_cambiar_password` en falso, evento `SISTEMA`, token nuevo válido); implementar el servicio y confirmar GREEN.
- [x] 6.3 Escribir primero las pruebas de contraseña actual incorrecta (`401` sin cambios) y de nueva contraseña fuera del límite (`422` sin cambios); ajustar el servicio y confirmar GREEN.

## 7. Dependencias de autenticación

- [x] 7.1 Escribir primero las pruebas de `get_current_user` (sin cookie, token inválido, usuario inexistente, usuario inactivo, `iat` anterior al cambio) y confirmarlas en RED; reemplazar la lectura del payload por la carga desde la base y confirmar GREEN.
- [x] 7.2 Escribir primero la prueba de aceptación del token emitido por el propio cambio de contraseña; verificar que el helper de comparación lo acepta y confirmar GREEN.
- [x] 7.3 Escribir primero las pruebas de roles vigentes (rol revocado, rol vencido, rol otorgado durante la sesión, rol del token no vigente en base); reemplazar `get_active_roles` por la consulta a `asignacion_rol` y confirmar GREEN.
- [x] 7.4 Escribir primero la prueba de `require_password_change` leyendo el estado de la base y no el claim; ajustar la dependencia y confirmar GREEN.
- [x] 7.5 Escribir primero las pruebas de `requiere_rol` con roles vigentes (concede con rol vigente, deniega con rol revocado, deniega sin rol); ajustar la dependencia y confirmar GREEN.

## 8. Router y cableado de la aplicación

- [x] 8.1 Escribir primero las pruebas de las utilidades de cookie (`HttpOnly`, `SameSite=Lax`, `Max-Age` igual a la vigencia, borrado con `Max-Age=0`); implementarlas y confirmar GREEN.
- [x] 8.2 Escribir primero las pruebas de `POST /auth/registro` (`201` con cookie, `409` con correo repetido, `422` con cuerpo inválido) y confirmarlas en RED; implementar la ruta y confirmar GREEN.
- [x] 8.3 Escribir primero las pruebas de `POST /auth/login` (`200` con cookie y cuerpo sin token, `401` genérico, `429` con `Retry-After`) y confirmarlas en RED; implementar la ruta y confirmar GREEN.
- [x] 8.4 Escribir primero las pruebas de `POST /auth/logout` (`200` con y sin sesión, cookie borrada); implementar la ruta y confirmar GREEN.
- [x] 8.5 Escribir primero las pruebas de `GET /auth/yo` (`200` con datos y roles, `401` sin sesión) y confirmarlas en RED; implementar la ruta y confirmar GREEN.
- [x] 8.6 Escribir primero las pruebas de `POST /auth/cambiar-password` (`200` con cookie nueva, `401` con contraseña actual incorrecta, `422` con nueva inválida) y confirmarlas en RED; implementar la ruta y confirmar GREEN.
- [x] 8.7 Montar el router `/auth` en `router_abierto` con dependencias por ruta; verificar con una prueba que `GET /auth/yo` y `POST /auth/cambiar-password` responden a una cuenta con `debe_cambiar_password` en verdadero sin devolver `403`.

## 9. Verificación final y documentación

- [x] 9.1 Ejecutar `.venv\Scripts\python.exe -m pytest test/unit -q` y verificar que toda la suite pasa, incluidos los 51 tests previos de C-02.
- [x] 9.2 Ejecutar `.venv\Scripts\python.exe -m pytest test/integration -q` (creando el directorio si no existe) y verificar los flujos de router con `httpx`.
- [x] 9.3 Actualizar `test/unit/README.md` con el runner y el nuevo total esperado de pruebas; verificar que el comando documentado se ejecuta tal cual.
- [x] 9.4 Ejecutar `openspec validate c-03-auth --strict` y verificar que el change es válido con todos sus artefactos.
- [x] 9.5 Actualizar `CHANGES.md` marcando C-03 como implementado con su verificación; verificar que el estado y el conteo de tareas coinciden con `openspec status --change "c-03-auth"`.

## Workflow follow-up

- Revisar los artefactos y la implementación con el usuario antes de archivar.
- Sincronizar los delta specs a los specs principales y archivar el change cuando el usuario lo solicite.
- No ejecutar `git commit` ni `git push`: el control de versiones es manual del usuario.
