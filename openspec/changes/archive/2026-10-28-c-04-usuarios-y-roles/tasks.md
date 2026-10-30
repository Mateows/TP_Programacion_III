# Tasks

## 1. Base compartida de paginación y conteo

- [x] 1.1 Escribir primero los tests de `app/core/paginacion.py` en `test/unit/test_paginacion.py`: `Pagina.pages` con total 0, 1, múltiplo exacto y no múltiplo de `size`; `construir_pagina` conserva `page` y `size` y calcula `total` y `pages`; verificar que los tests fallan antes de crear el módulo (`pytest test/unit/test_paginacion.py -q`)
- [x] 1.2 Implementar `ParametrosPagina`, `Pagina[T]` y `construir_pagina` en `app/core/paginacion.py` y verificar `pytest test/unit/test_paginacion.py -q` en verde
- [x] 1.3 Escribir primero los tests de `BaseRepository.contar` en `test/unit/test_repository.py`: sin filtros, con filtros, y que la sentencia compilada contra el dialecto de PostgreSQL sea un `SELECT count(*)` sobre la tabla del modelo
- [x] 1.4 Implementar `contar()` en `BaseRepository` reutilizando `_sentencia()` y verificar `pytest test/unit/test_repository.py -q` en verde, incluidos los tests previos de C-02

## 2. Contratos y errores del módulo usuarios

- [x] 2.1 Escribir primero los tests de `app/modules/usuarios/schemas.py` en `test/unit/test_usuarios_schemas.py`: `AltaUsuarioRequest` acepta email, nombre y contraseña de 1 a 72 bytes, rechaza `roles`, `activo` y campos extra; `AsignacionRolRequest` acepta `ADMIN`, `RECEPCION` y `MECANICO`, rechaza `CLIENTE` y roles desconocidos, rechaza `vence_en` pasado y `vence_en` sin zona horaria, y acepta `vence_en` futuro con zona horaria; `UsuarioCreadoResponse` no expone `password_hash`
- [x] 2.2 Implementar los schemas con Pydantic V2, `extra="forbid"` y `X | None`, reutilizando `PasswordValidadaMixin` y `validar_password` de `app.modules.auth.schemas`, hasta que `pytest test/unit/test_usuarios_schemas.py -q` pase
- [x] 2.3 Escribir primero los tests de `app/modules/usuarios/errors.py` en `test/unit/test_usuarios_errors.py`: cada error de dominio es distinguible y su mensaje no contiene nombres de tabla, columna ni restricción
- [x] 2.4 Implementar `errors.py` hasta que `pytest test/unit/test_usuarios_errors.py -q` pase

## 3. Consultas de administración de roles y eventos

- [x] 3.1 Escribir primero los tests de `AsignacionRolRepository` en `test/unit/test_usuarios_repository.py`: `buscar_abierta` filtra por usuario, rol y `revocada_en IS NULL`; `listar_historial` ordena por `desde DESC, id DESC` e incluye revocadas y vencidas; `contar_admin_vigentes` excluye la asignación indicada, descarta vencidas y cuentas inactivas y une con `usuario`, verificando el SQL compilado
- [x] 3.2 Implementar los tres métodos en `app/modules/auth/repository.py` hasta que `pytest test/unit/test_usuarios_repository.py -q` pase
- [x] 3.3 Escribir primero los tests de `EventoSeguridadRepository.listar_paginado` y su conteo: orden `cuando DESC, id DESC`, `limit` y `offset` aplicados, y `contar()` sin filtros
- [x] 3.4 Implementar ambos métodos y verificar `pytest test/unit/test_usuarios_repository.py -q` en verde
- [x] 3.5 Verificar que ningún repositorio nuevo llama `commit()` (los tests de `test_auth_repository.py` y `test_unit_of_work.py` siguen verdes)

## 4. Servicio: alta de personal

- [x] 4.1 Escribir primero los tests de `crear_usuario_personal` en `test/unit/test_usuarios_service_alta.py`: alta exitosa deja `activo=True`, `debe_cambiar_password=True`, `password_cambiada_en=None` y sin asignaciones; el hash se calcula antes de abrir la unidad de trabajo; se registra el evento `ALTA_USUARIO_PERSONAL` con actor `USUARIO:{id}`; un correo duplicado produce `CorreoYaRegistrado` sin confirmar; un conflicto en una escritura posterior se propaga como `ConflictoDeIntegridad` y no como `CorreoYaRegistrado`
- [x] 4.2 Implementar `crear_usuario_personal` hasta que `pytest test/unit/test_usuarios_service_alta.py -q` pase
- [x] 4.3 Verificar que la respuesta del servicio no contiene el hash y que no emite token ni cookie

