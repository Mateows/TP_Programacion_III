# Tasks

## 1. Modelos y restricciones de integridad

- [x] 1.1 Crear `app/modules/clientes/models.py` con `Cliente` (`__tablename__ = "cliente"`): `id` PK, `usuario_id` FK a `usuario.id` nullable e indexada, `nombre`, `documento` único, `telefono` nullable. Verificar con un test unitario de metadata que la tabla se registra con esas columnas y que `usuario_id` es `UNIQUE`.
- [x] 1.2 Agregar `Vehiculo` (`__tablename__ = "vehiculo"`): `id` PK, `cliente_id` FK a `cliente.id` not null e indexada, `patente`, `marca`, `modelo`, `anio`, `borrado_en` nullable. Verificar con un test unitario de metadata que ambas FKs tienen índice explícito.
- [x] 1.3 Declarar el índice único parcial `ix_vehiculo_patente_vigente` sobre `patente` con `postgresql_where=text("borrado_en IS NULL")` y el `CHECK anio BETWEEN 1950 AND 2100`. Verificar con un test que inspecciona `Vehiculo.__table__` y comprueba el `unique`, el `where` y el nombre del CHECK.

## 2. Repositorios

- [x] 2.1 Implementar `ClienteRepository(BaseRepository[Cliente])` con `buscar_por_documento(documento)` y `buscar_por_usuario(usuario_id)` en `app/modules/clientes/repository.py`; verificar con tests unitarios que ambas consultas filtran por la columna correcta.
- [x] 2.2 Implementar `VehiculoRepository(SoftDeleteRepository[Vehiculo])` con `listar_vigentes_por_cliente(cliente_id)` y `buscar_vigente_por_patente(patente)`; verificar con tests que `listar_vigentes_por_cliente` no devuelve vehículos con `borrado_en` y que `buscar_vigente_por_patente` ignora los dados de baja.
- [x] 2.3 Verificar con un test unitario que `soft_delete` sobre un vehículo ya dado de baja conserva su `borrado_en` original y no vuelve a escribir la marca.

## 3. Esquemas, errores y traducción HTTP

- [x] 3.1 Crear `app/modules/clientes/schemas.py` con `AltaClienteRequest`, `AltaVehiculoRequest`, `ClienteResponse` y `VehiculoResponse`, todos con `extra="forbid"`; normalizar `patente` (`strip` + `upper`) en un `field_validator`. Verificar con tests de contrato que un campo extra da error, que la patente queda normalizada y que el año se acepta en 1950/2100.
- [x] 3.2 Crear `app/modules/clientes/errors.py` con `ErrorClientes` como base y `ClienteNoEncontrado`, `DocumentoYaRegistrado`, `VehiculoNoEncontrado`, `PatenteYaRegistrada`, `VehiculoConOrdenesAbiertas`, `SinFichaDeCliente` y `AnioFueraDeRango`, con mensajes que no nombren tablas ni constraints. Verificar con un test que ningún mensaje contiene `ix_` ni `ck_`.

## 4. Alta y consulta de clientes

- [x] 4.1 Implementar `crear_cliente(uow, datos, actor)` en `app/modules/clientes/service.py`: abre el `UnitOfWork`, traduce `ConflictoDeIntegridad` del `add` a `DocumentoYaRegistrado` y confirma al salir. Verificar con tests unitarios de alta exitosa, documento repetido (sin dejar fila) y conflicto posterior que se propaga sin traducir.
- [x] 4.2 Implementar `consultar_cliente(uow, cliente_id)` que devuelve la ficha con sus vehículos vigentes en dos consultas y lanza `ClienteNoEncontrado` si no existe. Verificar con tests unitarios de cliente con vehículos, sin vehículos, con vehículos dados de baja excluidos e inexistente.
- [x] 4.3 Crear `app/modules/clientes/router.py` con `POST /clientes` (`201`) y `GET /clientes/{id}` (`200`), protegidos con `requiere_rol("RECEPCION", "ADMIN")` y con `_traducir` de 404/409/422/403. Verificar con tests de integración: 201, 409 documento, 422 cuerpo inválido, 404, 403 sin rol y 401 sin sesión.
- [x] 4.4 Montar `router_clientes` con prefijo `/clientes` en `router_protegido` de `app/main.py`. Verificar con un test de integración que `POST /clientes` responde desde la app montada y que sin sesión da `401`.

## 5. Alta de vehículos

