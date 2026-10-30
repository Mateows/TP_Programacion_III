# Design

## Context

Ver `proposal.md` — Why. El estado actual relevante:

- `app/modules/ordenes/models.py` sólo tiene `EstadoOrden` (catálogo, PK `codigo`).
- `MovimientoStock.orden_id` ya declara la FK a `orden_trabajo.id`, todavía irresoluble porque la tabla no existe.
- No hay ninguna `Relationship` en `app/`: todas las lecturas son consultas explícitas por FK, y los tests usan una `SesionFalsa` que no resuelve cargas perezosas ni `unique()`.
- `dar_de_baja_vehiculo` acepta un `VerificadorOrdenesAbiertas` inyectable, pero el router no lo pasa y el default es `SinOrdenesAbiertas`, que siempre responde `0`.
- `UnitOfWork` confirma al salir del bloque y revierte con excepción; los repositorios sólo hacen `flush`.
- `PaginaResponse`, `PaginaFueraDeRango` y `construir_pagina` viven en `app/core/paginacion.py`; el listado de repuestos acepta la página 1 con `pages == 0`.
- No hay `BackgroundTasks` en uso ni versiones Alembic; la migración 001 es de C-09.

## Goals / Non-Goals

**Goals:**

- Modelar `orden_trabajo`, `item_orden` e `historial_estado_orden` con las restricciones del dominio y dejarlos importables para la migración de C-09.
- Exponer el ciclo completo de la orden con autorización por rol vigente y por dueño del vehículo, distinguiendo `401`, `403`, `404`, `409` y `422` en el orden que fijan RN-11/RN-12.
- Consumir stock de forma atómica en la terminación, reutilizando el patrón de movimientos existente.
- Cerrar RN-16 con un verificador real, sin cambiar el contrato de `DELETE /vehiculos/{id}`.
- Mantener el detalle sin N+1 con un número constante de consultas.

**Non-Goals:**

- Migraciones, seed y disparadores de sólo agregado (C-09).
- `GET /mis-ordenes` y la autorización de "lo propio" como listado (C-08); C-07 sólo resuelve el acceso del dueño al detalle y a la cancelación.
- Bloqueo pesimista entre transacciones concurrentes más allá de `SELECT ... FOR UPDATE` sobre los repuestos de la orden; no hay requisito de rendimiento ni de reintentos.
- Notificaciones reales: el aviso al cliente es simulado y no observable por HTTP.

## Decisions

### 1. Modelos planos, sin `Relationship`

`OrdenTrabajo` (`orden_trabajo`): `id` PK, `vehiculo_id` FK indexada no nula, `mecanico_id` FK a `usuario.id` indexada nullable, `estado` FK a `estado_orden.codigo` indexada no nula, `falla` `String(500)` no nula, `total` `Numeric(12,2)` no nulo con `CheckConstraint("total >= 0", name="ck_orden_trabajo_total")`, `creada_en` `timestamptz` no nula con `server_default=func.now()`.

`ItemOrden` (`item_orden`): `id` PK, `orden_id` y `repuesto_id` FK indexadas no nulas, `cantidad` int no negativo positivo (`CHECK cantidad > 0`, `ck_item_orden_cantidad`), `precio_unitario` `Numeric(10,2)` (`CHECK precio_unitario > 0`, `ck_item_orden_precio`), `UniqueConstraint("orden_id", "repuesto_id", name="uq_item_orden_repuesto")`.

`HistorialEstadoOrden` (`historial_estado_orden`): `id` PK, `orden_id` FK indexada no nula, `desde_estado` FK a `estado_orden.codigo` indexada nullable, `hasta_estado` FK indexada no nula, `usuario_id` FK indexada no nula, `cuando` `timestamptz` con `server_default=func.now()`.

**Por qué:** el proyecto no declara relaciones en ningún módulo y los dobles de test no las resuelven. Las lecturas se harán con consultas explícitas; agregar `Relationship` sólo a órdenes introduciría un patrón nuevo y obligaría a `foreign_keys` explícitos por las dos FK a `estado_orden` y a `unique()` en `joinedload` de colecciones. **Alternativa descartada:** `Relationship(lazy="raise") + selectinload`; más ergonómico, pero incompatible con la `SesionFalsa` actual sin extenderla y con mayor riesgo de ciclos.

Se usa `creada_en` (nombre del modelo de datos de la KB) y no el `TimestampMixin` de C-02, que agrega `actualizado_en`; la orden es de sólo agregado en su creación y no necesita marca de actualización.

