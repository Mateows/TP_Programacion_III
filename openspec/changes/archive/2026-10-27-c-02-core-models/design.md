# Design

## Context

Ver `proposal.md` — Why. El punto de partida es C-01 ya archivado: `app/core/config.py` expone `Settings` con `DATABASE_URL` async, `app/core/database.py` crea el motor y la fábrica de sesiones en el lifespan (`expire_on_commit=False`) y entrega sesiones con `get_session`, y `app/core/security.py` ya resuelve bcrypt y JWT. `migrations/` está configurado con plantilla asíncrona y `target_metadata` vacío; no existe ninguna revisión.

Restricciones que condicionan el diseño:

- Stack fijado por el TP: SQLModel 0.0.24 sobre SQLAlchemy 2.0 async, PostgreSQL 16, `Decimal` para dinero y `timestamptz` para fechas.
- La KB define los atributos exactos de cada tabla (`knowledge-base/04_modelo_de_datos.md`); este change no agrega columnas de dominio que la KB no liste.
- Los repositorios solo hacen `flush()`; el `commit()` pertenece a la unidad de trabajo (`knowledge-base/08_arquitectura_propuesta.md`).
- No se generan migraciones ni se usa `create_all`: la Migración 001 se autogenera en C-09.

## Goals / Non-Goals

**Goals:**

- Dejar un contrato único de persistencia (repositorio base, repositorio con borrado lógico, unidad de trabajo) que C-03 a C-08 consuman sin reimplementar transacciones.
- Definir las tablas de usuarios/roles/auditoría y el catálogo de estados con las restricciones que la KB exige (CHECK, índices únicos parciales, índices de FK).
- Fijar convenciones de carga anticipada y de traducción de errores de integridad antes de que existan los módulos de dominio.

**Non-Goals:**

- Endpoints, routers, schemas de request/response y servicios: pertenecen a C-03 en adelante.
- Repositorios concretos de usuarios y de órdenes: solo se define la base genérica; los concretos llegan con su módulo.
- Migraciones, `seed.py` y validación del esquema: C-09.
- Columnas de negocio de clientes, vehículos, repuestos y órdenes: C-05, C-06 y C-07.

## Decisions

### D1 — Modelos de tabla con SQLModel y restricciones en `__table_args__`

Cada entidad se declara como clase `table=True` de SQLModel con `__tablename__` explícito en singular, respetando los nombres de la KB (`usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`, `estado_orden`). Los atributos usan anotaciones tipadas y `Field` para longitud, nulabilidad y claves foráneas.

SQLModel no expresa índices únicos parciales ni CHECK con `Field`, así que se declaran en `__table_args__` con `Index(..., unique=True, postgresql_where=...)` y `CheckConstraint`. Alternativa considerada: SQLAlchemy declarativo puro, que expresa todo con naturalidad; se descarta porque el TP exige SQLModel como capa de modelos.

Consecuencia: el autogenerate de C-09 debe verse obligado a emitir esos índices y CHECK; se verifica allí, no en este change.

### D2 — Identificadores: enteros para entidades transaccionales, texto para el catálogo

`usuario`, `asignacion_rol`, `intento_acceso` y `evento_seguridad` usan `id` entero autoincremental como PK. `estado_orden` usa `codigo` textual como PK, tal como exige la KB y porque el estado se referencia por nombre en las reglas de transición.

Alternativa considerada: dar a `estado_orden` un `id` numérico y un `codigo` único; se descarta porque la KB y la FK de `orden_trabajo.estado` apuntan a `estado_orden.codigo`.

### D3 — Marcas temporales siempre con zona horaria

Todas las columnas de fecha se mapean con `DateTime(timezone=True)` (equivalente a `timestamptz`). Los valores por defecto se resuelven en la base con `func.now()` para no depender del reloj del proceso; en Python se usa `datetime.now(UTC)` cuando hay que comparar o calcular.