- [x] 5.1 Implementar `crear_vehiculo(uow, cliente_id, datos, actor)`: verifica que el cliente exista (`ClienteNoEncontrado`), normaliza la patente, traduce el conflicto del índice parcial a `PatenteYaRegistrada` y valida el año en el contrato, revalidándolo en el servicio (`AnioFueraDeRango`) como defensa en profundidad. Verificar con tests unitarios de alta exitosa, cliente inexistente, patente vigente repetida, patente liberada por una baja y año fuera de rango.
- [x] 5.2 Exponer `POST /clientes/{id}/vehiculos` (`201`) con `requiere_rol("RECEPCION", "ADMIN")`. Verificar con tests de integración: 201, 404 cliente inexistente, 409 patente repetida, 422 año fuera de rango y 422 campo no declarado.
- [x] 5.3 Verificar con un test de integración que una patente con distinta capitalización o con espacios circundantes respecto de una vigente responde `409`.

## 6. Baja lógica de vehículos

- [x] 6.1 Crear `app/modules/clientes/verificacion.py` con el protocolo `VerificadorOrdenesAbiertas` y la implementación por defecto que devuelve `0`, documentando que C-07 la sustituye por la consulta a `orden_trabajo`. Verificar con un test unitario que la implementación por defecto devuelve `0`.
- [x] 6.2 Implementar `dar_de_baja_vehiculo(uow, vehiculo_id, actor, verificador)`: obtiene el vehículo vigente (`VehiculoNoEncontrado` si no existe o ya está de baja), consulta el verificador y lanza `VehiculoConOrdenesAbiertas` cuando el conteo es mayor que `0`, y aplica `soft_delete`. Verificar con tests unitarios de baja exitosa, 404 inexistente, 404 repetida, y 409 con un verificador doble que devuelve `1`.
- [x] 6.3 Exponer `DELETE /vehiculos/{id}` con `204`, `requiere_rol("RECEPCION", "ADMIN")` y retorno `None`. Verificar con tests de integración: 204 con fila conservada, 404 inexistente, 404 repetida, 403 sin rol y que el vehículo dado de baja desaparece de `GET /clientes/{id}`.

## 7. Vehículos propios del cliente

- [x] 7.1 Implementar `listar_mis_vehiculos(uow, usuario_id)` que resuelve la ficha por `usuario_id`, lanza `SinFichaDeCliente` si no existe y devuelve sólo los vehículos vigentes de esa ficha. Verificar con tests unitarios de cliente con vehículos propios, cliente sin vehículos, cuenta sin ficha y exclusión de vehículos ajenos.
- [x] 7.2 Exponer `GET /mis-vehiculos` con `CurrentUser` (sin `requiere_rol`), traduciendo `SinFichaDeCliente` a `403`. Verificar con tests de integración: 200 sólo con vehículos propios, 200 lista vacía, 403 cuenta sin ficha y 401 sin sesión.

## 8. Auto-registro con ficha de cliente (RN-02)

- [x] 8.1 Extender `RegistroRequest` en `app/modules/auth/schemas.py` con `documento` obligatorio y `telefono` opcional, conservando `extra="forbid"`. Verificar con tests de contrato que el registro sin documento da `422` y que el teléfono ausente se acepta.
- [x] 8.2 Extender `registrar_cuenta` para crear la ficha de cliente dentro del mismo `UnitOfWork`, traduciendo el conflicto del `add` de la ficha a `DocumentoYaRegistrado` y sin traducir conflictos de otros puntos. Verificar con tests unitarios: registro exitoso crea las tres filas, documento repetido revierte las tres, y fallo en la ficha revierte cuenta y rol.
- [x] 8.3 Traducir `DocumentoYaRegistrado` a `409` en `app/modules/auth/router.py` y actualizar los tests de `test/integration/test_auth_router.py` al contrato nuevo. Verificar que la suite de integración de auth queda verde con los casos: 201 con ficha, 409 correo, 409 documento y 422 sin documento.

## 9. Integración y documentación

- [x] 9.1 Ejecutar `pytest test/unit -q` y `pytest test/integration -q` y verificar que ambas suites pasan completas.
- [x] 9.2 Ejecutar `openspec validate c-05-clientes-y-vehiculos --strict` y verificar que el change es válido.
- [x] 9.3 Actualizar `CHANGES.md` marcando C-05 y registrando rutas entregadas y conteos reales de tests, y actualizar `test/unit/README.md` si su índice de archivos lo requiere; verificar que ambos archivos siguen en UTF-8 sin BOM.
- [x] 9.4 Verificar manualmente que `app/main.py` monta `/clientes`, `/vehiculos` y `/mis-vehiculos` en `router_protegido` y que ninguna ruta pública quedó expuesta sin sesión.

## Workflow follow-up

- Revisar los artefactos y ejecutar el flujo de apply con TDD estricto.
- Archivar el change con sincronización de delta specs cuando la implementación esté verificada.
