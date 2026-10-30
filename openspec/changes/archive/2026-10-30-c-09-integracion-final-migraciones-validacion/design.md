# Design

## Context

Ver `proposal.md` — Why. Los cambios funcionales C-01 a C-08 definieron 13 modelos SQLModel/SQLAlchemy en `app/modules/*/models.py`, pero la base de datos se encuentra vacía (sin tablas de dominio) y `migrations/env.py` mantiene `target_metadata = None`. Se requiere materializar el esquema en PostgreSQL 16/17 con Alembic, garantizar la inmutabilidad de tablas críticas (RN-15) mediante triggers DDL, exponer las sondas de salud (`/health/live` y `/ready`), poblar el dataset de demostración con `seed.py` y validar la totalidad de las reglas operativas y no funcionales (C-01 a C-19 y consultas sin N+1).

## Goals / Non-Goals

**Goals:**
- Generar la Migración 001 con `alembic autogenerate` cubriendo las 13 tablas, índices parciales y claves foráneas.
- Escribir manualmente la Migración 002 con función PL/pgSQL y disparadores `BEFORE UPDATE OR DELETE` para RN-15.
- Validar el ciclo de vida e idempotencia de migraciones (`upgrade head` → `downgrade base` → `upgrade head`).
- Implementar los endpoints de salud `GET /health/live` (200 directo) y `GET /health/ready` (SELECT 1 asíncrono, 200/503) montados en `router_abierto`.
- Implementar `seed.py` de forma idempotente con el dataset exacto de la consigna.
- Crear y validar los casos de prueba `test/solo_agregado.sql` y `test/casos_de_prueba.http` (C-01 a C-19).

**Non-Goals:**
- Modificar esquemas de datos o firmas de repositorios existentes.
- Crear herramientas de interfaz de usuario o frontend propio.
- Alterar la lógica interna de UoW o repositorios (se mantiene carga anticipada y atomicidad ya verificada).

## Decisions

### 1. Migraciones: Autogeneración 001 y Disparadores Manuales 002
- **Decisión**: La Migración 001 se genera mediante `alembic revision --autogenerate` tras registrar en `migrations/env.py` los modelos de `usuarios`, `clientes`, `repuestos` y `ordenes`. La Migración 002 se redacta a mano conteniendo el código PL/pgSQL:
  ```sql
  CREATE OR REPLACE FUNCTION rechazar_modificacion_o_borrado()
  RETURNS TRIGGER AS $$
  BEGIN
      RAISE EXCEPTION 'Operación no permitida: tabla de sólo agregado (RN-15)' USING ERRCODE = '23505';
  END;
  $$ LANGUAGE plpgsql;
  ```
  y sus 3 triggers sobre `historial_estado_orden`, `movimiento_stock` e `historial_precio_repuesto`.
- **Alternativa descartada**: Incluir los disparadores en la migración 001. Se descarta para mantener una clara separación entre el DDL del modelo relacional autogenerado y las funciones procedimentales de PostgreSQL que Alembic no detecta.

### 2. Endpoints de Salud en Módulo `health`
- **Decisión**: Implementar `app/modules/health/router.py` con `APIRouter(prefix="/health", tags=["Salud"])`. `GET /health/live` devuelve `{ "status": "ok" }`. `GET /health/ready` inyecta `session: AsyncSession = Depends(get_session)` y ejecuta `await session.execute(text("SELECT 1"))`. Captura excepciones de base de datos respondiendo `HTTPException(status_code=503)`. Se monta en `router_abierto` en `app/main.py`.
- **Alternativa descartada**: Montar las rutas directamente en `main.py`. Se descarta para preservar la arquitectura modular por capas del proyecto.

### 3. Estrategia de Idempotencia en `seed.py` frente a RN-15
- **Decisión**: `seed.py` utilizará `TRUNCATE TABLE ... CASCADE` para reiniciar las tablas antes de poblar los datos maestros. En PostgreSQL, `TRUNCATE` no dispara los triggers `FOR EACH ROW` (a menos que se especifique `FOR EACH STATEMENT`), permitiendo limpiar y repoblar el entorno sin violar RN-15 ni deshabilitar temporalmente restricciones.
- **Alternativa descartada**: Usar `DELETE FROM`. Bloqueado inmediatamente por los triggers de la Migración 002.

### 4. Ejecución y Evidencia de Pruebas
- **Decisión**: Crear `test/solo_agregado.sql` estructurado con transacciones aisladas o bloques explicativos que evidencien los rechazos por trigger y el rechazo por FK (Caso C-14). Crear `test/casos_de_prueba.http` compatible con extensiones REST Client (VSCode/JetBrains), usando variables `@name` para capturar cookies de sesión y encadenar las llamadas de C-01 a C-19.

## Risks / Trade-offs

- **[PostgreSQL no activo en entorno local]** → Mitigación: Validar la conexión en `seed.py` y `env.py` reportando fallos de conexión tempranos y claros.
- **[Alembic autogenerate omite índices parciales específicos]** → Mitigación: Revisar manualmente el archivo `0001_inicial.py` generado para asegurar que los índices con cláusula `WHERE` (`ix_vehiculo_patente_vigente`, `ix_repuesto_codigo_vigente`, `ix_asignacion_rol_usuario_rol_abierta`) posean el argumento `postgresql_where`.

## Migration Plan

1. Actualizar `migrations/env.py` con `target_metadata = SQLModel.metadata` e imports de modelos.
2. Ejecutar `alembic revision --autogenerate -m "0001_inicial"`. Revisión manual del diff.
3. Crear `alembic revision -m "0002_solo_agregado"`. Implementar DDL de triggers en `upgrade()` y sus respectivos `DROP` en `downgrade()`.
4. Probar idempotencia: `alembic upgrade head` → `alembic downgrade base` → `alembic upgrade head`.
5. Ejecutar `seed.py` para cargar los datos base del sistema.