Se define un `TimestampMixin` reutilizable con `creado_en` y `actualizado_en` (segundo con `onupdate=func.now()`). Las tablas de C-02 no lo aplican: la KB les asigna nombres de dominio (`cuando`, `desde`, `vence_en`, `revocada_en`, `password_cambiada_en`). El mixin queda disponible para las entidades de C-05 a C-07 que la KB defina con esas columnas.

Alternativa considerada: usar `datetime.utcnow()` como default de Python; se descarta porque devuelve fechas sin zona y rompe la comparación con `timestamptz`.

### D4 — Restricciones de rol en la base, no en el servicio

`asignacion_rol.rol` lleva un `CheckConstraint` con los cuatro valores admitidos y un índice único parcial `(usuario_id, rol) WHERE revocada_en IS NULL`. Así, la regla “a lo sumo una asignación abierta por rol” (RN-03) se cumple aunque el servicio tenga un error, y el rechazo llega como error de integridad traducido.

`otorgada_por` es una FK nullable a `usuario.id`: la KB permite que la asignación la haya hecho el sistema o un usuario que ya no esté activo. Se indexa toda FK porque PostgreSQL no crea ese índice solo.

Alternativa considerada: validar la unicidad solo en el servicio; se descarta porque dos peticiones concurrentes podrían abrir dos asignaciones del mismo rol.

### D5 — Auditoría sin FK a usuario en intentos de acceso

`intento_acceso` guarda `email` e `ip` como texto y no referencia `usuario.id`: un intento puede corresponder a un correo inexistente y el registro debe sobrevivir a cualquier cambio de cuenta. Se crea un índice compuesto `(email, ip, cuando)` para que el conteo de RN-08 se resuelva sin recorrer la tabla.

`evento_seguridad.actor` es texto por la misma razón: admite `SISTEMA` y usuarios sin exigir una fila en `usuario`.

### D6 — Repositorio base genérico con `flush()` y sin `commit()`

`BaseRepository[T]` recibe el tipo de modelo y una `AsyncSession`, y ofrece operaciones async de lectura por identificador, listado y alta. Toda escritura termina en `session.flush()`; el repositorio nunca confirma ni cierra la sesión.

La implementación usa `select()` de SQLAlchemy 2.0 y `session.scalars()` en lugar de la API de sesión de SQLModel, porque el tipado genérico de SQLModel no cubre consultas dinámicas. Alternativa considerada: un repositorio por entidad sin base común; se descarta porque duplicaría la lógica de paginación, filtros y carga anticipada en cinco módulos.

### D7 — Carga anticipada declarada por repositorio y carga perezosa bloqueada

Cada repositorio concreto declara una tupla de opciones de carga (`selectinload` para colecciones, `joinedload` para relaciones muchos-a-uno) y el repositorio base las aplica a todas sus consultas. Los modelos declaran sus relaciones con `lazy="raise"`, de modo que acceder a una relación no cargada falla de forma explícita en desarrollo en lugar de disparar N+1 en producción.

Alternativa considerada: `lazy="selectin"` global en los modelos; se descarta porque carga relaciones que muchos casos de uso no necesitan y oculta el costo de las consultas.

### D8 — Borrado lógico con filtro por defecto y consulta explícita

`SoftDeleteRepository[T]` extiende el repositorio base y asume una columna `borrado_en` nullable. Sus lecturas habituales agregan `borrado_en IS NULL`; `get_by_id_including_deleted` omite ese filtro; `soft_delete` escribe la fecha solo si la fila no estaba ya dada de baja. No existe borrado físico en este repositorio.

El filtro se implementa en el repositorio y no en el modelo, para que las entidades sin borrado lógico no carguen con una condición que no les corresponde. Alternativa considerada: un `Event` de SQLAlchemy que filtre todas las consultas; se descarta por ser magia difícil de auditar y por afectar también a las consultas que sí deben ver las filas dadas de baja.

