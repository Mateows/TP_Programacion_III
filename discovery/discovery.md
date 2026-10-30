# Discovery — Taller mecánica: órdenes de trabajo, stock y acceso con FastAPI y PostgreSQL

**Fecha**: 2026-10-23
**Fuentes investigadas**: Ninguna externa (TP académico, no hay competidores)

## 1. Problema que resuelve

Un taller mecánico necesita una API para gestionar su operación diaria: alta de clientes y vehículos, apertura de órdenes de trabajo con ítems de repuestos, descuento de stock al terminar reparaciones, y consulta de estado por parte de los clientes. Todo con autenticación, autorización por roles y transacciones atómicas.

El usuario final es el taller (recepción, mecánicos, administrador) y los clientes que se registran por la web.

## 2. Usuarios / roles

- **Cliente**: se registra solo, consulta el estado de sus vehículos y sus órdenes.
- **Recepción**: da de alta clientes, vehículos y abre órdenes de trabajo.
- **Mecánico**: toma órdenes, las repara y las termina (descuenta stock de repuestos usados).
- **Administrador**: mantiene el catálogo de repuestos, repone el stock y administra al personal y sus roles.

## 3. Casos de uso

1. Como recepción, abro una orden de trabajo con ítems de repuestos para un vehículo.
2. Como mecánico, inicio y termino una orden; al terminar se descuenta el stock de cada repuesto usado.
3. Como administrador, gestiono repuestos, stock y roles de personal con vencimiento.
4. Como cliente, me registro y consulto el estado de mis vehículos y órdenes.

## 4. Competidores / soluciones existentes

Ninguno. Es un trabajo práctico académico (Materia: Programación III — Tecnicatura Universitaria en Programación). No busca competir ni implementarse en ninguna empresa; es un TP integrador de los capítulos 1 a 6. La solución actual del taller sería planillas, WhatsApp o papel, pero eso queda fuera del alcance.

## 5. Funcionalidades necesarias

- CRUD de clientes y vehículos.
- Apertura de órdenes de trabajo con ítems (composición: un ítem no existe sin su orden).
- Inicio y finalización de órdenes con descuento de stock en una sola transacción.
- Catálogo de estados de orden (PENDIENTE, EN_REPARACION, TERMINADA, CANCELADA).
- Autenticación con contraseñas hasheadas con bcrypt y token JWT en cookie HttpOnly.
- Autorización por roles consultados en la base en cada petición, distinguiendo 401 y 403.
- Historial inmutable de estados de orden, movimientos de stock y cambios de precio.
- Registro de cliente con usuario, rol CLIENTE y ficha de cliente en una sola transacción (Unit of Work).
- Límite de 5 intentos fallidos de login en 60 segundos (responde 429).

## 6. Funcionalidades opcionales

No se especifican funcionalidades opcionales en el alcance del TP. El aviso al cliente mediante BackgroundTasks está incluido como funcionalidad simulada dentro del MVP.

## 7. Reglas de negocio

18 reglas de negocio documentadas (RN-01 a RN-18), entre ellas:

- Unicidad de email de usuario, documento de cliente, patente y código de repuesto (sólo entre vigentes, sin borrado lógico).
- Auto-registro crea usuario + rol CLIENTE + ficha de cliente: o quedan las tres filas, o ninguna.
- Un usuario tiene a lo sumo una asignación abierta por rol.
- Los permisos se deciden con los roles vigentes en la base en cada petición.
- Un administrador no puede revocarse su propio rol ADMIN; el sistema nunca queda sin administradores vigentes.
- Mientras un usuario tenga cambio de contraseña pendiente, sólo puede usar rutas de salud y /auth.
- Al cambiar la contraseña, las sesiones emitidas antes dejan de valer.
- Después de 5 intentos fallidos con el mismo correo desde la misma IP en 60 segundos, el login responde 429.
- Una orden nace PENDIENTE con al menos un ítem y sin repuestos repetidos.
- Transiciones de estado estrictas: PENDIENTE → EN_REPARACION → TERMINADA, y PENDIENTE → CANCELADA.
- Terminar una orden descuenta el stock de cada ítem, deja un movimiento por salida y una línea de historial; si un repuesto no alcanza, no queda ninguna escritura.
- El stock de un repuesto sólo cambia a través de movimientos (alta, reposición, terminación).
- Tablas de sólo agregado (historial_estado_orden, movimiento_stock, historial_precio_repuesto) protegidas por disparador de base.

## 8. Integraciones

Ninguna integración externa obligatoria. El aviso al cliente se resuelve con BackgroundTasks dentro del mismo proceso (simulado con `await asyncio.sleep(0.5)` y un mensaje en el registro).

## 9. Restricciones

**Técnicas (obligatorias del TP):**

- Python 3.12+, FastAPI 0.111, SQLModel 0.0.24, SQLAlchemy 2.0 asíncrono.
- PostgreSQL 16, controlador asyncpg o psycopg 3 asíncrono.
- Alembic 1.13 con plantilla asíncrona para migraciones (no se usa `create_all`).
- pydantic-settings 2.0 para configuración desde variables de entorno o `.env`.
- bcrypt 4.0, PyJWT 2.8.
- Todos los handlers en `async def`; ninguna llamada bloqueante.
- Estructura por módulo funcional con 6 capas: Router → Service → UoW → Repository → Model.
- Dos migraciones: una autogenerada con `autogenerate`, una escrita a mano (disparador de sólo agregado).
- `seed.py` carga datos iniciales, incluido el catálogo de estados.
- Secrets solo en entorno (`.env` no versionado), sin valores por defecto en el código.
- Dinero en `NUMERIC` / `Decimal`, fechas en `timestamptz`.

**Organizacionales:**

- Materia: Programación III (Tecnicatura Universitaria en Programación).
- TP integrador de capítulos 1 a 6 (unidad 1 a 6: del objeto a la transacción).

## 10. Riesgos

- **Sólo agregado**: el disparador de base protege 3 tablas, pero si el rol de base de la aplicación tiene permisos de modificación, se pierde esa defensa en profundidad.
- **BackgroundTasks simulado**: si el proceso se reinicia, el aviso al cliente se pierde y no hay reintento (aceptado por el TP).
- **Nivel de aislamiento por defecto**: permite actualizaciones perdidas de stock entre órdenes concurrentes (tema del próximo capítulo, no de este TP).
- **Bcrypt fuera del bucle con semáforo**: si no se respeta, puede bloquear el event loop.

## 11. Preguntas abiertas

- ¿Preferencia de driver asíncrono: asyncpg o psycopg3?
- ¿Alguna regla de negocio adicional más allá de las 18 del TP?
- ¿Se considera necesaria alguna integración externa futura (pagos, notificaciones reales, etc.)?
