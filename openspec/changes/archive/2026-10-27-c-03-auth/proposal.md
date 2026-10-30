# Proposal

## Why

C-02 dejó persistidos los usuarios, las asignaciones de rol, los intentos de acceso y los eventos de seguridad, pero el sistema todavía no permite autenticarse: `app/core/dependencies.py` solo decodifica el JWT y lee los roles del propio token, y `app/core/security.py` trunca `iat` a segundos. Sin autenticación, ninguna ruta protegida puede saber quién llama ni qué puede hacer, y las ramas C-04 a C-08 del roadmap quedan bloqueadas.

## What Changes

- Se agrega la capacidad `autenticacion` con cinco rutas bajo `/auth`:
  - `POST /auth/registro` crea la cuenta y su rol `CLIENTE` en una sola unidad de trabajo, responde `201` y entrega la cookie de sesión.
  - `POST /auth/login` aplica el límite de intentos antes de verificar la contraseña, usa un hash ficticio cuando el correo no existe y responde siempre el mismo cuerpo ante credenciales inválidas.
  - `POST /auth/logout` elimina la cookie de sesión.
  - `GET /auth/yo` devuelve la cuenta autenticada con sus roles vigentes y los roles informativos del token.
  - `POST /auth/cambiar-password` verifica la contraseña actual, actualiza el hash y la marca de cambio, y emite un token nuevo que sigue siendo válido.
- El token viaja únicamente en la cookie `access_token` con `HttpOnly`, `SameSite=Lax` y `Max-Age`; nunca en el cuerpo ni en `Authorization`.
- `create_access_token` deja de truncar `iat`: emite la marca con precisión de microsegundos para que la comparación con `password_cambiada_en` no invalide por error el token emitido por el propio cambio de contraseña.
- `get_current_user` pasa a cargar la cuenta desde la base, rechaza cuentas inactivas y descarta tokens emitidos antes del último cambio de contraseña.
- `get_active_roles` deja de leer el claim `roles` y consulta `asignacion_rol` en cada petición; los roles del token quedan como información.
- Se incorpora el límite de 1 a 72 bytes UTF-8 en toda contraseña recibida, porque bcrypt ignora en silencio lo que excede ese tamaño.
- Se agrega configuración de cookie y duración de sesión (`COOKIE_SECURE`, minutos de vigencia del token).
- **Fuera de alcance:** migraciones y `seed.py` (se unifican en C-09), la ficha `Cliente` y la validación de documento único (C-05), y los endpoints de dominio de C-04 a C-08. El registro de C-03 crea la cuenta y el rol `CLIENTE`, pero no la ficha de cliente porque ese modelo no existe todavía.

## Capabilities

### New Capabilities
- `autenticacion`: registro, inicio y cierre de sesión, consulta de la sesión propia, cambio de contraseña, emisión y validación de tokens, cookie de sesión y límite de intentos de acceso.

### Modified Capabilities
- `gestion-de-usuarios`: se agrega el requisito de que los permisos se resuelvan con los roles vigentes en la base en cada petición, quedando los roles del token como información no autoritativa.

## Impact

- **Código nuevo:** `app/modules/auth/` con router, service, repositorios y schemas.
- **Código modificado:** `app/core/security.py` (precisión de `iat`, hash ficticio, contraseña máxima), `app/core/dependencies.py` (usuario desde base, roles vigentes, invalidación por `iat`), `app/core/config.py` (`COOKIE_SECURE`, vigencia del token), `app/main.py` (montaje de `/auth/*`).
- **Base de datos:** sin cambios de esquema; se usan las tablas de C-02 (`usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`).
- **Dependencias:** `bcrypt` y `PyJWT` ya están en `requirements.txt`; no se agregan librerías.
- **Pruebas:** nuevos tests unitarios de seguridad, servicio y dependencias, y tests de router con `httpx`.
