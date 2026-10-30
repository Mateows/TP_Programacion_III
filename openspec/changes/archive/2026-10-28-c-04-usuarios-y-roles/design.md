# Design

## Context

Ver `proposal.md` — Why. Estado actual que condiciona el enfoque:

- C-03 dejó `app/core/dependencies.py` con `UsuarioAutenticado`, `get_current_user`, `require_password_change` y `requiere_rol`, ya probados. `main.py` monta `router_abierto` (`/auth`) y `router_protegido` (con `require_password_change` a nivel de grupo), y deja comentado el punto de montaje de `/usuarios/*`.
- Los repositorios de `Usuario`, `AsignacionRol`, `IntentoAcceso` y `EventoSeguridad` viven en `app/modules/auth/repository.py`; `app/core/dependencies.py` los importa desde allí. `BaseRepository` no tiene `update()` ni `contar()`.
- `app/modules/usuarios/` solo contiene `models.py`. `app/core/paginacion.py` no existe.
- `evento_seguridad` no tiene índice por `cuando` ni trigger de inmutabilidad; `migrations/versions/` está vacío hasta C-09.
- Los tests no usan base de datos: `SesionFalsa` registra sentencias y se compilan contra el dialecto de PostgreSQL.

## Goals / Non-Goals

**Goals:**

- Cuatro rutas administrativas con contratos HTTP explícitos y errores de dominio traducidos en el router.
- Invariantes de RN-03 y RN-05 verificadas en el servicio, no en la base ni en el router.
- Auditoría escrita en la misma unidad de trabajo que la operación auditada.
- Un contrato de paginación reutilizable por C-06 y C-07.
- Cobertura TDD de schemas, repositorios, servicios y router.

**Non-Goals:**

- Reorganizar los repositorios de C-03 a `app/modules/usuarios/repository.py`; el movimiento queda diferido para no romper imports ni tests de un change archivado.
- Agregar relaciones ORM (`Relationship`) a los modelos de C-02.
- Migraciones, índices nuevos, triggers de inmutabilidad y `seed.py`: C-09.
- Listado y detalle de usuarios, baja/reactivación, reset de contraseña por administrador.
- Bloqueo pesimista o `SELECT ... FOR UPDATE` para las comprobaciones de RN-05.

## Decisions

### 1. Superficie HTTP y montaje

| Método | Ruta | Éxito | Rol |
|---|---|---|---|
| `POST` | `/usuarios` | `201` | `ADMIN` |
| `GET` | `/usuarios/{id}/roles` | `200` | `ADMIN` |
| `POST` | `/usuarios/{id}/roles` | `201` | `ADMIN` |
| `DELETE` | `/usuarios/{id}/roles/{rol}` | `200` | `ADMIN` |
| `GET` | `/eventos` | `200` | `ADMIN` |

`app/modules/usuarios/router.py` expone dos routers (`router_usuarios` y `router_eventos`) y `main.py` los monta en `router_protegido` con prefijos `/usuarios` y `/eventos`. El rol se exige por ruta con `dependencias=[Depends(requiere_rol("ADMIN"))]`, no a nivel de router, para que un futuro endpoint de "lo propio" pueda convivir en el mismo módulo.

El orden de rechazo queda: `401` sin sesión → `403` por cambio de contraseña pendiente (grupo protegido) → `403` por falta de rol `ADMIN`.

Alternativa descartada: `DELETE /usuarios/{id}/roles` con el rol en el body. El Flujo 5 de la KB y la semántica de DELETE favorecen el rol en el path; además evita el cuerpo en un método que muchos clientes no lo envían.

### 2. Repositorios: extender los de C-03, no duplicarlos

Las consultas nuevas se agregan a las clases existentes de `app/modules/auth/repository.py`:

