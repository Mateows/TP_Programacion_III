# Tasks

## 1. Modelos y restricciones

- [x] 1.1 Crear `app/modules/repuestos/motivos.py` con `MOTIVO_STOCK_INICIAL = "Stock inicial"` y `MOTIVO_REPOSICION = "Reposición"` (más `__all__`), y verificar con un test unitario que los valores son los que espera el seed de la KB
- [x] 1.2 Implementar `Repuesto` en `app/modules/repuestos/models.py` (`__tablename__="repuesto"`, `codigo` 50, `descripcion` 200, `precio Numeric(10,2)`, `stock`, `borrado_en`) con `ck_repuesto_precio`, `ck_repuesto_stock` e `ix_repuesto_codigo_vigente` único parcial; verificar con tests de metadata (nombre de tabla, columnas, checks, índice único parcial con `borrado_en IS NULL`)
- [x] 1.3 Implementar `MovimientoStock` (`repuesto_id` y `usuario_id` con FK indexada no nula, `orden_id` FK indexada nula a `orden_trabajo.id`, `cantidad` con `ck_movimiento_stock_cantidad`, `motivo` 100, `cuando` timestamptz con `server_default`); verificar con tests de metadata que ambas FKs tienen índice y que `orden_id` es nula
- [x] 1.4 Implementar `HistorialPrecioRepuesto` (`repuesto_id` y `usuario_id` con FK indexada no nula, `precio_anterior` y `precio_nuevo Numeric(10,2)`, `cuando` con `server_default`) con `ck_historial_precio_nuevo` para `precio_nuevo > 0` y `precio_nuevo > precio_anterior`; verificar con tests de metadata que los dos checks existen con ese texto

## 2. Repositorios

- [x] 2.1 Implementar `RepuestoRepository(SoftDeleteRepository[Repuesto])` en `app/modules/repuestos/repository.py` con `buscar_vigente_por_codigo`, `listar_paginado(*, texto, limit, offset)` (filtro `ilike` ligado sobre descripción, orden `descripcion ASC, id ASC`) y `contar(*filtros, texto=None)` sobrescrito que aplique `_no_borrados()` y el mismo filtro de descripción; verificar con tests unitarios sobre `SesionFalsa` que el conteo excluye dados de baja, que filtra por `texto` y que la sentencia usa parámetro ligado
- [x] 2.2 Implementar `MovimientoStockRepository.listar_por_repuesto(repuesto_id)` con orden `cuando DESC, id DESC`; verificar con test unitario que la sentencia filtra por repuesto y ordena descendente
- [x] 2.3 Implementar `HistorialPrecioRepository.listar_por_repuesto(repuesto_id)` con orden `cuando DESC, id DESC`; verificar con test unitario que la sentencia filtra por repuesto y ordena descendente
- [x] 2.4 Verificar con test unitario que `soft_delete` sobre un repuesto ya dado de baja conserva la marca original y no lanza, reutilizando el comportamiento de `SoftDeleteRepository`

## 3. Contratos, errores y paginación compartida

- [x] 3.1 Mover `PaginaResponse` y `PaginaFueraDeRango` a `app/core/paginacion.py` y re-exportarlos desde `app/modules/usuarios/schemas.py` y `app/modules/usuarios/errors.py`; verificar que `pytest test/unit -q` y `pytest test/integration -q` siguen verdes antes de sumar tests nuevos
- [x] 3.2 Implementar `app/modules/repuestos/schemas.py`: `AltaRepuestoRequest` (código normalizado `strip`+`upper`, `precio` `Decimal` con `max_digits=10, decimal_places=2, gt=0`, `stock` `ge=0`), `EditarRepuestoRequest` (sólo `descripcion` y `precio`), `ReponerRequest` (`cantidad` `gt=0`), `RepuestoResponse`, `MovimientoStockResponse` y `HistorialPrecioResponse`, todos con `extra="forbid"`; verificar con tests unitarios de normalización, `422` por precio no positivo, tres decimales, stock negativo, `stock` en el PATCH y campo no declarado
- [x] 3.3 Implementar `app/modules/repuestos/errors.py` con `ErrorRepuestos`, `RepuestoNoEncontrado`, `CodigoYaRegistrado` y `PrecioNoAumenta`; verificar con test unitario que todos heredan del error base y que sus mensajes no contienen `ix_`, `ck_`, `uq_` ni nombres de tabla

## 4. Alta y listado de repuestos

