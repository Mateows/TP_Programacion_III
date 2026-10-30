# Tasks

## 1. Modelos de órdenes

- [x] 1.1 Agregar `OrdenTrabajo` (`orden_trabajo`) a `app/modules/ordenes/models.py`: `vehiculo_id` FK indexada no nula, `mecanico_id` FK a `usuario.id` indexada nullable, `estado` FK a `estado_orden.codigo` indexada, `falla` 500, `total` `Numeric(12,2)` con `CHECK total >= 0`, `creada_en` `timestamptz` con `server_default=func.now()`; tests de columnas, CHECK, FK indexadas y zona horaria
- [x] 1.2 Agregar `ItemOrden` (`item_orden`) con FK indexadas a `orden_trabajo.id` y `repuesto.id`, `cantidad` y `precio_unitario` positivos (`CHECK`), `precio_unitario` `Numeric(10,2)` y `UNIQUE (orden_id, repuesto_id)`; tests de unicidad y CHECK
- [x] 1.3 Agregar `HistorialEstadoOrden` (`historial_estado_orden`) con `orden_id` y `usuario_id` indexados, `desde_estado` nullable y `hasta_estado` no nulo (ambos FK a `estado_orden.codigo` e indexados), `cuando` `timestamptz`; tests de FKs, nulabilidad y ausencia de timestamps de auditoría
- [x] 1.4 Verificar que los tres modelos son importables, que `SQLModel.metadata` contiene las tablas y que `MovimientoStock.orden_id` resuelve su FK; sin `create_all`, sin migraciones y sin `Relationship`

## 2. Repositorios y motivos

- [x] 2.1 Crear `EstadoOrdenRepository` en `app/modules/ordenes/repository.py` con `listar()` ordenado por `posicion`, `existe(codigo)` y `contar()`, sin ninguna escritura; tests sobre `SesionFalsa`
- [x] 2.2 Crear `OrdenTrabajoRepository` con `get`, `contar(*filtros, estado=None)` y `listar_paginado(*, estado, limit, offset)` ordenado `creada_en DESC, id DESC`, aplicando el mismo filtro al conteo y a las filas; tests de filtro, orden y paginación
- [x] 2.3 Implementar `listar_detalle(orden_id)` con un número constante de consultas (orden con vehículo/cliente/mecánico/estado, ítems con repuesto e historial) y `ItemOrdenRepository.listar_por_orden` / `HistorialEstadoOrdenRepository.listar_por_orden`; test que cuente las consultas y verifique el orden cronológico del historial
- [x] 2.4 Ampliar `RepuestoRepository` con `listar_vigentes_por_ids(ids)` y `listar_por_ids_para_actualizar(ids)` con `SELECT ... FOR UPDATE`; tests de filtro de bajas, consulta única y bloqueo de filas
- [x] 2.5 Agregar `MOTIVO_CONSUMO_ORDEN = "Consumo por orden"` a `app/modules/repuestos/motivos.py` y exportarlo en `__all__`; test del valor exacto y de que C-07 no reescribe los motivos existentes

## 3. Contratos y errores

- [x] 3.1 Crear `app/modules/ordenes/schemas.py` con `ItemOrdenRequest`, `AltaOrdenRequest` (`falla` obligatoria 1..500, `items` con al menos uno, `extra="forbid"`) y un validador que rechace repuestos repetidos con `422`; tests de contrato, campo extra y duplicados
- [x] 3.2 Agregar `OrdenResumenResponse`, `OrdenDetalleResponse`, `ItemOrdenResponse`, `HistorialEstadoResponse` y `EstadoOrdenResponse`, y el mapeo desde las filas del detalle; tests de `model_validate` y de campos anidados
- [x] 3.3 Crear `app/modules/ordenes/errors.py` con `ErrorOrdenes`, `OrdenNoEncontrada`, `VehiculoNoDisponible`, `RepuestoNoDisponible`, `CatalogoDeEstadosVacio`, `EstadoNoDeclarado`, `TransicionNoPermitida`, `StockInsuficiente` y `SinPermisoSobreLaOrden`; tests de jerarquía y de mensajes sin nombres de tabla, columna o restricción

## 4. Alta y listado de órdenes

