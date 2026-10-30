# Design: c-06-repuestos-stock

## Context

Ver `proposal.md` (Why) y `specs/repuestos-y-stock/spec.md` (requisitos). Condiciones que moldean el enfoque:

- `app/modules/repuestos/` sólo contiene un `__init__.py` vacío. No hay ningún uso previo de `Numeric`/`Decimal` en `app/`: C-06 introduce el primer dinero del proyecto.
- `orden_trabajo` no existe todavía (llega en C-07); sólo existe `EstadoOrden`. `movimiento_stock.orden_id` debe declararse ahora pero su tabla destino no está en el metadata.
- `app/core/paginacion.py` ya ofrece `ParametrosPagina`, `Pagina` y `construir_pagina`, pero el envoltorio `PaginaResponse` y el error `PaginaFueraDeRango` viven dentro del módulo `usuarios` (`app/modules/usuarios/schemas.py:102`, `app/modules/usuarios/errors.py:114`), que C-05 dejó anotado para mover a `core/`.
- `SoftDeleteRepository.contar` hereda el `contar` de `BaseRepository` **sin** aplicar `_no_borrados()` (`app/core/repository.py:155-167`).
- Migraciones, seed y disparadores de sólo agregado son exclusivos de **C-09** (`openspec/changes/c-09-.../tasks.md:5-10`); C-06 sólo deja modelos importables.
- Reglas duras del proyecto: `snake_case`, type hints, `X | None`, `extra="forbid"`, dinero en `NUMERIC`/`Decimal`, fechas `timestamptz`, FK indexadas, seis capas, sin `commit()` en repositorios, `create_all` prohibido.

## Goals / Non-Goals

**Goals:**

- Modelar `repuesto`, `movimiento_stock` e `historial_precio_repuesto` con las restricciones de la KB, de forma que el `autogenerate` de C-09 las emita sin ajustes manuales.
- Un único punto de escritura del stock (alta con movimiento, reposición y, en C-07, consumo por orden).
- Dejar el vocabulario de `motivo` y el envoltorio de paginación en lugares compartidos para que C-07 no duplique ni diverja.

**Non-Goals:**

- Migraciones, seed y disparadores de sólo agregado (C-09).
- Consumo de stock al terminar órdenes y FK efectiva a `orden_trabajo` (C-07).
- `GET /repuestos/{id}` de detalle (decisión del usuario: no incluirlo).
- Alerta de stock mínimo, redondeo monetario o impuestos (no están en la KB).

## Decisions

### 1. Tres entidades en un solo módulo, sin `Relationship`

`Repuesto`, `MovimientoStock` e `HistorialPrecioRepuesto` viven en `app/modules/repuestos/models.py`, con `__tablename__` singular (`repuesto`, `movimiento_stock`, `historial_precio_repuesto`), siguiendo `usuarios/models.py`. No se declaran `Relationship`: el proyecto resuelve las relaciones con consultas explícitas en los repositorios (carga anticipada declarada), lo que evita N+1 y mantiene el metadata simple.

### 2. Columnas, tipos y restricciones

| Tabla | Columna | Tipo | Regla |
|---|---|---|---|
| `repuesto` | `id` | int PK | |
| | `codigo` | `str(50)` | normalizado `strip` + `upper` antes de persistir |
| | `descripcion` | `str(200)` | |
| | `precio` | `Numeric(10, 2)` | `ck_repuesto_precio`: `precio > 0` |
| | `stock` | int | `ck_repuesto_stock`: `stock >= 0` |
| | `borrado_en` | `timestamptz` nulo | |
| `movimiento_stock` | `id` | int PK | |
| | `repuesto_id` | FK `repuesto.id`, indexada, no nula | |
| | `orden_id` | FK `orden_trabajo.id`, indexada, nula | siempre nula en C-06 |
| | `usuario_id` | FK `usuario.id`, indexada, no nula | |
| | `cantidad` | int | `ck_movimiento_stock_cantidad`: `cantidad > 0` |
| | `motivo` | `str(100)` | vocabulario de `motivos.py` |
| | `cuando` | `timestamptz` | `server_default=func.now()` |
| `historial_precio_repuesto` | `id` | int PK | |
| | `repuesto_id` | FK `repuesto.id`, indexada, no nula | |
| | `usuario_id` | FK `usuario.id`, indexada, no nula | |
| | `precio_anterior` | `Numeric(10, 2)` | |
| | `precio_nuevo` | `Numeric(10, 2)` | `ck_historial_precio_nuevo`: `precio_nuevo > 0` y `precio_nuevo > precio_anterior` |
| | `cuando` | `timestamptz` | `server_default=func.now()` |

`repuesto` no lleva `creado_en`/`actualizado_en`: la KB enumera sus atributos y C-05 ya fijó el precedente de agregar sólo `borrado_en` cuando el modelo de datos no pide marcas de tiempo. `motivo` y `codigo`/`descripcion` no tienen longitud en la KB: se eligen 100/50/200 como cotas razonables y se documentan como supuesto.

