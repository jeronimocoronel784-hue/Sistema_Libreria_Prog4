# Librería de barrio — API de catálogo, clientes y ventas (parcial cap. 1 a 6)

FastAPI asincrónico + SQLModel + PostgreSQL + Alembic, con acceso por usuarios
y roles, repositorios y Unit of Work, y la capa de despliegue en contenedor.

- Sin autenticación por token en la cabecera: la sesión viaja **sólo** en una
  cookie `HttpOnly`.
- La lógica de negocio vive en el `service` de cada módulo, que recibe el
  **Unit of Work** y lo abre.
- Los repositorios nunca confirman y nunca cierran la sesión: el único punto de
  confirmación es el Unit of Work.

## Integrantes

- Coronel Jeronimo
- Godoy Joaquin
- Gimenez Sabrina
- Saleme Ismael

## Guía manual

`MANUAL.md` tiene el paso a paso, con los comandos exactos, para levantar el
proyecto desde cero en una máquina limpia, armar la imagen de Docker y
desplegarla en el VPS. Está pensado para que cualquiera del grupo lo pueda
hacer sin ayuda.

## Requisitos

- Python 3.12
- PostgreSQL 16 (o compatible)
- Ver `requirements.txt` para las versiones exactas
  (FastAPI 0.111, SQLModel 0.0.24, SQLAlchemy 2.0 async, asyncpg 0.30,
  Alembic 1.13, pydantic-settings 2.16, bcrypt 4.3, PyJWT 2.15).

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

# 4. Generar la clave de firma del token
#    (es el secreto más importante del sistema: no tiene valor por defecto,
#     y si falta la aplicación no arranca)
python -c "import secrets; print(secrets.token_hex(32))"

# 5. Completar el .env con los datos de la base y esa clave, y con
#    POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB / POSTGRES_HOST /
#    POSTGRES_PORT

# 6. Migraciones (crea todo el esquema sobre la base vacía)
alembic upgrade head

# 7. Datos iniciales (estado conocido para las pruebas)
python scripts/seed.py

# 8. Servidor
uvicorn app.main:app --reload
# Docs: http://localhost:8000/docs
# Health: GET /health/live  -> {"estado": "vivo"}
#         GET /health/ready -> SELECT 1; 503 si la base no contesta
```

Volver atrás y re-aplicar también funciona:

```bash
alembic downgrade base
alembic upgrade head
```

## Verificación

```bash
# Casos C-01..C-16 de punta a punta (deja la base en el estado inicial)
python scripts/e2e_check.py

# Evidencia del caso C-15 (consultas del detalle de una venta)
python scripts/capturar_c15.py

# Evidencia del caso C-14 (el disparador de sólo agregado)
python scripts/capturar_c14.py
```

Los casos manuales están en `test/*.http` (se abren con la extensión REST
Client de VS Code) y `test/solo_agregado.sql` (para correr en `psql`).

## Estructura

```
app/main.py                  app, lifespan (motor+sessions en app.state) y los
                             dos grupos de rutas (abierto y protegido)
app/models.py                registro central de modelos (lo importa Alembic)
app/core/config.py           Settings con pydantic-settings
app/core/database.py         motor async, fábrica (expire_on_commit=False), get_session
app/core/security.py         hash con bcrypt fuera del bucle, emisión y
                             verificación del token
app/core/dependencies.py     usuario actual, roles vigentes, cambio obligatorio
                             y requiere_rol
app/core/repository.py       BaseRepository[T] y SoftDeleteRepository[T]
app/core/paginacion.py       el envoltorio de los listados y el cálculo de páginas
app/core/unit_of_work.py     UnitOfWork base: confirma o revierte al salir del bloque
app/core/errors.py           traducción central: IntegrityError -> 409, validación -> 422
app/modules/<módulo>/models.py         tablas, restricciones y relaciones
app/modules/<módulo>/schemas.py        contratos de entrada y de salida
app/modules/<módulo>/repository.py     los repositorios de cada entidad
app/modules/<módulo>/unit_of_work.py   el Unit of Work del módulo
app/modules/<módulo>/service.py        las reglas de negocio (recibe el UoW)
app/modules/<módulo>/router.py         rutas HTTP: construyen el UoW y traducen errores
migrations/                  env async + 0001 y 0002 (TP) + 0003 (autogenerada)
                             + 0004 (a mano: el disparador de sólo agregado)
test/                        casos C-01..C-16 en .http + solo_agregado.sql
evidencia/                   capturas de C-14 y C-15
scripts/seed.py              estado inicial conocido
scripts/e2e_check.py         verificación de punta a punta
despliegue/                  el TP de los capítulos 1 a 4 con Dockerfile y DEPLOY.md
```

## Módulos

| Módulo | Qué tiene |
|--------|-----------|
| `health` | Sólo `router.py`: `/health/live` y `/health/ready` |
| `usuarios` | `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad` y las rutas de `/auth` |
| `editoriales`, `generos`, `autores` | Catálogo de referencia |
| `libros` | `libro`, `libro_autor`, `movimiento_stock`; borrado lógico y stock por movimientos |
| `clientes` | `cliente` (con `usuario_id` opcional) y `perfil_cliente` |
| `ventas` | `venta` y `renglon_venta`; registra la venta y descuenta el stock |

## Decisiones clave

- Dinero con `Decimal` y `NUMERIC`; nunca `float`.
- `libro_autor` es objeto de asociación (rol, orden, PK compuesta).
- `Cliente.perfil` es uno a uno (`uselist=False`, `cliente_id` UNIQUE).
- El ISBN es único **entre los vigentes**: índice único parcial
  `WHERE borrado_en IS NULL`. El libro dado de baja sigue en la tabla porque
  las ventas viejas lo apuntan.
- `movimiento_stock` es de **sólo agregado**: el stock de un libro es la suma
  de sus movimientos, y un movimiento que se equivoca se compensa con otro.
- El stock tiene una **sola vía de escritura** (`aplicar_movimiento_stock`): el
  alta con stock inicial, la reposición y el registro de ventas.
- El login verifica contra un **hash ficticio** cuando el correo no existe:
  misma respuesta y mismo tiempo, sin revelar qué cuentas hay.
- Cada intento de login se anota en `intento_acceso` desde **su propia sesión
  y transacción**, porque el fallo que se quiere contar es el mismo que
  revierte la del login fallido.
- Los roles se deciden con los **roles vigentes en la base**, en cada petición:
  revocar un rol le quita el permiso a una sesión ya abierta.
- Ningún repositorio confirma; ningún servicio construye su Unit of Work; el
  Unit of Work no cierra la sesión.
- Ningún error devuelve texto interno de la base: `IntegrityError` se traduce
  a 409 con mensaje propio, y ninguna entrada inválida termina en un 500.
- El aviso del comprobante se registra en el logger de uvicorn: con un logger
  propio sin configurar no aparecería en la consola ni en `docker logs`.
