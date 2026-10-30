# Design

## Context

Ver `proposal.md — Why`. Al momento de este change existe el módulo `clientes` vacío (sólo `__init__.py`), los modelos de `usuario`, `asignacion_rol`, `intento_acceso` y `evento_seguridad` en `app/modules/usuarios/models.py`, y la infraestructura de `BaseRepository`, `SoftDeleteRepository`, `UnitOfWork`, `requiere_rol` y `CurrentUser`. El auto-registro de C-03 crea cuenta y rol `CLIENTE` pero no ficha de cliente, y su contrato (`RegistroRequest`) no incluye documento.

Restricciones que condicionan el diseño:

- La KB nombra las tablas en singular (`cliente`, `vehiculo`) y el repositorio usa `__tablename__` en singular (`usuario`, `estado_orden`).
- `cliente` no tiene `borrado_en`; `vehiculo` sí. Sólo el vehículo usa `SoftDeleteRepository`.
- La patente es única **sólo entre vigentes**, igual que el índice parcial ya usado para `asignacion_rol`.
- La tabla `orden_trabajo` pertenece a C-07 y todavía no existe.
- Prohibido `create_all`: las migraciones se generan en C-09.

## Goals / Non-Goals

**Goals:**

- Modelar `cliente` y `vehiculo` con las restricciones de integridad de la KB expresadas en la base (unicidad, índice parcial, CHECK, índices de FK).
- Exponer las cinco rutas del scope con la traducción de errores y la autorización ya establecidas en el proyecto.
- Cerrar RN-02 extendiendo el auto-registro en una sola unidad de trabajo.
- Dejar RN-16 especificada y verificable sin acoplarse a una tabla que aún no existe.

**Non-Goals:**

- Generar migraciones, `seed.py`, o tocar `alembic` (C-09).
- Definir `orden_trabajo`, sus estados por fila o la consulta real de órdenes abiertas (C-07).
- Edición o baja de clientes, búsqueda/paginación de clientes, y `/mis-ordenes` (C-08).
- Mover `PaginaResponse` a `core/` (no hay paginación en este change).

## Decisions

### 1. Dos tablas en `app/modules/clientes/models.py`

`Cliente`: `id` PK, `usuario_id` FK a `usuario.id` **nullable, unique e indexada**, `nombre`, `documento` (unique), `telefono` nullable. `Vehiculo`: `id` PK, `cliente_id` FK a `cliente.id` **not null e indexada**, `patente`, `marca`, `modelo`, `anio`, `borrado_en` nullable.

- **Por qué**: reproduce la KB (`04_modelo_de_datos.md:51-58`) y el estilo de `usuarios/models.py`.
- **Alternativa descartada**: tabla `clientes` en plural y `borrado_en` en `cliente`. Se descarta por la KB y porque ningún requirement pide dar de baja clientes.
- `ON DELETE` se deja en el valor por defecto (`NO ACTION`): la KB no lo define y no hay endpoint que borre clientes ni usuarios.

### 2. Índice único parcial para la patente

`Index("ix_vehiculo_patente_vigente", "patente", unique=True, postgresql_where=text("borrado_en IS NULL"))`, calcado de `ix_asignacion_rol_usuario_rol_abierta`.

- **Por qué**: PostgreSQL no permite un `UNIQUE` común porque impediría reutilizar la patente de un vehículo dado de baja (US-012 CA-3).
- La patente se **normaliza en el contrato** (`strip` + `upper`) antes de persistir, para que el índice parcial cubra las variantes de capitalización y espacios que el spec declara equivalentes.

### 3. `ClienteRepository` y `VehiculoRepository`

`ClienteRepository(BaseRepository[Cliente])` con `buscar_por_usuario(usuario_id)` y `buscar_por_documento(documento)`. `VehiculoRepository(SoftDeleteRepository[Vehiculo])` con `listar_vigentes_por_cliente(cliente_id)` y `buscar_vigente_por_patente(patente)`.

- **Por qué**: `SoftDeleteRepository.get`, `list` y `soft_delete` ya implementan el filtrado de baja y la baja idempotente (sólo setea `borrado_en` si es `None`). Reimplementarlo duplicaría la regla.
- **Cuidado conocido**: `SoftDeleteRepository` **no** sobrescribe `contar`; si en el futuro se pagina vehículos vigentes hay que pasar `borrado_en.is_(None)` explícitamente. Este change no pagina.
- La consulta de cliente con vehículos hace **dos consultas** (cliente, luego vehículos vigentes ordenados por patente) en lugar de cargar la relación. Evita el N+1 y evita un `primaryjoin` filtrado por baja, que sería más frágil que una consulta explícita.

### 4. Verificador de órdenes abiertas inyectable

La baja de vehículo recibe un `VerificadorOrdenesAbiertas` (protocolo con `async def contar_abiertas(vehiculo_id) -> int`). Su implementación por defecto, en `app/modules/clientes/verificacion.py`, devuelve `0` y documenta que C-07 la reemplaza por la consulta real contra `orden_trabajo` y `estado_orden.es_final`.