### 2. Repositorios: catálogo, orden, ítems e historial

- `EstadoOrdenRepository`: `listar()` ordenado por `posicion`, `existe(codigo) -> bool`, `contar()`.
- `OrdenTrabajoRepository`: `get(id)` (sin baja lógica), `contar(*filtros, estado=None)`, `listar_paginado(*, estado, limit, offset)` con orden `creada_en DESC, id DESC`, `listar_detalle(id)`.
- `ItemOrdenRepository`: `listar_por_orden(orden_id)` con join a `repuesto` para obtener descripción y precio copiado.
- `HistorialEstadoOrdenRepository`: `listar_por_orden(orden_id)` ordenado `cuando ASC, id ASC` (el detalle muestra la cronología).

**Detalle sin N+1:** `listar_detalle` ejecuta un número fijo de consultas, independiente de la cantidad de ítems: (1) orden con join a `vehiculo`, `cliente`, `usuario` (mecánico) y `estado_orden`; (2) ítems con join a `repuesto`; (3) historial. Se devuelve un `DetalleOrden` (dataclass con la orden y las filas resueltas) para que el servicio no dispare consultas por ítem. **Alternativa descartada:** cargar la orden y acceder a colecciones (sería N+1 o exigiría relaciones).

### 3. Contratos y formas de respuesta

- `AltaOrdenRequest`: `vehiculo_id: int`, `falla: str = Field(min_length=1, max_length=500)`, `items: list[ItemOrdenRequest] = Field(min_length=1)`. `ItemOrdenRequest`: `repuesto_id: int`, `cantidad: int = Field(gt=0)`. `extra="forbid"` en todos; un `precio`, `total`, `estado` o `mecanico_id` en el cuerpo da `422`.
- Un `@model_validator(mode="after")` en `AltaOrdenRequest` rechaza `repuesto_id` repetidos con `422` antes de tocar la base (el `UNIQUE` queda como última red).
- `OrdenResumenResponse`: `id`, `vehiculo_id`, `patente`, `estado`, `mecanico_id`, `falla`, `total`, `creada_en`.
- `OrdenDetalleResponse`: `id`, `vehiculo` (`id`, `patente`, `marca`, `modelo`, `anio`), `cliente` (`id`, `nombre`, `documento`, `telefono`), `estado`, `mecanico_id`, `mecanico_nombre`, `falla`, `total`, `creada_en`, `items` (`id`, `repuesto_id`, `descripcion`, `cantidad`, `precio_unitario`) y `historial` (`id`, `desde_estado`, `hasta_estado`, `usuario_id`, `cuando`).
- `EstadoOrdenResponse`: `codigo`, `descripcion`, `posicion`, `es_final`.
- `POST /ordenes`, `POST /iniciar`, `/terminar` y `/cancelar` responden `OrdenDetalleResponse`; `GET /ordenes` responde `PaginaResponse[OrdenResumenResponse]`; `GET /ordenes/{id}` responde `OrdenDetalleResponse`.

**Supuesto registrado:** `falla` es obligatoria con máximo 500 caracteres. El usuario no respondió esta decisión; se elige la opción conservadora y se documenta.

### 4. Autorización: dependencia por ruta y regla de dominio en el servicio

| Ruta | Dependencia | Regla adicional |
|---|---|---|
| `POST /ordenes` | `requiere_rol("ADMIN", "RECEPCION")` | — |
| `GET /ordenes` | `requiere_rol("ADMIN", "RECEPCION", "MECANICO")` | — |
| `GET /ordenes/{id}` | `CurrentUser` | personal (`ADMIN`, `RECEPCION`, `MECANICO`) o dueño del vehículo |
| `POST /{id}/iniciar` | `requiere_rol("MECANICO")` | estado `PENDIENTE` |
| `POST /{id}/terminar` | `requiere_rol("ADMIN", "MECANICO")` | `ADMIN` o `orden.mecanico_id == actor.id` |
| `POST /{id}/cancelar` | `CurrentUser` | `ADMIN`/`RECEPCION` o dueño del vehículo |
| `GET /estados-orden` | `CurrentUser` | — |

El servicio recibe `actor: UsuarioAutenticado` (o el usuario y sus roles) y aplica la regla de dueño con `ClienteRepository.buscar_por_usuario(actor.id)` y `VehiculoRepository.get(orden.vehiculo_id)`: es dueño si existe ficha y `vehiculo.cliente_id == ficha.id`. La cuenta sin ficha nunca es dueña. El personal se evalúa con `actor.tiene_rol(...)` sobre los roles vigentes que ya resolvió `get_current_user`.

