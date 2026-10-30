# Evidencia de validación — C-09 integración final

Fecha de ejecución: 30/10/2026
Alcance: tarea 4 del change `c-09-integracion-final-migraciones-validacion`
(`test/solo_agregado.sql`, `test/casos_de_prueba.http`, validación de C-01 a C-19
contra un servidor real, ciclo de migraciones y pruebas automatizadas).

> **Resultado global: validación exitosa.** Los **19/19 casos** pasan y se
> completaron **115/115 verificaciones** (sin fallos) sobre una base migrada a
> `0002 (head)` y sembrada con `seed.py`. El defecto bloqueante detectado en la
> corrida anterior (serialización del historial del detalle) **está corregido y
> verificado**; ver §6.

## 1. Entorno

| Elemento | Valor |
|---|---|
| Sistema | Windows (PowerShell) |
| Python | 3.12 (`.venv` del proyecto) |
| PostgreSQL | 17 (`C:\Program Files\PostgreSQL\17\bin\psql.exe`) |
| Base | `localhost:5432/taller_db`, usuario `postgres` |
| Esquema | `alembic_version = 0002 (head)`; 14 tablas en `public` (13 de dominio + `alembic_version`), 3 disparadores |
| Datos | `python seed.py` antes de cada corrida y al final |
| Servidor | `uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| SQL_ECHO | `true` para medir C-15 (variable de entorno, sin tocar `.env`) |

El servidor se levantó desde un script temporal (`%TEMP%\c09_run_all.py`) que usa
`httpx` ya instalado; no se agregaron dependencias ni archivos al repo. Los
efectos persistidos se contrastaron con `psql` en los casos donde aporta
evidencia adicional, y así se indica.

## 2. Reproducción

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe seed.py
$env:PGPASSWORD='<password de .env>'
& 'C:\Program Files\PostgreSQL\17\bin\psql.exe' -h localhost -U postgres -d taller_db -f test/solo_agregado.sql
# En otra terminal, con SQL_ECHO=true para reproducir C-15:
$env:SQL_ECHO='true'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
# Luego, con REST Client, abrir test/casos_de_prueba.http y ejecutar en orden.
```

## 3. Ciclo de migraciones

Sobre la base existente:

```text
alembic current                      -> 0002 (head)
alembic downgrade base               -> Running downgrade 0002 -> 0001, solo_agregado
                                        Running downgrade 0001 -> , inicial
alembic upgrade head                 -> Running upgrade  -> 0001, inicial
                                        Running upgrade 0001 -> 0002, solo_agregado
```

Verificación posterior por SQL: 14 tablas en `public`, 3 disparadores no
internos y `alembic_version = 0002`. Luego `seed.py` repobló la base. Los 19
casos de §5 se ejecutaron **después** de este ciclo, sobre el esquema recreado.

## 4. C-14 — Tablas de sólo agregado y FK de estado (script SQL)

`test/solo_agregado.sql` abre una transacción por intento y la revierte con
`ROLLBACK`, por lo que es re-ejecutable y no deja cambios. Salida real de
`psql` sobre la base sembrada (3 líneas de historial, 4 movimientos, 1 precio
histórico, `stock 10`, 2 órdenes):