- **Por qué**: mantiene la regla RN-16 especificada y testeable ahora, sin crear un modelo de C-07 ni una tabla inexistente.
- El servicio depende del protocolo, no de un repositorio concreto, así que el cambio de C-07 no altera el contrato HTTP (`204`/`409`).
- **Alternativa descartada**: definir `OrdenTrabajo` en este change — adelantaría decisiones de C-07 (ítems, estado, historial) y rompería la separación del roadmap.

### 5. Extensión del auto-registro (RN-02)

`RegistroRequest` suma `documento: str` (obligatorio) y `telefono: str | None`. `registrar_cuenta` crea, dentro del mismo `async with uow`, `Usuario` → `AsignacionRol("CLIENTE")` → `Cliente(usuario_id=<id>, nombre=..., documento=..., telefono=...)`, reutilizando el patrón de traducción de `ConflictoDeIntegridad` que ya usa el alta de usuario.

- **Por qué**: sin ficha, ninguna cuenta auto-registrada puede tener vehículos y `/mis-vehiculos` respondería `403` siempre.
- El conflicto de documento se distingue del de correo porque ocurren en `add` distintos: el correo sólo puede fallar en el `add` del usuario y el documento sólo en el `add` de la ficha. Un conflicto en cualquier otro punto se propaga tal cual (mismo criterio que `auth/service.py:132-144`).
- **Acoplamiento asumido**: `auth/service.py` y `auth/router.py` importan `clientes.repository` y `clientes.errors`. Es la dirección ya usada por `auth` → `usuarios`; no se crea ciclo porque `clientes` no importa `auth`.
- **Alternativa descartada**: mover los errores compartidos a un módulo común. Es un refactor sin cambio de comportamiento observable y queda fuera de este change.

### 6. Capa HTTP

Dos routers en `app/modules/clientes/router.py`: `router_clientes` (`""`, `"/{id}"`, `"/{id}/vehiculos"`) montado con prefijo `/clientes`, y `router_vehiculos` (`"/{id}"`) montado con prefijo `/vehiculos`; `/mis-vehiculos` se declara como ruta absoluta en `router_vehiculos` o en un tercer router montado sin prefijo, para no colgar de `/vehiculos`.

- Personal: `Annotated[UsuarioAutenticado, Depends(requiere_rol("RECEPCION", "ADMIN"))]`.
- Lo propio: `CurrentUser`, sin `requiere_rol` (RN-17).
- `DELETE /vehiculos/{id}` es el primer endpoint `204` del proyecto: `status_code=status.HTTP_204_NO_CONTENT` y retorno `None`.
- Traducción de errores con el mismo `_traducir` del módulo: `ClienteNoEncontrado`/`VehiculoNoEncontrado` → `404`; `DocumentoYaRegistrado`/`PatenteYaRegistrada`/`VehiculoConOrdenesAbiertas`/`ConflictoDeIntegridad` → `409`; `AnioFueraDeRango` → `422`; `SinFichaDeCliente` → `403`. `AnioFueraDeRango` no queda como clase muerta: el contrato valida el rango y el servicio lo revalida antes de escribir (defensa en profundidad), de modo que un llamador que eluda los validadores recibe un `422` de dominio en lugar de un error del motor. Los mensajes son genéricos, sin nombres de constraints (RN-18).

### 7. Orden de rechazo

Se respeta el orden ya documentado en el proyecto: `401` sin sesión → `403` cambio de contraseña pendiente (dependencia de grupo) → `403` rol (dependencia de ruta) → `404` recurso → `409`/`422` de negocio. Por eso `/mis-vehiculos` sin sesión responde `401` aunque US-013 sólo mencione `200`/`403`.

## Risks / Trade-offs

- **El verificador por defecto siempre dice "sin órdenes abiertas"** → Mitigación: queda aislado tras el protocolo, cubierto por tests con un doble que devuelve `> 0`, y C-07 lo sustituye; se documenta en el propio módulo que la implementación real llega con `orden_trabajo`.
- **El campo `documento` obligatorio rompe el contrato de `POST /auth/registro`** → Mitigación: es un cambio BREAKING declarado en el proposal; los tests de `test/integration/test_auth_router.py` se actualizan en este change, no en C-09.
- **Index único parcial + normalización**: si un cliente antiguo tuviera patentes sin normalizar, el índice no las cubriría → Mitigación: no hay datos previos (no existen migraciones ni seed), y `seed.py` de C-09 debe cargar patentes normalizadas.
- **Dos consultas en la consulta de cliente** → Mitigación: son consultas acotadas por cliente; se acepta a cambio de no modelar una relación filtrada por baja.
- **`Cliente.usuario_id` unique nullable** → PostgreSQL permite varios `NULL` en un `UNIQUE`, que es justo lo necesario para clientes sin cuenta (Jorge en el seed).

## Migration Plan

No hay migración en este change. Los modelos quedan declarados y C-09 los incluye en la migración 001 unificada. Rollback: al no haber cambios de esquema aplicados, revertir el código deja el sistema en el estado de C-04.