**Orden de errores:** primero `404` si la orden no existe; después autorización (`403`); después estado (`409`). Para `terminar` se sigue el mismo criterio aunque RN-12 lo diga sólo de `cancelar`: el usuario eligió explícitamente "autorización antes que estado". Para `iniciar`, la dependencia de rol produce `403` antes de consultar la orden; luego `404` y `409`.

**Alternativa descartada:** `requiere_rol` para cancelar/detalle. Imposibilitaría el acceso del dueño sin rol de personal. Para el detalle se devuelve `403` a un no-dueño autenticado (no `404`): se prioriza RN-17 y la claridad del contrato; el `404` queda reservado a la orden inexistente.

### 5. Alta: catálogo, vehículo y repuestos

Dentro de `async with uow`:

1. `EstadoOrdenRepository.contar()`; si es `0` → `CatalogoDeEstadosVacio` (`409`). Si no contiene `PENDIENTE` → mismo error (FK inválida de otro modo).
2. `VehiculoRepository.get(vehiculo_id)` (excluye baja) → `None` → `VehiculoNoDisponible` (`409`).
3. `RepuestoRepository.listar_vigentes_por_ids(ids)` en una sola consulta; si falta alguno de los pedidos (inexistente o dado de baja) → `RepuestoNoDisponible` (`409`).
4. Construir `ItemOrden` con `precio_unitario = repuesto.precio` y `cantidad`; `total = sum(precio * cantidad)` con `Decimal` y cuantización a dos decimales.
5. `add` de la orden, `flush` para obtener la PK, `add` de ítems e historial (`desde_estado=None`, `hasta_estado="PENDIENTE"`, `usuario_id=actor.id`), `flush`.

No se escribe movimiento de stock en el alta: el stock no cambia hasta la terminación (RN-14). **Alternativa descartada:** mover stock al crear la orden; contradice el flujo 4 y RN-13.

### 6. Listado y página vacía

Se reutiliza `ParametrosPagina`, `construir_pagina` y `PaginaResponse`. El filtro `estado` se valida contra el catálogo antes de contar: si no existe → `EstadoNoDeclarado` (`422`). Se adopta la convención de repuestos: `ultima_pagina = max(previa.pages, 1)`, de modo que un listado vacío tiene `pages == 0` y su página 1 es válida. El conteo y las filas usan el mismo filtro. **Alternativa descartada:** validar `estado` con un `Literal` fijo; acoplaría el contrato al seed y rompería si el catálogo cambia (RN-19).

### 7. Transiciones y consumo atómico

Una tabla de transiciones permitidas: `PENDIENTE → EN_REPARACION`, `EN_REPARACION → TERMINADA`, `PENDIENTE → CANCELADA`; cualquier otra → `TransicionNoPermitida` (`409`). Cada transición agrega una línea de historial con `desde_estado` actual, `hasta_estado` destino, actor y momento, y actualiza `orden.estado` (y `mecanico_id` en `iniciar`).

Terminación, dentro de una única UoW:

1. Verificar autorización (ADMIN o mecánico asignado) antes de mirar el estado.
2. Verificar estado `EN_REPARACION`.
3. Cargar todos los repuestos de los ítems con `SELECT ... FOR UPDATE` (`listar_por_ids_para_actualizar`) y validar que cada `stock >= cantidad`; si alguno no alcanza → `StockInsuficiente` (`409`) antes de mutar nada.
4. Descontar `stock` de cada repuesto, agregar un `MovimientoStock` por ítem con `cantidad` positiva, `motivo=MOTIVO_CONSUMO_ORDEN`, `orden_id=orden.id`, `usuario_id=actor.id`.
5. Cambiar el estado a `TERMINADA`, agregar el historial y `flush`.

Si algo falla después de mutar, la UoW revierte todo (RN-13). El movimiento usa `cantidad` positiva porque el signo lo da el motivo (no hay columna de dirección). **Alternativa descartada:** `UPDATE ... WHERE stock >= cantidad` con `rowcount`; más robusto frente a concurrencia, pero la `SesionFalsa` no modela `rowcount` y el requisito no pide ese nivel. El `FOR UPDATE` cubre la carrera dentro de una transacción.