- `UsuarioRepository`: sin cambios (usa `get` de `BaseRepository` y `buscar_por_email`).
- `AsignacionRolRepository`: `buscar_abierta(usuario_id, rol)`, `listar_historial(usuario_id)` (orden `desde DESC, id DESC`), `contar_admin_vigentes(ahora, excluir_asignacion_id)`.
- `EventoSeguridadRepository`: `listar_paginado(limit, offset)` (orden `cuando DESC, id DESC`) y conteo.

`app/modules/usuarios/service.py` los importa desde `auth.repository`, igual que ya hace `app/core/dependencies.py`. No se crean clases paralelas sobre los mismos modelos.

Alternativas descartadas: mover los repositorios a `usuarios/repository.py` (rompe imports y 175 tests de C-03 por un beneficio solo organizativo) y crear clases nuevas en `usuarios/repository.py` (duplica el acceso al mismo modelo).

`contar_admin_vigentes` cuenta asignaciones `ADMIN` con `revocada_en IS NULL`, `(vence_en IS NULL OR vence_en > :ahora)` y `usuario.activo = true`, con un `JOIN` a `usuario` y excluyendo la asignación que se está revocando. Una cuenta inactiva no puede autenticarse, así que su rol no evita el bloqueo del sistema.

### 3. Contrato de paginación compartido

`app/core/paginacion.py` define:

- `ParametrosPagina(page: int = 1, size: int = 20)` con validación `page >= 1` y `1 <= size <= 100`.
- `Pagina[T]` con `items`, `total`, `page`, `size` y `pages = ceil(total / size)`.
- `construir_pagina(items, total, parametros)`.

Los routers reciben `page` y `size` como `Query(..., ge=..., le=...)`, de modo que Pydantic devuelve `422` sin código extra. Una página posterior a la última se detecta en el servicio y se traduce a `422` con un error de dominio (`PaginaFueraDeRango`), coherente con el contrato que US-014 fija para repuestos.

`contar()` se agrega a `BaseRepository` como método genérico (`select(func.count()).select_from(...)` con los mismos filtros que `list`). Es aditivo y lo necesitan también C-06 y C-07.

### 4. Alta de personal

`POST /usuarios` recibe `email`, `nombre` y `password` (`extra="forbid"`). El servicio:

1. Calcula `hash_password` **antes** de abrir la unidad de trabajo, para no retener la conexión durante bcrypt.
2. Abre `async with uow`.
3. Crea `Usuario` con `activo=True`, `debe_cambiar_password=True`, `password_cambiada_en=None` y el hash.
4. Captura `ConflictoDeIntegridad` **solo alrededor de ese `add`** y la traduce a `CorreoYaRegistrado`; así una violación en otra escritura no se reporta como correo duplicado.
5. Registra el evento `ALTA_USUARIO_PERSONAL` en la misma unidad de trabajo.

No se emite cookie ni token, y la respuesta no incluye el hash. El usuario queda sin roles: puede autenticarse, pero recibirá `403` en todo el grupo protegido hasta que se le asigne uno.

### 5. Roles asignables

`ROLES_ASIGNABLES = ("ADMIN", "RECEPCION", "MECANICO")` en `app/modules/usuarios/schemas.py`, validado con `Literal` en el contrato de entrada. `ROLES_VALIDOS` de `models.py` conserva los cuatro roles para el `CHECK` de la base, porque `CLIENTE` se sigue creando desde el auto-registro.

`CLIENTE` responde `422` en la administración: asignarlo produciría una cuenta con rol de cliente sin ficha `cliente`, inconsistente con RN-02 hasta que C-05 exista.

### 6. Asignación y reasignación de rol

`POST /usuarios/{id}/roles` recibe `rol` y `vence_en: datetime | None`. Un `field_validator` exige que `vence_en` tenga `tzinfo` y sea estrictamente posterior al instante de la operación; cualquier otro caso es `422` (`VencimientoInvalido`).

Lógica del servicio, dentro de una sola unidad de trabajo:

