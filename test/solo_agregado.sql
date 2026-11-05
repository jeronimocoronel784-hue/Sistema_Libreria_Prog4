-- Caso C-14: el disparador de sólo agregado rechaza UPDATE y DELETE
-- sobre movimiento_stock (RN-12), venga de donde venga.
--
-- Cómo ejecutarlo:
--   psql -U <usuario> -h localhost -d libreria -f test/solo_agregado.sql
--
-- Se espera: los dos primeros comandos fallan con
--   ERROR:  La tabla movimiento_stock es de sólo agregado: UPDATE no está permitido
-- y el INSERT sí se acepta.

\set ON_ERROR_STOP off
\pset pager off

\echo '=== 1. Estado inicial: un movimiento de la venta 1 ==='
SELECT id, libro_id, venta_id, usuario_id, cantidad, motivo
FROM movimiento_stock
WHERE venta_id IS NOT NULL
ORDER BY id
LIMIT 1;

\echo ''
\echo '=== 2. UPDATE sobre movimiento_stock -> debe ser RECHAZADO ==='
UPDATE movimiento_stock
SET cantidad = 999
WHERE venta_id IS NOT NULL;

\echo ''
\echo '=== 3. DELETE sobre movimiento_stock -> debe ser RECHAZADO ==='
DELETE FROM movimiento_stock
WHERE venta_id IS NOT NULL;

\echo ''
\echo '=== 4. La tabla sigue intacta (los movimientos no setocaron) ==='
SELECT count(*) AS movimientos, sum(cantidad) AS total
FROM movimiento_stock;

\echo ''
\echo '=== 5. INSERT: un movimiento nuevo sí se acepta ==='
INSERT INTO movimiento_stock (libro_id, venta_id, usuario_id, cantidad, motivo, cuando)
SELECT libro_id, NULL, usuario_id, 1, 'Reposición', now()
FROM movimiento_stock
WHERE venta_id IS NOT NULL
ORDER BY id
LIMIT 1;

\echo ''
\echo '=== 6. INSERT con cantidad 0 -> el CHECK lo rechaza (cantidad <> 0) ==='
INSERT INTO movimiento_stock (libro_id, venta_id, usuario_id, cantidad, motivo, cuando)
SELECT libro_id, NULL, usuario_id, 0, 'Reposición', now()
FROM movimiento_stock
WHERE venta_id IS NOT NULL
ORDER BY id
LIMIT 1;