- [x] 4.1 Implementar `crear_orden` en `app/modules/ordenes/service.py`: catálogo no vacío y con `PENDIENTE`, vehículo vigente, repuestos vigentes en una consulta, precio copiado, total en `Decimal`, primera línea `null → PENDIENTE`, todo en una UoW; tests de alta, catálogo vacío, vehículo y repuesto no disponibles y precios copiados
- [x] 4.2 Implementar `listar_ordenes` con validación de `estado` contra el catálogo (`422`), conteo y filas con el mismo filtro, y convención de página 1 válida con `pages == 0`; tests de filtro, estado inexistente y página fuera de rango
- [x] 4.3 Crear `app/modules/ordenes/router.py` con `POST /ordenes` (`201`, ADMIN/RECEPCION) y `GET /ordenes` (`200`, ADMIN/RECEPCION/MECANICO), `_traducir` y `ERRORES_DE_ORDENES`; montar `/ordenes` en `router_protegido` de `app/main.py`; tests de contrato `201/403/409/422`, listado y `401`
- [x] 4.4 Agregar tests de integración de alta y listado en `test/integration/test_ordenes_router.py`: alta exitosa con historial, ítem repetido `422`, campo extra `422`, vehículo/repuesto no disponible `409`, catálogo vacío `409`, roles y paginación

## 5. Detalle y catálogo de estados

- [x] 5.1 Implementar `consultar_orden` con autorización de personal o dueño del vehículo (`ClienteRepository.buscar_por_usuario` + `VehiculoRepository.get`), `404` antes de permiso y `403` para autenticado sin permiso; tests de personal, dueño, no-dueño y cuenta sin ficha
- [x] 5.2 Implementar `listar_estados` y `GET /estados-orden` (`200`, cualquier autenticado, ordenado por posición) en el router; tests de orden, `es_final`, `401` y ausencia de rutas de escritura
- [x] 5.3 Agregar tests de integración de detalle y catálogo: `200` con vehículo/cliente/ítems/historial, `403` de no-dueño, `404`, `401`, catálogo con cuatro estados y finales marcados

## 6. Transiciones de estado

- [x] 6.1 Implementar `iniciar_orden`: sólo `MECANICO`, `PENDIENTE → EN_REPARACION`, asignación al actor, línea de historial y `200`; tests de inicio, estado incorrecto `409`, rol `403`, inexistente `404`
- [x] 6.2 Implementar `terminar_orden`: autorización (ADMIN o mecánico asignado) antes que estado, validación de stock con `FOR UPDATE`, descuento, un movimiento por ítem con `MOTIVO_CONSUMO_ORDEN` y `orden_id`, historial y atomicidad; tests de descuento, historial, stock insuficiente `409` sin escrituras y varios ítems con uno insuficiente
- [x] 6.3 Implementar `cancelar_orden`: permiso (`ADMIN`/`RECEPCION` o dueño) antes que estado, sólo `PENDIENTE → CANCELADA`, historial y `200`; tests de personal, dueño sin rol, no-dueño `403`, estado `409`, permiso antes que estado y `404`
- [x] 6.4 Agregar `POST /{id}/iniciar`, `POST /{id}/terminar` y `POST /{id}/cancelar`, con `BackgroundTasks` para el aviso simulado después del commit; tests de contrato `200/401/403/404/409` y de que el aviso no altera la respuesta

## 7. Baja de vehículo con órdenes abiertas (RN-16)

- [x] 7.1 Crear `app/modules/ordenes/verificacion.py` con `VerificadorOrdenesAbiertasSQL(session)` que cuente órdenes del vehículo unidas a `estado_orden` con `es_final = false`; tests de conteo, estados finales y vehículo sin órdenes
- [x] 7.2 Inyectar el verificador real en `dar_de_baja_vehiculo` desde `clientes/router.py`, retirar `SinOrdenesAbiertas` de producción y hacer obligatorio el parámetro; actualizar los tests de clientes que usaban el stub y agregar `409` de baja con orden abierta y `204` con órdenes sólo finales

## 8. Integración y documentación

- [x] 8.1 Ejecutar `pytest test/unit -q` y `pytest test/integration -q` completos, sin fallos, y registrar los conteos nuevos
- [x] 8.2 Ejecutar `openspec validate c-07-ordenes-de-trabajo --strict` y confirmar que el cambio es válido
- [x] 8.3 Actualizar `CHANGES.md` (C-07 en `[x]`, scope efectivo y conteos) y `test/unit/README.md` (totales, filas de los archivos nuevos y verificación del change), sin BOM
- [x] 8.4 Confirmar que no se generaron migraciones, seed ni disparadores, y que `app.main` monta las rutas de órdenes y estados

## Workflow follow-up

- Con el change archivado, ejecutar `/opsx-archive c-07-ordenes-de-trabajo` (sincroniza el delta `ordenes-de-trabajo` a la spec principal).
- Al iniciar C-08, reutilizar `OrdenTrabajoRepository`, la autorización de dueño y los schemas de detalle; C-09 debe importar todos los modelos antes de autogenerar la migración 001.