### 3. Código único parcial, no `UNIQUE`

`Index("ix_repuesto_codigo_vigente", "codigo", unique=True, postgresql_where=text("borrado_en IS NULL"))`, igual que `ix_vehiculo_patente_vigente`. Un `UNIQUE` común impediría reutilizar el código de un repuesto dado de baja, que la KB exige permitir (RN-01, RN-16).

### 4. `orden_id` se declara con FK aunque la tabla llegue en C-07

La alternativa —omitir la columna o dejarla sin FK— obligaría a una migración extra y a tocar el modelo en C-07. Se declara `foreign_key="orden_trabajo.id"` con `nullable=True` y C-06 nunca la escribe. El metadata no se traduce a DDL en ningún punto de C-06 (`create_all` está prohibido, DD-03), y C-09 debe generar la migración cuando `OrdenTrabajo` ya exista.

### 5. `motivo` textual con constantes compartidas

La KB sólo define `cantidad > 0` y `motivo` como texto, sin columna de tipo ni signo: la dirección del movimiento se infiere del motivo. Se crea `app/modules/repuestos/motivos.py` con `MOTIVO_STOCK_INICIAL = "Stock inicial"` y `MOTIVO_REPOSICION = "Reposición"`, que C-07 extenderá con el consumo por orden. Alternativa descartada: agregar una columna `tipo` o un enum, porque no está en el modelo de datos y rompería el seed previsto (`04_modelo_de_datos.md:108-110`).

### 6. El precio sólo sube: 409 desde el servicio, `CHECK` como última red

Ante un `PATCH` con precio menor al vigente, el servicio lanza `PrecioNoAumenta` antes de escribir y el router lo traduce a `409`; el `CHECK precio_nuevo > precio_anterior` queda como última red si algún llamador elude el contrato. Mismo criterio que `AnioFueraDeRango` en C-05: un caso de negocio no debe depender de un error del motor. Precio igual → no-op con `200` y sin línea de historial (US-016 CA-3). Alternativas descartadas: dejar que reviente el `CHECK` (depende del motor y produce un rollback por caso esperado) y devolver `422` (el cuerpo es válido; el conflicto es con la regla del dominio).

### 7. Paginación compartida en `app/core/paginacion.py`

`PaginaResponse` y `PaginaFueraDeRango` se mueven a `app/core/paginacion.py`; `app/modules/usuarios/schemas.py` y `errors.py` los re-exportan para no romper su API pública ni sus tests. El listado de repuestos usa `ParametrosPagina` y `construir_pagina`, y responde `422` cuando `page > pages`. Alternativa descartada: importar desde `usuarios` (acopla dos módulos de dominio) o duplicar el envoltorio (divergencia futura).

### 8. `RepuestoRepository` sobrescribe `contar`

`contar` aplica `_no_borrados()` antes de contar, porque el `contar` heredado no filtra el borrado lógico y `total`/`pages` incluirían repuestos dados de baja. Se cubre con un test dedicado.

### 9. Búsqueda por descripción con parámetro ligado

`GET /repuestos?q=...&page=&size=`: `q` opcional que se aplica como `descripcion.ilike(f"%{q}%")` mediante parámetro ligado (nunca interpolación de SQL), sin distinguir mayúsculas. Sólo descripción, como dice `CHANGES.md`. El orden es `descripcion ASC, id ASC` para que la paginación sea estable entre páginas. Alternativa descartada: buscar también por código (amplía el scope sin pedido).

### 10. Alta: repuesto y movimiento inicial en la misma unidad de trabajo

Secuencia: `add(repuesto)` → `flush` (obtiene la PK) → si `stock > 0`, `add(MovimientoStock(motivo="Stock inicial", usuario_id=actor.id, cantidad=stock))`. Con `stock = 0` no se crea movimiento porque el `CHECK` exige `cantidad > 0`. El conflicto del `add` del repuesto se traduce a `CodigoYaRegistrado`; cualquier conflicto posterior se propaga sin traducir. El alta **no** escribe historial de precios: el seed de la KB sólo tiene una línea de historial 8000→8500, es decir, un cambio posterior.

### 11. `PATCH` parcial con `exclude_unset`

El contrato `EditarRepuestoRequest` declara sólo `descripcion` y `precio` (`extra="forbid"`), así que enviar `stock` es un `422` del contrato sin necesidad de lógica extra. El servicio usa `model_dump(exclude_unset=True)`, resuelve el repuesto vigente (`get` excluye dados de baja → `404`) y, si el precio viene y difiere, valida el aumento y agrega el historial con el valor anterior, el nuevo y el actor: todo dentro de la misma `UnitOfWork`.

### 12. Reponer devuelve el repuesto actualizado

`POST /repuestos/{id}/reponer` con `{"cantidad": n}` (`gt=0`): suma al stock y agrega un movimiento `"Reposición"`, respondiendo `200` con el `RepuestoResponse` actualizado. Devolver la entidad permite al cliente ver el stock nuevo sin una consulta extra y encaja con US-017 (`200`, `404`, `422`).