El aviso al cliente se agenda con `BackgroundTasks` en el router **después** de que el servicio retorna (la UoW ya confirmó): `tareas.add_task(avisar_terminacion, orden_id)`. Es una corrutina que simula el envío como describe SU-01 (`await asyncio.sleep(0.5)`) y deja el mensaje en el log; no toca la base ni hace I/O de red y no usa la sesión de la petición.

### 8. RN-16: verificador real y retiro del stub

`app/modules/ordenes/verificacion.py` define `VerificadorOrdenesAbiertasSQL(session: AsyncSession)` con `contar_abiertas(vehiculo_id)`:

```sql
SELECT count(*) FROM orden_trabajo
JOIN estado_orden ON estado_orden.codigo = orden_trabajo.estado
WHERE orden_trabajo.vehiculo_id = :id AND estado_orden.es_final = false
```

Implementa el `Protocol` `VerificadorOrdenesAbiertas` de `clientes.verificacion` (importar sólo el protocolo; no hay ciclo porque `clientes.verificacion` no importa nada del dominio). `clientes/router.py` inyecta `VerificadorOrdenesAbiertasSQL(session)` en `dar_de_baja_vehiculo`; se elimina `SinOrdenesAbiertas` de producción y `verificador` pasa a ser obligatorio en el servicio. Los tests que usaban el stub se reemplazan por un doble local (`VerificadorFijo`), que ya existe.

**Alternativa descartada:** dejar `SinOrdenesAbiertas` como default. Mantendría RN-16 sin cumplir en producción, que es justamente lo que este change cierra.

### 9. Ubicación del código

```
app/modules/ordenes/
├── models.py          # + OrdenTrabajo, ItemOrden, HistorialEstadoOrden
├── schemas.py         # requests, responses y DetalleOrden
├── errors.py          # ErrorOrdenes y subclases
├── repository.py      # catálogo, orden, ítems, historial
├── service.py         # alta, listado, detalle, estados, transiciones
├── router.py          # /ordenes y /estados-orden
├── verificacion.py    # VerificadorOrdenesAbiertasSQL
└── avisos.py          # aviso simulado al cliente
```

`app/main.py` monta `router_ordenes` en `/ordenes` y `router_estados_orden` en `/estados-orden`, ambos dentro de `router_protegido`. `app/modules/repuestos/motivos.py` agrega `MOTIVO_CONSUMO_ORDEN = "Consumo por orden"` y lo exporta.

## Risks / Trade-offs

- **Concurrencia en la terminación:** dos terminaciones simultáneas podrían leer el mismo stock antes del `FOR UPDATE` si el motor no lo aplica como se espera → el bloqueo de fila y la validación previa lo mitigan; no hay reintentos ni requisito de alto rendimiento.
- **Detalle con consultas explícitas:** más código de mapeo que un `selectinload` → se encapsula en `listar_detalle` y se prueba que el número de consultas es constante.
- **`SesionFalsa` limitada:** no soporta `rowcount`, `unique()` ni cargas → los tests construyen el `DetalleOrden` a mano y no se usan esas APIs.
- **Retirar `SinOrdenesAbiertas`:** rompe tests existentes que lo instancian → se actualizan en la misma tarea; el contrato HTTP de `DELETE /vehiculos/{id}` no cambia.
- **`falla` obligatoria:** si el cliente real la considera opcional, el contrato habrá que relajarlo → queda como supuesto explícito y el cambio sería un `min_length` menos.
- **`total` y precios:** se usa `Decimal` y `Numeric(12,2)`; nunca `float`. El total se calcula una vez y no se recalcula al terminar (el precio quedó congelado en el ítem).
- **BackgroundTasks:** si el proceso muere después de responder, el aviso se pierde → es simulado y no forma parte del contrato.

## Migration Plan

- Sin migración en este change: sólo se agregan modelos importables. `MovimientoStock.orden_id` resuelve su FK cuando `OrdenTrabajo` está importado en el metadata; C-09 debe importar todos los modelos antes de `alembic autogenerate` y generar la revisión 001.
- Despliegue: montar los routers no requiere variables nuevas. Rollback: revertir el change; no hay cambios de esquema que deshacer.
- El catálogo y las órdenes de ejemplo siguen a cargo de `seed.py` (C-09).

## Open Questions

- Ninguna que afecte specs, enfoque o desglose de tareas. El canal real de aviso y el bloqueo optimista entre transacciones quedan fuera del alcance y pueden resolverse en un change posterior.