## 5. Servicio: asignación, reasignación y revocación

- [x] 5.1 Escribir primero los tests de `asignar_rol` en `test/unit/test_usuarios_service_roles.py`: sin vencimiento y con vencimiento futuro crean la asignación con `desde` y `otorgada_por` fijados en Python; un rol abierto y vigente produce `RolYaAsignado`; un rol abierto y vencido se revoca con `flush()` **antes** del `INSERT` de la nueva (verificar el orden de sentencias); un usuario inexistente produce `UsuarioNoEncontrado`; se registra el evento `ASIGNACION_ROL`
- [x] 5.2 Implementar `asignar_rol` hasta que `pytest test/unit/test_usuarios_service_roles.py -q` pase
- [x] 5.3 Escribir primero los tests de `revocar_rol`: revocación exitosa escribe `revocada_en` y conserva la fila; sin asignación abierta y segunda revocación producen `AsignacionNoEncontrada`; la autoprotección produce `RevocacionPropiaNoPermitida` aun con otro administrador vigente; el último administrador vigente produce `UltimoAdministrador`; con otro administrador vigente la revocación se acepta; un administrador inactivo no cuenta como vigente; revocar un rol propio distinto de `ADMIN` se acepta; se registra el evento `REVOCACION_ROL`
- [x] 5.4 Implementar `revocar_rol` hasta que `pytest test/unit/test_usuarios_service_roles.py -q` pase
- [x] 5.5 Verificar que una operación rechazada no registra evento ni confirma la unidad de trabajo

## 6. Servicio: consulta de roles y de eventos

- [x] 6.1 Escribir primero los tests de `consultar_roles` en `test/unit/test_usuarios_service_consultas.py`: devuelve el historial completo ordenado, una lista vacía cuando no hay asignaciones, y `UsuarioNoEncontrado` cuando el usuario no existe
- [x] 6.2 Implementar `consultar_roles` hasta que `pytest test/unit/test_usuarios_service_consultas.py -q` pase
- [x] 6.3 Escribir primero los tests de `consultar_eventos`: primera página con 20 elementos por defecto, `pages` calculado sobre el total, una página posterior a la última produce `PaginaFueraDeRango`, y los límites de `size` se respetan
- [x] 6.4 Implementar `consultar_eventos` hasta que `pytest test/unit/test_usuarios_service_consultas.py -q` pase

## 7. Router y montaje

- [x] 7.1 Escribir primero los tests de integración en `test/integration/test_usuarios_router.py` con `ASGITransport` y `dependency_overrides`: `POST /usuarios` responde `201`, `409`, `422` y `403` según el caso; `GET /usuarios/{id}/roles` responde `200` y `404`; `POST /usuarios/{id}/roles` responde `201`, `409`, `422` y `404`; `DELETE /usuarios/{id}/roles/{rol}` responde `200`, `404` y `409`; `GET /eventos` responde `200`, `422` y `403`; las cinco rutas responden `401` sin sesión y `403` con cambio de contraseña pendiente; el alta no devuelve `password_hash` ni `Set-Cookie`
- [x] 7.2 Implementar `app/modules/usuarios/router.py` con la traducción de errores de dominio a `404`, `409` y `422`, hasta que `pytest test/integration/test_usuarios_router.py -q` pase
- [x] 7.3 Montar los dos routers en `app/main.py` bajo `router_protegido` con prefijos `/usuarios` y `/eventos`, y verificar que las rutas aparecen en `app.openapi()` y que `pytest test/integration/test_auth_router.py -q` sigue verde

## 8. Integración y cierre

- [x] 8.1 Ejecutar `pytest test/unit test/integration -q` y verificar que no hay fallos, anotando los conteos reales
- [x] 8.2 Actualizar `test/unit/README.md` con los archivos nuevos y los conteos reales de la suite
- [x] 8.3 Actualizar `CHANGES.md`: C-04 en `[x]` con las rutas entregadas y la verificación real
- [x] 8.4 Ejecutar `openspec validate c-04-usuarios-y-roles --strict` y `openspec instructions apply --change c-04-usuarios-y-roles --json`, y verificar `state=all_done` con todas las tareas completas

## Workflow follow-up

- Revisar el change con el usuario antes de archivarlo.
- Archivar con `/opsx:archive c-04-usuarios-y-roles` una vez aprobado.