### 13. `404` uniforme para repuestos no vigentes

Todas las operaciones por `id` usan `SoftDeleteRepository.get`, que ya excluye las filas con `borrado_en`: editar, reponer, consultar movimientos o precios y volver a dar de baja un repuesto inexistente o ya dado de baja responden `404` sin distinguir el caso. La baja usa `soft_delete`, que conserva la marca original si ya estaba dada de baja (defensa redundante que no cambia el contrato).

### 14. Movimientos y precios se devuelven completos y ordenados

`GET /repuestos/{id}/movimientos` y `/precios` devuelven la lista completa con `cuando DESC, id DESC`, igual que el historial de roles. US-018 no pide paginación y un repuesto de taller no acumula volúmenes que la justifiquen; agregarla después sería compatible.

### 15. `cuando` lo fija la base

`server_default=func.now()` en las dos tablas de sólo agregado, como el resto de los modelos del proyecto. Los tests inspeccionan las entidades agregadas y no dependen del reloj; si C-07 necesita un instante determinista, podrá inyectarlo allí.

### 16. Autorización por ruta

Lectura del catálogo (`GET /repuestos`): `requiere_rol("ADMIN", "RECEPCION", "MECANICO")`. Administración (`POST`, `PATCH`, `POST .../reponer`, `DELETE`, `GET .../movimientos`, `GET .../precios`): `requiere_rol("ADMIN")`. El grupo protegido ya aplica `require_password_change`, así que una cuenta con cambio pendiente recibe `403` en todas las rutas.

### 17. Sin eventos de seguridad

La auditoría de inventario son `movimiento_stock` e `historial_precio_repuesto` (RN-14, RN-15, RN-20); `evento_seguridad` queda reservado a credenciales y roles. No se escribe ninguna fila de esa tabla desde este módulo.

### 18. Errores y traducción HTTP

`RepuestoNoEncontrado` → `404`; `CodigoYaRegistrado` y `PrecioNoAumenta` → `409`; `PaginaFueraDeRango` → `422`; `ConflictoDeIntegridad` → `409`. Mensajes genéricos de dominio, sin tablas, columnas ni restricciones (RN-18).

### 19. Montaje y `204`

Un router `router_repuestos` montado en `router_protegido` con `prefix="/repuestos"`. El `DELETE` responde `204` con `response_class=Response` y `response_model=None` (lección de C-05: sin `response_model=None`, FastAPI rechaza un `204` con cuerpo declarado).

### 20. Decimal en los contratos

`precio`, `precio_nuevo` y `precio_anterior` usan `Decimal` con `max_digits=10, decimal_places=2, gt=0` en los contratos de entrada. No se cuantiza a mano: el contrato ya rechaza más de dos decimales y `NUMERIC(10, 2)` los conserva.

## Risks / Trade-offs

- **`orden_id` apunta a una tabla que aún no existe** — Mitigación: columna nullable, C-06 nunca la escribe y no se genera DDL; C-09 emite la migración con `OrdenTrabajo` ya presente.
- **Mover `PaginaResponse`/`PaginaFueraDeRango` toca el módulo `usuarios`** — Mitigación: re-export con los mismos nombres y la suite completa de usuarios como red de seguridad.
- **`SoftDeleteRepository.contar` no filtra bajas** — Mitigación: override en `RepuestoRepository` más un test que verifica `total`/`pages` con repuestos dados de baja.
- **El `409` por bajar el precio depende del servicio, no del `CHECK`** — Mitigación: test unitario que construye el contrato con `model_construct` (eludiendo validadores) y test de integración; el `CHECK` queda como última red.
- **Longitudes de `codigo`, `descripcion` y `motivo` no definidas por la KB** — Mitigación: cotas explícitas (50/200/100) documentadas como supuesto; ampliarlas después es una migración trivial.
- **Sin `GET /repuestos/{id}`** — el cliente debe localizar el repuesto por el listado antes de editar o reponer. Limitación aceptada por el usuario para no ampliar el scope de `CHANGES.md`.
- **El seed de C-09 depende de estas formas** — Mitigación: `Decimal`, motivo `"Stock inicial"` y FK a `usuario` quedan fijados por constantes y tests de metadata.

## Migration Plan

Este change no genera migraciones ni seed: sólo modelos importables. C-09 ejecuta `alembic autogenerate` con los modelos de C-02 a C-07 y agrega a mano los disparadores de sólo agregado sobre `movimiento_stock` e `historial_precio_repuesto` (RN-15). Rollback: quitar el módulo y sus montajes; no hay cambio de esquema que revertir en C-06.

## Open Questions

- Qué motivo exacto usará C-07 para el consumo por orden: se decide allí, siempre a través de `app/modules/repuestos/motivos.py`.
- Si más adelante se necesita un umbral de stock mínimo o alertas: la KB no lo pide y no afecta a este diseño.
