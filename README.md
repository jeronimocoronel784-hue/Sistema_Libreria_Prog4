# Librería de barrio — API de catálogo y ventas

FastAPI asincrónico + SQLModel + PostgreSQL + Alembic. Sin autenticación,
sin repositorios/Unit of Work y sin Redis: la lógica vive en el `service`
de cada módulo, que recibe la sesión como parámetro.

## Requisitos

- Python 3.12
- PostgreSQL 16 (o compatible) corriendo en `localhost:5432`
- Ver `requirements.txt` para las versiones exactas
  (FastAPI 0.111, SQLModel 0.0.24, SQLAlchemy 2.0 async, asyncpg 0.30,
  Alembic 1.13, python-dotenv 1.0).

## Puesta en marcha desde cero

```bash
# 1. Entorno virtual e instalación
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt

# 2. Base de datos vacía
psql -U postgres -h localhost -c "CREATE DATABASE libreria"

# 3. Variables de entorno (el .env NO se versiona)
copy env.example .env         # Windows
# cp env.example .env         # Linux/macOS
# Editar .env -> DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/libreria

# 4. Migraciones (crea todo el esquema sobre la base vacía)
alembic upgrade head

# 5. Datos iniciales (estado conocido para las pruebas)
python scripts/seed.py

# 6. Servidor
uvicorn app.main:app --reload
# Docs: http://localhost:8000/docs
# Health: GET /health/live -> {"estado": "vivo"}
#         GET /health/ready -> ejecuta SELECT 1
```

Volver atrás y re-aplicar también funciona:

```bash
alembic downgrade -1
alembic upgrade head
```

## Pruebas manuales (`test/*.http`)

Abrir los archivos con la extensión REST Client (VS Code) o replicar con
curl. Cada caso indica su respuesta esperada en un comentario:

| Caso | Qué demuestra | Esperado |
|------|---------------|----------|
| C-01 | Parámetro de ruta no entero | 422 sin ejecutar el handler |
| C-02 | ISBN o email repetido | 409 con mensaje propio |
| C-03 | Segundo perfil del mismo cliente | 409 |
| C-04 | Libro con editorial/autor inexistente | 409 con mensaje propio |
| C-05 | Venta con libro/cliente inexistente | 409 |
| C-06 | Venta válida con dos renglones | 201, precios copiados y total calculado |
| C-07 | Detalle de libro y de venta | Nº fijo de consultas (ver `docs/evidencia-c07.md`) |
| C-08 | Búsqueda con `' OR '1'='1` | 200 con lista vacía |

## Estructura

```
app/main.py                  app, lifespan (motor+sessions en app.state) y routers
app/core/config.py           DATABASE_URL desde .env
app/core/database.py         motor async, fábrica (expire_on_commit=False), get_session
app/modules/<mod>/models.py  tablas, UNIQUE/CHECK/FK+índice, back_populates
app/modules/<mod>/schemas.py DTO Create/Update/Read (los Create no llevan id)
app/modules/<mod>/service.py lógica + traducción de IntegrityError + precarga
app/modules/<mod>/router.py  handlers async def con Depends(get_session)
migrations/                  env async + 0001 (sin genero) + 0002 (agrega genero)
test/                        casos C-01..C-08 en .http
scripts/seed.py              estado inicial conocido
```

## Decisiones clave

- Dinero con `Decimal` y `NUMERIC`; nunca `float`.
- `libro_autor` es objeto de asociación (rol, orden, PK compuesta).
- `Cliente.perfil` es uno a uno (`uselist=False`, `cliente_id` UNIQUE).
- Altas de libro: sin `if` previos, la base valida FK/UNIQUE -> 409.
- Ventas inmutables (sin PATCH), precio copiado del libro, total del servidor,
  aviso simulado con `BackgroundTasks` (`asyncio.sleep(0.5)` + log).
- Lecturas con `joinedload` (relaciones a uno) y `selectinload` (colecciones);
  la búsqueda por título usa parámetro ligado (`ilike`), nunca concatenación.
- Errores 409 con mensajes propios: jamás texto interno de la base.
