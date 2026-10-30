# Proposal

## Why

C-03 entregó autenticación, pero hoy nadie puede crear cuentas de personal ni administrar roles: el único alta existente es el auto-registro público, que crea clientes. Sin alta de personal, asignación de roles con vigencia y revocación, el taller no puede operar con recepción, mecánicos ni administradores, y RN-03 y RN-05 quedan sin la capa de servicio que las hace cumplir. Tampoco existe forma de auditar esos cambios, porque la consulta paginada de eventos de seguridad no está implementada.

## What Changes

- `POST /usuarios` (ADMIN): alta de personal con contraseña provisoria. La cuenta nace activa, con `debe_cambiar_password = true` y sin roles; la contraseña nunca se devuelve ni se emite cookie.
- `GET /usuarios/{id}/roles` (ADMIN): historial de asignaciones del usuario, con vencimiento y revocación, para poder auditar el estado desde la API.
- `POST /usuarios/{id}/roles` (ADMIN): asignación de un rol con vencimiento opcional. Responde `409` si ya hay una asignación abierta del mismo rol (RN-03) y reasigna un rol vencido cerrando la fila anterior.
- `DELETE /usuarios/{id}/roles/{rol}` (ADMIN): revoca sin borrar la fila, escribiendo `revocada_en`.
- RN-05 en el servicio: un administrador no puede revocarse su propio rol `ADMIN` y el sistema nunca queda sin administradores vigentes; ambos casos responden `409`.
- Catálogo de roles asignables desde la API: `ADMIN`, `RECEPCION` y `MECANICO`. `CLIENTE` queda reservado al auto-registro de C-03, que crea la ficha de cliente en C-05.
- `GET /eventos` (ADMIN): historial de seguridad paginado, ordenado por `cuando DESC, id DESC`, con envoltorio `{items, total, page, size, pages}`.
- Auditoría en `evento_seguridad` con actor `SISTEMA` o el administrador actuante, escrita en la misma unidad de trabajo que el cambio que la origina.
- `app/core/paginacion.py`: envoltorio de paginación y validación de parámetros, compartido por los listados del proyecto.
- Montaje de `/usuarios` y `/eventos` en `router_protegido`, de modo que hereden la sesión obligatoria y el bloqueo por cambio de contraseña pendiente.

**Fuera de alcance:** listado o detalle de usuarios, baja y reactivación de cuentas, reset de contraseña por administrador, migraciones de Alembic y `seed.py` (C-09), ficha de cliente (C-05), y trigger de inmutabilidad sobre `evento_seguridad`.

## Capabilities

### New Capabilities

Ninguna. El comportamiento nuevo pertenece a una capacidad existente.

### Modified Capabilities

- `gestion-de-usuarios`: se agregan requisitos de comportamiento para el alta de personal por administrador, la asignación y revocación de roles a través de la API, las invariantes de administración (autoprotección y al menos un administrador vigente), la auditoría de cambios de rol con actor humano y la consulta paginada de eventos de seguridad.

## Impact

**Código**

- Nuevo `app/modules/usuarios/schemas.py`, `repository.py`, `service.py` y `router.py`.
- Nuevo `app/core/paginacion.py`, reutilizable por C-06 y C-07.
- `app/main.py`: montaje de `/usuarios` y `/eventos` en `router_protegido`.
- `app/core/repository.py` o el repositorio de eventos: método de conteo para paginar.
- Se reutilizan `UsuarioRepository`, `AsignacionRolRepository` y `EventoSeguridadRepository` de `app/modules/auth/repository.py`; no se duplican clases.

**API**

Cuatro rutas nuevas, todas bajo `router_protegido` con rol `ADMIN`: `POST /usuarios`, `GET /usuarios/{id}/roles`, `POST /usuarios/{id}/roles`, `DELETE /usuarios/{id}/roles/{rol}`, más `GET /eventos`. Cada una responde `401` sin sesión, `403` con cambio de contraseña pendiente o sin rol `ADMIN`, y `404` cuando el usuario no existe.

**Dependencias**

Sin dependencias externas nuevas: se reutilizan FastAPI, SQLModel/SQLAlchemy async, bcrypt y PyJWT ya instalados.

**Datos**

Sin cambios de esquema. Se usan `usuario`, `asignacion_rol` y `evento_seguridad` definidas en C-02, incluido el índice único parcial de asignación abierta. `migrations/versions/` sigue vacío hasta C-09.

**Riesgos de coordinación**

`app/core/paginacion.py` también lo necesitan C-06 y C-07, que pueden ejecutarse en paralelo. Se crea en este change y los demás lo reutilizan; si otro change lo crea primero, este debe adaptarse en lugar de duplicarlo.
