# Tasks

## 1. Base de pruebas y mixin de timestamps

- [x] 1.1 Agregar `pytest==9.1.1` a `requirements.txt` bajo un comentario de pruebas y verificar que `python -m pytest --version` responde con la versión instalada
- [x] 1.2 RED: crear `test/unit/test_timestamps.py` que afirme que `TimestampMixin` expone `creado_en` y `actualizado_en` como `DateTime(timezone=True)`, no nulos y con valor por defecto de servidor; verificar que el test falla porque el mixin no existe
- [x] 1.3 GREEN: implementar `TimestampMixin` en `app/core/repository.py` y verificar que `python -m pytest test/unit/test_timestamps.py -q` pasa
- [x] 1.4 TRIANGULATE: agregar al test un caso que aplique el mixin a un modelo de prueba y compruebe que las dos columnas aparecen en su metadata con zona horaria; verificar que pasa

## 2. Repositorio base

- [x] 2.1 RED: crear `test/unit/test_repository.py` con una sesión falsa que registre llamadas y afirmar que `BaseRepository` agrega la entidad, hace `flush()` y nunca `commit()`; verificar que el test falla porque el repositorio no existe
- [x] 2.2 GREEN: implementar `BaseRepository[T]` con lectura por identificador, listado con filtros y alta, usando `select()` y `session.scalars()`; verificar que el test de 2.1 pasa
- [x] 2.3 TRIANGULATE: agregar un caso con dos filtros combinados y un límite, y comprobar que la sentencia compilada para PostgreSQL contiene ambos filtros y el límite; verificar que pasa
- [x] 2.4 RED: agregar tests que afirmen que `SoftDeleteRepository` excluye por defecto las filas con `borrado_en` no nulo, las incluye cuando se pide explícitamente y que `soft_delete` solo escribe la marca sin borrar la fila; verificar que fallan
- [x] 2.5 GREEN: implementar `SoftDeleteRepository[T]` con filtro por defecto, `get_by_id_including_deleted` y `soft_delete` idempotente; verificar que los tests de 2.4 pasan
- [x] 2.6 TRIANGULATE: agregar un caso que aplique opciones de carga declaradas por un repositorio concreto y compruebe que la sentencia las incluye; verificar que pasa

## 3. Unidad de trabajo

- [x] 3.1 RED: crear `test/unit/test_unit_of_work.py` con una sesión falsa y afirmar que una unidad de trabajo que recibe la sesión confirma al salir sin excepción y no la cierra; verificar que el test falla
- [x] 3.2 GREEN: implementar `UnitOfWork` base como gestor de contexto async con `commit()` al salir y sin cerrar la sesión recibida; verificar que el test de 3.1 pasa
- [x] 3.3 RED: agregar un test que afirme que ante una excepción la unidad de trabajo revierte, no confirma y propaga la excepción; verificar que falla
- [x] 3.4 GREEN: implementar la rama de excepción con `rollback()` y propagación; verificar que el test de 3.3 pasa
- [x] 3.5 RED: agregar tests que afirmen que un `IntegrityError` en `flush()` o en `commit()` se traduce a `ConflictoDeIntegridad` sin incluir el mensaje original del motor; verificar que fallan
- [x] 3.6 GREEN: implementar `ConflictoDeIntegridad` y la traducción en la frontera de persistencia, registrando el detalle original solo en el log; verificar que los tests de 3.5 pasan
- [x] 3.7 TRIANGULATE: agregar un caso de sesión creada por la propia unidad de trabajo y comprobar que sí se cierra al salir; verificar que pasa

## 4. Modelos de usuarios y roles

- [x] 4.1 RED: crear `test/unit/test_usuarios_models.py` y afirmar que `Usuario` tiene tabla `usuario`, PK entera, `email` único, `password_hash` obligatorio, `activo` y `debe_cambiar_password` booleanos con valor por defecto, y `password_cambiada_en` con zona horaria y nullable; verificar que el test falla
- [x] 4.2 GREEN: implementar `Usuario` en `app/modules/usuarios/models.py`; verificar que el test de 4.1 pasa
- [x] 4.3 RED: agregar tests que afirmen que `AsignacionRol` tiene CHECK con los cuatro roles, índice único parcial `(usuario_id, rol)` limitado a `revocada_en IS NULL`, FK a usuario y FK indexada de `otorgada_por`; verificar que fallan
- [x] 4.4 GREEN: implementar `AsignacionRol` con sus `__table_args__`; verificar que los tests de 4.3 pasan
- [x] 4.5 RED: agregar tests que afirmen que `IntentoAcceso` tiene índice compuesto `(email, ip, cuando)` y que `EventoSeguridad` guarda `actor` como texto sin FK a usuario; verificar que fallan
- [x] 4.6 GREEN: implementar `IntentoAcceso` y `EventoSeguridad`; verificar que los tests de 4.5 pasan
- [x] 4.7 TRIANGULATE: agregar un caso que compruebe que el metadata de los cuatro modelos registra exactamente las tablas `usuario`, `asignacion_rol`, `intento_acceso` y `evento_seguridad`, y que cada FK tiene índice; verificar que pasa

## 5. Catálogo de estados de orden

- [x] 5.1 RED: crear `test/unit/test_estado_orden_model.py` y afirmar que `EstadoOrden` usa tabla `estado_orden`, PK textual `codigo`, `descripcion` obligatoria, `posicion` entera única y `es_final` booleano; verificar que el test falla
- [x] 5.2 GREEN: implementar `EstadoOrden` en `app/modules/ordenes/models.py`; verificar que el test de 5.1 pasa
- [x] 5.3 TRIANGULATE: agregar un caso que compruebe que el modelo no tiene columna `id` ni marcas temporales, y que `codigo` es la única PK; verificar que pasa

## 6. Verificación integrada

- [x] 6.1 Agregar `test/unit/test_metadata_global.py` que importe los modelos y verifique que el metadata global contiene las cinco tablas, que ninguna FK carece de índice y que las columnas de fecha son con zona horaria; verificar que pasa
- [x] 6.2 Verificar que no existe ninguna llamada a `create_all` en `app/`, `seed.py` ni `migrations/`, y que `migrations/versions/` no contiene revisiones; documentar el resultado en la salida de la tarea
- [x] 6.3 Ejecutar `python -m pytest test/unit -q` y verificar que toda la suite pasa
- [x] 6.4 Ejecutar `openspec validate c-02-core-models --strict` y verificar que el change no reporta errores

## Workflow follow-up

- Revisar los artefactos y, cuando el usuario lo pida, ejecutar `/opsx-apply c-02-core-models`.
- C-09 consume estos modelos para autogenerar la Migración 001 y debe revisar que el autogenerate incluya PK textual, índices únicos parciales, CHECK e índices de FK.
- Archivar el change solo después de la revisión del usuario; no ejecutar `git commit` ni `git push`.
