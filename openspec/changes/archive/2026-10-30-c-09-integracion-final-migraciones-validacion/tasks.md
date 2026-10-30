# Tasks

## 1. Migraciones de Base de Datos y Ciclo de Idempotencia

- [x] 1.1 Configurar `migrations/env.py`: importar `SQLModel`, los 4 módulos de modelos (`usuarios`, `clientes`, `repuestos`, `ordenes`) y asignar `target_metadata = SQLModel.metadata`
- [x] 1.2 Generar la Migración 001 con `alembic revision --autogenerate -m "0001_inicial"`, revisando que incluya las 13 tablas, claves foráneas con índices explícitos, restricciones CHECK e índices únicos parciales con `postgresql_where`
- [x] 1.3 Crear la Migración 002 con `alembic revision -m "0002_solo_agregado"` e implementar la función PL/pgSQL y los disparadores `BEFORE UPDATE OR DELETE` sobre `historial_estado_orden`, `movimiento_stock` e `historial_precio_repuesto` (RN-15), con su correspondiente `downgrade()`
- [x] 1.4 Ejecutar `alembic upgrade head` sobre la base de datos limpia de PostgreSQL y verificar la creación completa de las tablas, índices y triggers
- [x] 1.5 Ejecutar `alembic downgrade base` y verificar que todo el esquema y funciones sean eliminados sin errores
- [x] 1.6 Ejecutar nuevamente `alembic upgrade head` y verificar la idempotencia total del esquema

## 2. Endpoints de Salud del Sistema

- [x] 2.1 Implementar `app/modules/health/router.py` con `GET /health/live` (retorna `200` sin interactuar con la BD) y `GET /health/ready` (ejecuta `SELECT 1` asíncrono, respondiendo `200` ante éxito o `503` ante falla de conexión)
- [x] 2.2 Montar el router de health en `router_abierto` dentro de `app/main.py`
- [x] 2.3 Crear pruebas unitarias y de integración para ambos endpoints en `test/unit/test_health.py` y `test/integration/test_health_router.py`

## 3. Población Inicial de Datos (`seed.py`)

- [x] 3.1 Implementar la rutina de limpieza previa idempotente (`TRUNCATE TABLE ... CASCADE`) compatible con los disparadores de sólo agregado
- [x] 3.2 Implementar la carga del catálogo `estado_orden` (PENDIENTE, EN_REPARACION, TERMINADA, CANCELADA)
- [x] 3.3 Implementar la carga de usuarios y asignación de roles vigentes (admin, admin2, recepcion, mecanico, mecanico2, cliente, nuevo con cambio obligatorio) con contraseñas hasheadas con bcrypt
- [x] 3.4 Implementar la carga de clientes y vehículos (Laura con 2 vehículos, Jorge sin usuario con 1 vehículo)
- [x] 3.5 Implementar la carga de repuestos con su stock inicial registrado en `movimiento_stock`
- [x] 3.6 Implementar la carga del historial de precios (filtro de aceite con incremento de precio)
- [x] 3.7 Implementar la carga de órdenes de trabajo (Orden 1 PENDIENTE, Orden 2 EN_REPARACION con 4 bujías asignada a mecánico) con sus ítems e historial inicial
- [x] 3.8 Implementar la carga del evento de seguridad inicial con actor `SISTEMA`
- [x] 3.9 Ejecutar `python seed.py` y verificar la correcta inserción de todos los registros en PostgreSQL

## 4. Pruebas de Integración y Validación de Casos (C-01 a C-19)

- [x] 4.1 Crear `test/solo_agregado.sql` con los 6 intentos de modificación (UPDATE y DELETE en las 3 tablas de sólo agregado) y el intento de orden con estado inexistente; ejecutar contra PostgreSQL y documentar la evidencia de los rechazos (Caso C-14)
- [x] 4.2 Crear `test/casos_de_prueba.http` documentando los 19 casos de prueba (C-01 a C-19) con soporte de cookies para sesiones concurrentes y respuestas esperadas en comentarios
- [x] 4.3 Ejecutar y validar los casos C-01 a C-19 contra el servidor levantado, incluyendo la verificación del Caso C-15 (número idéntico de consultas SQL en órdenes con 2 y 4 ítems bajo `SQL_ECHO=true`)
  - Ejecutado y documentado en `test/evidencia_c09.md`: **115/115 verificaciones OK y 19/19 casos completos**, sobre una base migrada a `0002 (head)` y sembrada con `seed.py`. C-15: **5 SELECT con 2 ítems y 5 con 4**. El defecto de serialización del historial detectado en la primera corrida quedó corregido (`repository.py`: `scalars().all()`), con test de regresión RED→GREEN.
- [x] 4.4 Ejecutar la suite completa de `pytest test/unit -q` y `pytest test/integration -q` asegurando 100% de aprobación sin regresiones
  - `704 passed` (unit) y `217 passed` (integration): **921 passed**, sin regresiones.
- [x] 4.5 Actualizar `CHANGES.md` marcando el change C-09 en `[x]` y registrando los resultados finales de validación
  - `CHANGES.md`: C-09 marcado `[x]` con el resumen (migraciones, seed, 19 casos, pytest).