```text
=== Estado previo (filas y stock) ===
 historial_estado_orden | movimiento_stock | historial_precio_repuesto | stock_repuesto_1
------------------------+------------------+---------------------------+------------------
                      3 |                4 |                         1 |               10
(1 fila)

--- C-14.1 UPDATE historial_estado_orden (esperado: rechazo 23505) ---
BEGIN
psql:test/solo_agregado.sql:40: ERROR:  Operación no permitida: tabla de sólo agregado (RN-15)
CONTEXTO:  función PL/pgSQL rechazar_modificacion_o_borrado() en la línea 3 en RAISE
ROLLBACK

--- C-14.2 DELETE historial_estado_orden (esperado: rechazo 23505) ---
BEGIN
psql:test/solo_agregado.sql:47: ERROR:  Operación no permitida: tabla de sólo agregado (RN-15)
CONTEXTO:  función PL/pgSQL rechazar_modificacion_o_borrado() en la línea 3 en RAISE
ROLLBACK

--- C-14.3 UPDATE movimiento_stock (esperado: rechazo 23505) ---
BEGIN
psql:test/solo_agregado.sql:55: ERROR:  Operación no permitida: tabla de sólo agregado (RN-15)
CONTEXTO:  función PL/pgSQL rechazar_modificacion_o_borrado() en la línea 3 en RAISE
ROLLBACK

--- C-14.4 DELETE movimiento_stock (esperado: rechazo 23505) ---
BEGIN
psql:test/solo_agregado.sql:62: ERROR:  Operación no permitida: tabla de sólo agregado (RN-15)
CONTEXTO:  función PL/pgSQL rechazar_modificacion_o_borrado() en la línea 3 en RAISE
ROLLBACK

--- C-14.5 UPDATE historial_precio_repuesto (esperado: rechazo 23505) ---
BEGIN
psql:test/solo_agregado.sql:70: ERROR:  Operación no permitida: tabla de sólo agregado (RN-15)
CONTEXTO:  función PL/pgSQL rechazar_modificacion_o_borrado() en la línea 3 en RAISE
ROLLBACK

--- C-14.6 DELETE historial_precio_repuesto (esperado: rechazo 23505) ---
BEGIN
psql:test/solo_agregado.sql:77: ERROR:  Operación no permitida: tabla de sólo agregado (RN-15)
CONTEXTO:  función PL/pgSQL rechazar_modificacion_o_borrado() en la línea 3 en RAISE
ROLLBACK

--- C-14.7 INSERT orden_trabajo con estado inexistente (esperado: rechazo 23503 por FK) ---
BEGIN
psql:test/solo_agregado.sql:84: ERROR:  inserción o actualización en la tabla «orden_trabajo» viola la llave foránea «orden_trabajo_estado_fkey»
DETALLE:  La llave (estado)=(NO_EXISTE) no está presente en la tabla «estado_orden».
ROLLBACK

=== Estado posterior (debe ser identico al previo) ===
 historial_estado_orden | movimiento_stock | historial_precio_repuesto | stock_repuesto_1 | orden_trabajo
------------------------+------------------+---------------------------+------------------+---------------
                      3 |                4 |                         1 |               10 |             2
(1 fila)
```

**Resultado: 7 rechazos (6 × RN-15 y 1 × FK) y estado idéntico antes/después. C-14 OK.**

## 5. C-15 — Igual número de consultas para 2 y 4 ítems

Con `SQL_ECHO=true` se contaron las sentencias `SELECT` registradas por
SQLAlchemy entre el inicio y el fin de cada `GET /ordenes/{id}` (los pedidos se
hicieron de a uno, sin concurrencia).

| Orden | Ítems | Total | Respuesta | SELECT ejecutados |
|---|---|---|---|---|
| id 3 (C-10) | 2 (2 × FIL-001 + 1 × ACE-530) | 29000.00 | 200 con 2 ítems | **5** |
| id 4 (C-15) | 4 (FIL-001, FRE-010, BUJ-020, ACE-530) | 57500.00 | 200 con 4 ítems | **5** |

Ambas trazas contienen exactamente las mismas cinco consultas:

1. `SELECT usuario…` (autenticación)
2. `SELECT asignacion_rol…` (roles vigentes)
3. `SELECT orden_trabajo… + vehiculo + cliente + usuario` (cabecera del detalle)
4. `SELECT item_orden… + repuesto` (ítems, en una sola consulta)
5. `SELECT historial_estado_orden…` (historial, en una sola consulta)

Es decir, el detalle no hace una consulta por ítem ni carga perezosa:
**el número de consultas no depende de la cantidad de ítems. C-15 OK.**

## 6. Defecto bloqueante: **corregido y verificado**

### 6.1 Corrección aplicada

