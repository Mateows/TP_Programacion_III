-- ============================================================================
-- C-14 - Tablas de solo agregado (RN-15) y clave foranea del estado
-- ============================================================================
-- Requisitos:
--   * Base taller_db migrada a head y poblada con `python seed.py`.
--   * Ejecutar con psql, por ejemplo (PowerShell):
--       $env:PGPASSWORD='<password de .env>'
--       & 'C:\Program Files\PostgreSQL\17\bin\psql.exe' `
--           -h localhost -U postgres -d taller_db `
--           -f test/solo_agregado.sql
--
-- Resultado esperado: siete (7) rechazos.
--   * C-14.1 a C-14.6: ERROR 23505 "Operacion no permitida: tabla de solo
--     agregado (RN-15)" lanzado por los disparadores BEFORE UPDATE OR DELETE
--     de historial_estado_orden, movimiento_stock e historial_precio_repuesto.
--   * C-14.7: ERROR 23503 de clave foranea porque 'NO_EXISTE' no esta en
--     estado_orden.
--
-- Cada bloque abre su propia transaccion y la revierte con ROLLBACK, de modo
-- que el script no deja ningun cambio y puede re-ejecutarse cuantas veces se
-- quiera. Se mantiene ON_ERROR_STOP en off para que psql siga con el bloque
-- siguiente despues de cada rechazo esperado.
-- ============================================================================

\set ON_ERROR_STOP off

\echo ''
\echo '=== Estado previo (filas y stock) ==='
SELECT
    (SELECT count(*) FROM historial_estado_orden) AS historial_estado_orden,
    (SELECT count(*) FROM movimiento_stock) AS movimiento_stock,
    (SELECT count(*) FROM historial_precio_repuesto) AS historial_precio_repuesto,
    (SELECT stock FROM repuesto WHERE id = 1) AS stock_repuesto_1;

\echo ''
\echo '--- C-14.1 UPDATE historial_estado_orden (esperado: rechazo 23505) ---'
BEGIN;
UPDATE historial_estado_orden
SET hasta_estado = 'TERMINADA'
WHERE id = 1;
ROLLBACK;

\echo ''
\echo '--- C-14.2 DELETE historial_estado_orden (esperado: rechazo 23505) ---'
BEGIN;
DELETE FROM historial_estado_orden
WHERE id = 1;
ROLLBACK;

\echo ''
\echo '--- C-14.3 UPDATE movimiento_stock (esperado: rechazo 23505) ---'
BEGIN;
UPDATE movimiento_stock
SET cantidad = 999
WHERE id = 1;
ROLLBACK;

\echo ''
\echo '--- C-14.4 DELETE movimiento_stock (esperado: rechazo 23505) ---'
BEGIN;
DELETE FROM movimiento_stock
WHERE id = 1;
ROLLBACK;

\echo ''
\echo '--- C-14.5 UPDATE historial_precio_repuesto (esperado: rechazo 23505) ---'
BEGIN;
UPDATE historial_precio_repuesto
SET precio_nuevo = 9999.00
WHERE id = 1;
ROLLBACK;

\echo ''
\echo '--- C-14.6 DELETE historial_precio_repuesto (esperado: rechazo 23505) ---'
BEGIN;
DELETE FROM historial_precio_repuesto
WHERE id = 1;
ROLLBACK;

\echo ''
\echo '--- C-14.7 INSERT orden_trabajo con estado inexistente (esperado: rechazo 23503 por FK) ---'
BEGIN;
INSERT INTO orden_trabajo (vehiculo_id, mecanico_id, estado, falla, total)
VALUES (1, NULL, 'NO_EXISTE', 'Estado que no esta en el catalogo', 0.00);
ROLLBACK;

\echo ''
\echo '=== Estado posterior (debe ser identico al previo) ==='
SELECT
    (SELECT count(*) FROM historial_estado_orden) AS historial_estado_orden,
    (SELECT count(*) FROM movimiento_stock) AS movimiento_stock,
    (SELECT count(*) FROM historial_precio_repuesto) AS historial_precio_repuesto,
    (SELECT stock FROM repuesto WHERE id = 1) AS stock_repuesto_1,
    (SELECT count(*) FROM orden_trabajo) AS orden_trabajo;