1. Verifica que el usuario exista → `404` (`UsuarioNoEncontrado`).
2. Busca la asignación abierta (`revocada_en IS NULL`) de `(usuario_id, rol)`.
3. Si existe y está vigente (`vence_en` nulo o futuro) → `409` (`RolYaAsignado`).
4. Si existe y está vencida → escribe `revocada_en = ahora` y hace `flush()`, **antes** de insertar la nueva. Es el punto delicado: el índice único parcial solo excluye filas con `revocada_en` no nulo, no las vencidas; sin este paso el `INSERT` choca.
5. Crea la asignación con `desde = ahora` y `otorgada_por = actor.id`.
6. Registra `ASIGNACION_ROL` en la misma unidad de trabajo.

`desde` se fija en Python, no se delega al `server_default`, para poder devolverlo en la respuesta sin un `refresh()` ni un `SELECT` implícito que dispare `MissingGreenlet`. `otorgada_por` es nullable en el modelo, pero la API siempre lo escribe.

Alternativa descartada: aceptar `desde` en el cuerpo. Permitiría falsear la auditoría de cuándo se otorgó el rol.

### 7. Revocación y RN-05

`DELETE /usuarios/{id}/roles/{rol}` revoca la asignación abierta:

1. Usuario inexistente → `404`.
2. Sin asignación abierta de ese rol → `404` (`AsignacionNoEncontrada`). La operación no es idempotente en el código de estado: la segunda revocación también da `404`, porque la fila ya no está abierta.
3. Si `rol == "ADMIN"` y `usuario_id == actor.id` → `409` (`RevocacionPropiaNoPermitida`), sin importar cuántos administradores haya.
4. Si `rol == "ADMIN"` y `contar_admin_vigentes(ahora, excluir=asignacion.id) == 0` → `409` (`UltimoAdministrador`).
5. Escribe `revocada_en = ahora`, hace `flush()` y registra `REVOCACION_ROL` en la misma unidad de trabajo.
6. Responde `200` con la asignación revocada.

El orden importa: la autoprotección se evalúa antes que la invariante global, para que el mensaje sea el correcto cuando un administrador intenta revocarse siendo el último.

**Carrera aceptada:** dos administradores podrían revocarse mutuamente en paralelo y dejar cero. Se documenta como limitación: la comprobación es *check-then-act* y resolverla requiere bloqueo de filas, fuera del alcance del TP. La base no puede expresar la invariante con un `CHECK`.

### 8. Auditoría

Formato del actor: `USUARIO:{id}`. El email no sirve como actor porque `evento_seguridad.actor` es `VARCHAR(100)` y `usuario.email` es `VARCHAR(255)`: un correo largo rompería el `INSERT` y, con él, la operación auditada. `SISTEMA` se conserva para los eventos sin persona.

Acciones: `ALTA_USUARIO_PERSONAL`, `ASIGNACION_ROL`, `REVOCACION_ROL`, como constantes del módulo, igual que C-03 hizo con `REGISTRO_USUARIO` y `CAMBIO_PASSWORD`.

El evento se escribe **dentro** de la unidad de trabajo, no después del `commit` como sugiere el orden del Flujo 5. Si se escribiera después, un fallo del evento dejaría un cambio de permisos sin auditoría, que es exactamente lo que la auditoría debe impedir. Como contrapartida, una operación rechazada no deja evento, y eso es lo que la spec exige.

### 9. Consulta de roles y de eventos

`GET /usuarios/{id}/roles` devuelve el historial completo (abiertas, vencidas y revocadas) ordenado por `desde DESC, id DESC`. Devolver solo las vigentes haría inútil el endpoint para auditar; el estado se lee en `vence_en` y `revocada_en`. No se pagina: la cantidad de asignaciones por usuario está acotada por el catálogo y su historial.

`GET /eventos` pagina con el contrato de la decisión 3 y ordena por `cuando DESC, id DESC`. El desempate por `id` es obligatorio: sin él, dos eventos con la misma marca temporal podrían repetirse u omitirse entre páginas.

### 10. Contratos de respuesta