`app/modules/ordenes/repository.py`, `listar_detalle` (línea 225):

```diff
- historial = [linea for linea in resultado_historial.all()]
+ historial = list(resultado_historial.scalars().all())
```

`select(HistorialEstadoOrden)` devuelve filas `Row` de un elemento; `.all()` no
desenvuelve la entidad y `HistorialEstadoResponse.model_validate(Row,
from_attributes=True)` fallaba con `5 validation errors … input_type=Row`, lo
que producía **500** en `GET /ordenes/{id}` y en toda operación que responde el
detalle (`POST /ordenes`, `…/terminar`, `…/cancelar`).

### 6.2 Prueba de regresión RED → GREEN

- Test: `test/unit/test_ordenes_repository.py::test_listar_detalle_entrega_entidades_de_historial_no_filas_row`.
  Simula una sesión cuyo `.all()` devuelve `Row` y verifica que el historial
  llega como entidades y se serializa.
- **RED:** en la corrida anterior, contra el servidor real, las 13
  verificaciones afectadas fallaban con 500 y la traza
  `ValidationError: 5 validation errors for HistorialEstadoResponse … input_type=Row`
  quedó registrada (ver historial de esta evidencia).
- **GREEN:** con la corrección aplicada, el test pasa y los mismos casos
  responden 200/201.

```text
.\.venv\Scripts\python.exe -m pytest "test/unit/test_ordenes_repository.py::test_listar_detalle_entrega_entidades_de_historial_no_filas_row" -q
1 passed in 1.01s
```

Además, `ResultadoFalso.scalars()` se agregó a `test/unit/conftest.py` y
`test/integration/conftest.py` para que las sesiones falsas cubran también el
camino `.scalars()`.

### 6.3 Smoke real (cubierto por los 19 casos)

| Operación | Antes | Ahora |
|---|---|---|
| `GET /ordenes/2` (admin) | 500 | **200** con historial de 2 líneas |
| `GET /ordenes/1` (cliente dueño) | 500 | **200** con historial de 1 línea |
| `POST /ordenes` (2 ítems) | 500 (orden persistida) | **201** con ítems, total 29000 e historial |
| `POST /ordenes/2/terminar` | 500 + rollback | **200** `TERMINADA`, stock 6→2, 3 movimientos |
| `POST /ordenes/1/cancelar` | 500 + rollback | **200** `CANCELADA`, 2 líneas de historial |

## 7. Resultado caso por caso (C-01 a C-19)

Corrida final: **115/115 verificaciones OK**, **19/19 casos completos**.