- [x] 4.1 Implementar `crear_repuesto(uow, datos, actor)` en `app/modules/repuestos/service.py`: `add` + `flush` del repuesto, traducción del conflicto a `CodigoYaRegistrado`, y movimiento `"Stock inicial"` sólo si `stock > 0`; verificar con tests unitarios de alta con stock (dos filas, un solo commit), alta con stock cero (sin movimiento), código repetido y conflicto posterior propagado
- [x] 4.2 Implementar `listar_repuestos(uow, parametros, texto)` con `contar(texto=texto)` + `construir_pagina` (el total y `pages` cuentan sólo las coincidencias), `PaginaFueraDeRango` si `page > pages` y `PaginaResponse`; verificar con tests unitarios de página por omisión, búsqueda con texto, búsqueda sin coincidencias (`total` cero) y página fuera de rango
- [x] 4.3 Implementar `app/modules/repuestos/router.py` con `ERRORES_DE_REPUESTOS`, `_traducir`, `POST /repuestos` (ADMIN, `201`) y `GET /repuestos` (ADMIN/RECEPCION/MECANICO, `200`, `page`/`size`/`q` por `Query`), y montar el router en `router_protegido` desde `app/main.py`; verificar con tests de integración de `201`, `409`, `422`, `403` por rol, `403` por cambio de contraseña, `401` sin sesión, paginación y `422` por página fuera de rango
- [x] 4.4 Documentar el nuevo módulo en `test/unit/README.md` (conteo real de la suite y filas de los archivos de test de repuestos) y verificar que los conteos coinciden con la ejecución

## 5. Edición y precio

- [x] 5.1 Implementar `editar_repuesto(uow, repuesto_id, datos, actor)` con `exclude_unset`: `404` si no está vigente, actualización de descripción, y para el precio `409` si baja (`PrecioNoAumenta`), no-op sin historial si es igual y actualización con línea de historial si sube; verificar con tests unitarios de sólo descripción, precio igual sin historial, precio menor sin escritura, precio mayor con historial y repuesto inexistente
- [x] 5.2 Sumar `PATCH /repuestos/{id}` al router con `response_model=RepuestoResponse`; verificar con tests de integración de `200`, `404`, `422` por `stock` en el cuerpo, `422` por precio no positivo, `409` por precio menor y `403` sin `ADMIN`

## 6. Reposición y consultas de inventario

- [x] 6.1 Implementar `reponer_stock(uow, repuesto_id, cantidad, actor)`: `404` si no está vigente, suma al stock y agrega movimiento `"Reposición"`, devolviendo el repuesto actualizado; verificar con tests unitarios de reposición exitosa (stock sumado y movimiento), cantidad no positiva rechazada por el contrato y repuesto inexistente sin escritura
- [x] 6.2 Implementar `consultar_movimientos(uow, repuesto_id)` y `consultar_precios(uow, repuesto_id)` con `404` si el repuesto no está vigente y listas ordenadas del más reciente al más antiguo; verificar con tests unitarios de lista con filas, lista vacía e inexistente
- [x] 6.3 Sumar `POST /repuestos/{id}/reponer` (`200`), `GET /repuestos/{id}/movimientos` y `GET /repuestos/{id}/precios` (ADMIN) al router; verificar con tests de integración de `200`, `404`, `422` por cantidad no positiva, `403` sin `ADMIN` y `401` sin sesión

## 7. Baja lógica

- [x] 7.1 Implementar `dar_de_baja_repuesto(uow, repuesto_id)` con `soft_delete` y `404` si no está vigente; verificar con tests unitarios de baja exitosa (`borrado_en` seteado, commit), baja repetida (`404`, sin escritura) y conservación de movimientos e historial encolados
- [x] 7.2 Sumar `DELETE /repuestos/{id}` con `204`, `response_class=Response` y `response_model=None`; verificar con tests de integración de `204` sin cuerpo, repuesto excluido del listado tras la baja, `404` en baja repetida, `404` al reponer o editar el dado de baja y `403` sin `ADMIN`

## 8. Integración y cierre

- [x] 8.1 Verificar que los modelos de repuestos son importables sin efectos secundarios (`python -c "import app.modules.repuestos.models"` e `import app.main`) y que las tres tablas aparecen en `metadata.tables` sin ejecutar DDL, para que el `autogenerate` de C-09 las vea
- [x] 8.2 Ejecutar `pytest test/unit -q`, `pytest test/integration -q` y `openspec validate c-06-repuestos-stock --strict`, y confirmar que las cinco rutas nuevas aparecen en `app.routes` con sus roles
- [x] 8.3 Actualizar `CHANGES.md` (C-06 en `[x]` completado con los conteos reales y el scope efectivo) y `test/unit/README.md` (conteos finales y rutas cubiertas), verificando que ambos archivos quedan en UTF-8 sin BOM

## Workflow follow-up

- Archivar el change cuando la revisión del proyecto lo autorice.
- Verificar el resultado archivado (`openspec validate --archived`).
- Dejar anotado para C-07 el motivo del consumo por orden, creado a partir de `app/modules/repuestos/motivos.py`.
