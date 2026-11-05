# Evidencia C-15 — el detalle de una venta no crece con los renglones

Generado con `python scripts/capturar_c15.py` (el motor registra cada consulta que se ejecuta).

Detalle de la venta 2 (2 renglones): **4 consultas**.

```sql
-- consulta 1
SELECT usuario.id AS usuario_id, usuario.email AS usuario_email, usuario.nombre AS usuario_nombre, usuario.password_hash AS usuario_password_hash, usuario.activo AS usuario_activo, usuario.debe_cambiar_password AS usuario_debe_cambiar_password 
FROM usuario 
WHERE usuario.id = $1::INTEGER
```

```sql
-- consulta 2
SELECT venta.id, venta.cliente_id, venta.fecha, venta.total, cliente_1.id AS id_1, cliente_1.usuario_id, cliente_1.nombre, cliente_1.email 
FROM venta LEFT OUTER JOIN cliente AS cliente_1 ON cliente_1.id = venta.cliente_id 
WHERE venta.id = $1::INTEGER
```

```sql
-- consulta 3
SELECT renglon_venta.venta_id AS renglon_venta_venta_id, renglon_venta.id AS renglon_venta_id, renglon_venta.libro_id AS renglon_venta_libro_id, renglon_venta.cantidad AS renglon_venta_cantidad, renglon_venta.precio_unitario AS renglon_venta_precio_unitario, libro_1.id AS libro_1_id, libro_1.isbn AS libro_1_isbn, libro_1.titulo AS libro_1_titulo, libro_1.precio AS libro_1_precio, libro_1.stock AS libro_1_stock, libro_1.editorial_id AS libro_1_editorial_id, libro_1.genero_id AS libro_1_genero_id, libro_1.borrado_en AS libro_1_borrado_en 
FROM renglon_venta LEFT OUTER JOIN libro AS libro_1 ON libro_1.id = renglon_venta.libro_id 
WHERE renglon_venta.venta_id IN ($1::INTEGER)
```

```sql
-- consulta 4
SELECT asignacion_rol.rol 
FROM asignacion_rol 
WHERE asignacion_rol.usuario_id = $1::INTEGER AND asignacion_rol.revocada_en IS NULL AND (asignacion_rol.vence_en IS NULL OR asignacion_rol.vence_en > $2::TIMESTAMP WITH TIME ZONE) ORDER BY asignacion_rol.rol
```

Detalle de la venta 3 (4 renglones): **4 consultas**.

```sql
-- consulta 1
SELECT usuario.id AS usuario_id, usuario.email AS usuario_email, usuario.nombre AS usuario_nombre, usuario.password_hash AS usuario_password_hash, usuario.activo AS usuario_activo, usuario.debe_cambiar_password AS usuario_debe_cambiar_password 
FROM usuario 
WHERE usuario.id = $1::INTEGER
```

```sql
-- consulta 2
SELECT venta.id, venta.cliente_id, venta.fecha, venta.total, cliente_1.id AS id_1, cliente_1.usuario_id, cliente_1.nombre, cliente_1.email 
FROM venta LEFT OUTER JOIN cliente AS cliente_1 ON cliente_1.id = venta.cliente_id 
WHERE venta.id = $1::INTEGER
```

```sql
-- consulta 3
SELECT renglon_venta.venta_id AS renglon_venta_venta_id, renglon_venta.id AS renglon_venta_id, renglon_venta.libro_id AS renglon_venta_libro_id, renglon_venta.cantidad AS renglon_venta_cantidad, renglon_venta.precio_unitario AS renglon_venta_precio_unitario, libro_1.id AS libro_1_id, libro_1.isbn AS libro_1_isbn, libro_1.titulo AS libro_1_titulo, libro_1.precio AS libro_1_precio, libro_1.stock AS libro_1_stock, libro_1.editorial_id AS libro_1_editorial_id, libro_1.genero_id AS libro_1_genero_id, libro_1.borrado_en AS libro_1_borrado_en 
FROM renglon_venta LEFT OUTER JOIN libro AS libro_1 ON libro_1.id = renglon_venta.libro_id 
WHERE renglon_venta.venta_id IN ($1::INTEGER)
```

```sql
-- consulta 4
SELECT asignacion_rol.rol 
FROM asignacion_rol 
WHERE asignacion_rol.usuario_id = $1::INTEGER AND asignacion_rol.revocada_en IS NULL AND (asignacion_rol.vence_en IS NULL OR asignacion_rol.vence_en > $2::TIMESTAMP WITH TIME ZONE) ORDER BY asignacion_rol.rol
```

## Conclusión

La venta de 2 renglones emite 4 consultas y la de 4 renglones emite 4: **el mismo número**.

Ninguna lectura depende de carga perezosa: el cliente, los renglones y el libro de cada renglón (incluso si el libro está dado de baja) se traen con `joinedload`/`selectinload` declarados en el repositorio.
