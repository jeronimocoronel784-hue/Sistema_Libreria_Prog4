# Evidencia C-07 — detalle sin N+1

Generado con `SQL_ECHO=true` (`python scripts/capturar_c07.py`).
Cada detalle emite un número **fijo** de consultas, igual con uno o con
varios autores/renglones.

## Detalle de un libro (`GET /libros/3`, dos coautores) — 2 SELECT

```sql
-- 1) libro + editorial + género (joinedload, un solo SELECT con JOIN)
SELECT libro.id, libro.isbn, libro.titulo, libro.precio,
       libro.stock, libro.editorial_id, libro.genero_id,
       editorial_1.id, editorial_1.nombre, editorial_1.pais,
       genero_1.id, genero_1.nombre
FROM libro
LEFT OUTER JOIN editorial AS editorial_1 ON editorial_1.id = libro.editorial_id
LEFT OUTER JOIN genero AS genero_1 ON genero_1.id = libro.genero_id
WHERE libro.id = 3;

-- 2) autorías + autores (selectinload, un solo SELECT con IN + JOIN)
SELECT libro_autor.libro_id, libro_autor.autor_id,
       libro_autor.rol, libro_autor.orden,
       autor_1.id, autor_1.nombre, autor_1.nacionalidad
FROM libro_autor
LEFT OUTER JOIN autor AS autor_1 ON autor_1.id = libro_autor.autor_id
WHERE libro_autor.libro_id IN (3);
```

## Detalle de una venta (`GET /ventas/{id}`) — 2 SELECT

```sql
-- 1) venta + cliente (joinedload, un solo SELECT con JOIN)
SELECT venta.id, venta.cliente_id, venta.fecha, venta.total,
       cliente_1.id, cliente_1.nombre, cliente_1.email
FROM venta
LEFT OUTER JOIN cliente AS cliente_1 ON cliente_1.id = venta.cliente_id
WHERE venta.id = 1;

-- 2) renglones + libros (selectinload, un solo SELECT con IN + JOIN)
SELECT renglon_venta.venta_id, renglon_venta.id, renglon_venta.libro_id,
       renglon_venta.cantidad, renglon_venta.precio_unitario,
       libro_1.id, libro_1.isbn, libro_1.titulo, libro_1.precio,
       libro_1.stock, libro_1.editorial_id, libro_1.genero_id
FROM renglon_venta
LEFT OUTER JOIN libro AS libro_1 ON libro_1.id = renglon_venta.libro_id
WHERE renglon_venta.venta_id IN (1);
```

Ninguna lectura depende de carga perezosa: toda relación se declara con
`joinedload` (a uno) o `selectinload` (colecciones) en la consulta original.

## Subrutas relacionadas — 2 SELECT fijos cada una

Cada subruta emite un número **fijo** de consultas, independiente de la
cantidad de filas devueltas (el `limit`/`offset` de RN-10 no agrega
consultas, solo acota la segunda):

| Subruta | Consulta 1 | Consulta 2 |
|---------|-----------|-----------|
| `GET /editoriales/{id}/libros` | `SELECT` editorial por PK (404 si no existe) | `SELECT` libros + editorial + género (`joinedload`) con `OFFSET`/`LIMIT` |
| `GET /generos/{id}/libros` | `SELECT` género por PK (404 si no existe) | `SELECT` libros + editorial + género (`joinedload`) con `OFFSET`/`LIMIT` |
| `GET /autores/{id}/libros` | `SELECT` autor por PK (404 si no existe) | `SELECT` autorías + libro (`joinedload`) con `OFFSET`/`LIMIT` |
| `GET /clientes/{id}/ventas` | `SELECT` cliente por PK (404 si no existe) | `SELECT` ventas con `ORDER BY id` + `OFFSET`/`LIMIT` |