### D9 — Unidad de trabajo como gestor de contexto que confirma o revierte

`UnitOfWork` base recibe una `AsyncSession` y un indicador de si la creó. En `__aenter__` no abre transacción explícita: la primera operación la inicia. En `__aexit__`, si no hubo excepción hace `commit()`; si hubo, hace `rollback()` y propaga la excepción. Solo cierra la sesión cuando la creó él.

Los servicios no construyen su propia unidad de trabajo: la reciben del router. Las unidades concretas de cada módulo heredan de esta base y exponen sus repositorios como atributos. Alternativa considerada: una única unidad de trabajo global con todos los repositorios; se descarta porque acopla módulos que deben poder evolucionar por separado.

### D10 — Errores de integridad traducidos en la frontera de persistencia

`ConflictoDeIntegridad` es una excepción de dominio sin detalles del esquema. Se lanza al traducir un `IntegrityError` en dos puntos: el `flush()` de los repositorios y el `commit()` de la unidad de trabajo. El mensaje original se registra en el log, nunca se devuelve al cliente (RN-18).

Alternativa considerada: dejar que `IntegrityError` suba hasta el manejador global de FastAPI; se descarta porque obligaría a cada módulo a conocer los nombres de las restricciones y a repetir el mapeo.

### D11 — Sin migraciones en este change

Los modelos se declaran pero no se aplican a ninguna base. `migrations/env.py` sigue con `target_metadata` vacío; C-09 lo conecta con el metadata de los modelos, autogenera la Migración 001 y valida `upgrade`/`downgrade`. Esto evita que C-02 dependa de una base viva y mantiene una sola migración inicial coherente con todas las tablas.

## Risks / Trade-offs

- **Índices únicos parciales y CHECK no visibles para SQLModel** → se declaran en `__table_args__` y se verifica en C-09 que el autogenerate los emita; si no los emite, se corrigen a mano en la Migración 001 antes de aplicarla.
- **`lazy="raise"` rompe serializaciones si falta una opción de carga** → cada repositorio concreto declara sus opciones y las pruebas de C-05 a C-07 cubren los listados; el error es explícito y aparece en desarrollo, no como N+1 silencioso.
- **Genéricos de SQLModel limitados** → el repositorio base usa SQLAlchemy `select` y `session.scalars`, y los repositorios concretos solo aportan modelo, filtros y opciones de carga.
- **`DateTime(timezone=True)` con asyncpg** → asyncpg devuelve `datetime` con zona; se normaliza a UTC al comparar y se evita `datetime.utcnow()`.
- **Sin migraciones hasta C-09, el esquema no es verificable por base** → la validación de C-02 se limita a importar los modelos, inspeccionar el metadata (tablas, columnas, índices, CHECK) y probar repositorio/UoW con una base de prueba creada por migración en C-09.
- **`ConflictoDeIntegridad` puede perder el detalle útil para depurar** → el mensaje original se registra en el log con el nombre de la restricción antes de traducir.

## Migration Plan

No hay migración en C-02. Al aplicar el change solo se agregan archivos de código; no se modifica el esquema ni la configuración de C-01. Revertir consiste en eliminar los archivos nuevos (`app/core/repository.py`, `app/core/unit_of_work.py`, `app/modules/usuarios/models.py`, `app/modules/ordenes/models.py`), sin tocar la base.

C-09 toma estos modelos como entrada para la Migración 001 y debe revisar que el autogenerate incluya: PK de `estado_orden.codigo`, índice único parcial de `asignacion_rol`, CHECK de rol, índice compuesto de `intento_acceso` e índices de todas las FK.

## Open Questions

Ninguna que afecte specs, enfoque o desglose de tareas. La longitud de los campos de texto (`email`, `nombre`, `ip`, `accion`) no está fijada por la KB; se eligen valores conservadores y ajustarlos no cambia el comportamiento observable.