| Caso | Esperado | Obtenido | Veredicto |
|---|---|---|---|
| C-01 | `GET /clientes/abc` → 422 | 422 con `detail` de validación | OK |
| C-02 | alta 201; correo/doc repetidos 409; login de la cuenta rechazada 401; usuario 8 y cliente 3 | 201 / 409 / 409 / 401; 8 usuarios, 3 clientes | OK |
| C-03 | cookie `HttpOnly`, `SameSite=Lax`, `Max-Age=1800`; sin token en el cuerpo; sin cookie/bearer → 401 | todo cumplido | OK |
| C-04 | credenciales inválidas 401, mismo cuerpo y tiempos parecidos | 401/401, cuerpo idéntico, 567 vs 524 ms | OK |
| C-05 | 5 fallos → 401; 6.º/7.º → 429 con `Retry-After`, sin verificar contraseña | 401 ×5; 429 (`Retry-After` 58 y 57); el 6.º sólo consulta `intento_acceso`; 539/521/514/555/563 → 314/327 ms | OK |
| C-06 | sin sesión 401; cliente sin rol de personal 403; cliente ve su orden 200; orden ajena 403 | 401 / 403 / 200 con historial / 403 | OK |
| C-07 | revocación efectiva en la misma cookie; `/auth/yo` distingue roles del token y vigentes; historial conserva la fila; vencimientos inválidos 422 | todo cumplido | OK |
| C-08 | admin no puede revocar su propio ADMIN → 409 | 409 | OK |
| C-09 | `debe_cambiar_password`; cookie vieja limitada; cambio de contraseña renueva cookie; cookie vieja luego 401 | todo cumplido | OK |
| C-10 | alta 201 con precios copiados, total 29000 e historial inicial; repuesto inexistente 409 sin crear orden | 201 con 2 ítems (8500/12000), total 29000, historial `null→PENDIENTE`; 409 correcto y total de órdenes sigue en 3 | OK |
| C-11 | terminar con stock insuficiente → 409 y estado/stock/movimientos/historial intactos | 409; orden 2 sigue `EN_REPARACION` (API y psql), stock 2, 1 movimiento, 2 líneas de historial | OK |
| C-12 | reponer 4 → stock 6; terminar → 200 `TERMINADA`, stock 2, 3 movimientos, 3.ª línea de historial | 200/6; 200 `TERMINADA`; historial `EN_REPARACION→TERMINADA`; stock 2; 3 movimientos con «Consumo por orden» | OK |
| C-13 | dueña cancela orden 1 → 200 `CANCELADA`; ajena 403; terminada 409 | 200 `CANCELADA` (2 líneas de historial, detalle 200); 403; 409 | OK |
| C-14 | 6 rechazos RN-15 + 1 FK, sin cambios | 7 rechazos; conteos y stock idénticos | OK |
| C-15 | altas con 2 y 4 ítems; mismo número de SELECT en el detalle | 201/29000 y 201/57500; detalle 200 con 2 y con 4 ítems; **5 vs 5 SELECT** | OK |
| C-16 | inyección → lista vacía; filtro y paginación; `page`/`size` fuera de rango 422; PATCH parcial no toca precio ni stock; PATCH de stock 422 | todo cumplido (stock verificado por el listado: el API no expone `GET /repuestos/{id}`) | OK |
| C-17 | 4 estados por posición con finales; sin sesión 401; estado no declarado 422 | todo cumplido | OK |
| C-18 | cambio de precio deja historial; segundo PATCH sin precio no agrega línea; recepción 403 | todo cumplido | OK |
| C-19 | baja del vehículo 1 → 204; misma patente reutilizable en otra ficha → 201; duplicada vigente → 409 | 204; 201 (vehículo 4 de Jorge con `AC456EF`); 409 | OK |

## 8. Pruebas automatizadas

```text
.\.venv\Scripts\python.exe -m pytest test/unit -q
704 passed, 1 warning in 3.42s

.\.venv\Scripts\python.exe -m pytest test/integration -q
217 passed, 1 warning in 2.66s
```

**Total: 921 passed**, sin regresiones. La única advertencia es
`PendingDeprecationWarning` de `starlette/formparsers.py` (dependencia, no del
proyecto).

## 9. Conclusión

- **4.1** `test/solo_agregado.sql`: 7 rechazos esperados, sin cambios
  persistidos, re-ejecutable. Completa.
- **4.2** `test/casos_de_prueba.http`: 19 casos con cookies por sesión,
  respuestas esperadas y contratos reales. Completa.
- **4.3** C-01 a C-19 ejecutados contra el servidor real: **19/19 OK**,
  C-15 con **5 SELECT** en ambos tamaños. Completa.
- **4.4** `pytest` unit + integration: **921 passed**. Completa.
- **4.5** `CHANGES.md` marcado `[x]` con el resumen final. Completa.

### Desvíos menores (sin impacto en la validación)

- El API no expone `GET /repuestos/{id}` (405; tampoco figura en la KB de
  diseño), así que los controles de stock de C-11, C-12 y C-16 usan
  `GET /repuestos?q=buj&size=10` (el buscador filtra por descripción).
- El historial de la orden 2 del seed tiene **2** líneas y pasa a **3** al
  terminarla; los comentarios del `.http` se ajustaron en consecuencia.
- Los identificadores de las órdenes creadas en C-10 y C-15 son 3 y 4 en una
  base recién sembrada; la validación los resuelve por total, no por id fijo.