| Schema | Campos |
|---|---|
| `UsuarioCreadoResponse` | `id`, `email`, `nombre`, `activo`, `debe_cambiar_password` |
| `AsignacionRolResponse` | `id`, `rol`, `desde`, `vence_en`, `revocada_en`, `otorgada_por` |
| `EventoSeguridadResponse` | `id`, `cuando`, `actor`, `accion` |
| `PaginaResponse[T]` | `items`, `total`, `page`, `size`, `pages` |

Todos con Pydantic V2 y `extra="forbid"`. Ninguno expone `password_hash` ni datos de otras cuentas.

### 11. Validación de contraseña reutilizada

`app/modules/usuarios/schemas.py` importa `PasswordValidadaMixin` y `validar_password` de `app.modules.auth.schemas` en lugar de repetir la regla de 1 a 72 bytes UTF-8. Duplicarla garantizaría que las dos reglas diverjan. Mover la validación a `app/core` sería más limpio, pero toca un módulo archivado y queda para un refactor posterior.

### 12. Errores y traducción a HTTP

Errores de dominio en `app/modules/usuarios/errors.py`, traducidos en el router:

| Error | HTTP |
|---|---|
| `UsuarioNoEncontrado`, `AsignacionNoEncontrada` | `404` |
| `CorreoYaRegistrado`, `RolYaAsignado`, `RevocacionPropiaNoPermitida`, `UltimoAdministrador`, `ConflictoDeIntegridad` | `409` |
| `RolNoAsignable`, `VencimientoInvalido`, `PaginaFueraDeRango`, `PasswordInvalida` | `422` |

Ningún mensaje incluye nombres de tablas, columnas o restricciones (RN-18). No se agregan manejadores globales: se mantiene el patrón de `auth/router.py`.

## Risks / Trade-offs

- **Índice único parcial vs. asignación vencida** → Mitigación: el servicio revoca la fila vencida con `flush()` antes de insertar la nueva; se cubre con un test que verifica el orden de las sentencias.
- **Carrera en RN-05** → Mitigación: se documenta como limitación aceptada; la comprobación es *check-then-act* y el bloqueo de filas queda fuera de alcance.
- **`server_default` en `desde` y `cuando`** → Mitigación: `desde` se fija en Python; `cuando` solo se lee en consultas, nunca se devuelve tras un `add`.
- **`contar()` en `BaseRepository` toca código de C-02** → Mitigación: método aditivo, con tests propios; no modifica los métodos existentes.
- **`app/core/paginacion.py` compartido con C-06 y C-07** → Mitigación: se crea aquí con su contrato y tests; los otros changes lo reutilizan en lugar de duplicarlo.
- **Actor `USUARIO:{id}` no es legible por humanos en el historial** → Mitigación: el id es estable y no desborda `VARCHAR(100)`; la resolución a email queda para un change de reportes.
- **Repositorios en `auth/` usados por `usuarios/`** → Mitigación: se documenta como deuda de organización; moverlos exige actualizar `core/dependencies.py` y los tests de C-03.
- **`evento_seguridad` sin índice por `cuando`** → Mitigación: la consulta paginada funciona igual; el índice se agrega en C-09 junto con las migraciones.

## Migration Plan

No hay migraciones en este change. El esquema de `usuario`, `asignacion_rol` y `evento_seguridad` ya existe en los modelos de C-02 y C-09 generará la revisión inicial. Despliegue: montar los routers y desplegar; no hay datos que transformar. Rollback: retirar el montaje de `/usuarios` y `/eventos`; las tablas no cambian.

## Open Questions

- ¿Conviene un índice por `cuando` en `evento_seguridad` y un trigger de inmutabilidad? Se difiere a C-09, que es donde viven las migraciones; no cambia las specs ni el enfoque.
- ¿`GET /eventos` necesita filtros por actor, acción o rango de fechas? Se difiere hasta que exista un caso de uso; agregarlos no cambia el contrato de paginación.
