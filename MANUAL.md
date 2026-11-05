# Guía manual — cómo levantar el proyecto

Paso a paso, con los comandos exactos, para levantar el proyecto desde cero en
una máquina limpia, armar la imagen de Docker y desplegarla en el VPS.

Está escrito para que cualquiera del grupo lo pueda hacer sin ayuda: si algo
se rompe, está en [Problemas frecuentes](#problemas-frecuentes).

- [Parte 1 — En tu máquina (para desarrollar y probar)](#parte-1--en-tu-máquina-para-desarrollar-y-probar)
- [Parte 2 — La imagen de Docker](#parte-2--la-imagen-de-docker)
- [Parte 3 — El despliegue en el VPS](#parte-3--el-despliegue-en-el-vps)
- [Problemas frecuentes](#problemas-frecuentes)

---

## Parte 1 — En tu máquina (para desarrollar y probar)

### 0. Qué hace falta

| Herramienta | Versión | Para qué |
|-------------|---------|----------|
| Python | 3.12 o superior | el proyecto |
| PostgreSQL | 16 o superior | la base de datos |
| Docker | 20.10 o superior | la imagen del despliegue |

### 1. Clonar el proyecto

```bash
git clone <url-del-repositorio>
cd Sistema_Libreria_Prog4
```

### 2. Entorno virtual y dependencias

```bash
python -m venv .venv
```

Activar el entorno:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Windows (cmd)
.venv\Scripts\activate.bat
# Linux/macOS
source .venv/bin/activate
```

Instalar las dependencias:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> Si PowerShell no deja activar el entorno, es que falta permiso de ejecución
> de scripts: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### 3. Crear la base de datos

Con el cliente de PostgreSQL (`psql`) o pgAdmin:

```bash
psql -U postgres -h localhost -c "CREATE DATABASE libreria"
```

### 4. Configurar el `.env`

Copiar el ejemplo y completarlo. **El `.env` no se versiona nunca.**

```bash
# Windows
copy env.example .env
# Linux/macOS
cp env.example .env
```

Generar la clave de firma del token (es el secreto más importante del sistema:
quien la tenga puede fabricar un token válido para cualquier usuario):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

`.env` completo (los valores de la base son los de tu máquina):

```ini
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<tu contraseña>
POSTGRES_DB=libreria
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

SECRET_KEY=<la clave que generaste arriba>

BCRYPT_ROUNDS=12
BCRYPT_MAX_CONCURRENT_HASHES=4

TOKEN_EXPIRE_MINUTES=30
COOKIE_SECURE=false

POOL_SIZE=5
MAX_OVERFLOW=10
SQL_ECHO=false
```

### 5. Crear el esquema

```bash
alembic upgrade head
```

Debe terminar con `Running upgrade ... -> 0004_solo_agregado`.

### 6. Cargar los datos iniciales

```bash
python scripts/seed.py
```

Deja la base con 5 usuarios, 3 editoriales, 3 géneros, 6 autores, 5 libros,
3 clientes, la venta 1, sus movimientos y una línea de historial de seguridad.

### 7. Levantar el servidor

```bash
uvicorn app.main:app --reload
```

- Docs interactivas: <http://localhost:8000/docs>
- Salud: `GET http://localhost:8000/health/live` → `{"estado": "vivo"}`
- `GET http://localhost:8000/health/ready` → `{"estado": "lista"}` (503 si la
  base no contesta)

### 8. Comprobar que todo anda

```bash
python scripts/e2e_check.py
```

Tiene que terminar con `TODO OK`. El script corre primero el `seed`, así que
deja la base como estaba.

### 9. Credenciales para probar

| Email | Rol | Contraseña |
|-------|-----|------------|
| `admin@example.com` | ADMIN | `Demo1234!` |
| `admin2@example.com` | ADMIN | `Demo1234!` |
| `vendedor@example.com` | VENDEDOR | `Demo1234!` |
| `ana@example.com` | CLIENTE | `Demo1234!` |
| `nuevo@example.com` | VENDEDOR (clave provisoria) | `Temporal1234!` |

### 10. Los casos de prueba a mano

Los archivos `test/*.http` se abren con la extensión **REST Client** de VS Code
(o con el IntelliJ HTTP Client). Cada uno tiene la respuesta esperada en un
comentario. Antes de correr uno: `python scripts/seed.py`.

El caso C-14 (el disparador de sólo agregado) se corre en `psql`:

```bash
psql -U postgres -h localhost -d libreria -f test/solo_agregado.sql
```

---

## Parte 2 — La imagen de Docker

Esta parte es la del despliegue: usa la carpeta **`despliegue/`**, que es el TP
de los capítulos 1 a 4 tal como se entregó (sin los cambios del parcial).

### 1. Entrar a la carpeta

```bash
cd despliegue
```

### 2. Construir la imagen

```bash
docker build -t libreria .
```

La imagen se apoya en `python:3.12-alpine` (74,7 MB en disco). Para ver que la
imagen de la base está por debajo de los 100 MB (caso D-01):

```bash
docker images
```

### 3. Preparar el archivo de variables

El archivo con la configuración **no** va en el repositorio ni en la imagen.
Vive en el servidor. `env.example` tiene la forma; se copia y se completa:

```bash
cp env.example libreria.env
```

```ini
DATABASE_URL=postgresql+asyncpg://<usuario>:<contraseña>@<host>:<puerto>/<base>
SQL_ECHO=false
```

> **La base no está en `localhost`.** Dentro de un contenedor, `localhost` es el
> propio contenedor. Si la base corre directamente en el servidor, el host es
> `host.docker.internal` (en Linux, hay que agregar
> `--add-host=host.docker.internal:host-gateway` al `docker run`).

### 4. Correr el contenedor

```bash
docker run -d --name libreria -p 8000:8000 --restart unless-stopped \
  --env-file libreria.env libreria
```

Ver que quedó sano:

```bash
docker ps        # la columna STATUS tiene que decir "healthy"
docker logs libreria
```

En el log se ve que las migraciones se aplicaron al arrancar.

### 5. Cargar los datos iniciales

```bash
docker exec libreria python scripts/seed.py
```

### 6. Comprobar desde afuera

```bash
curl http://localhost:8000/health/ready
curl http://localhost:8000/libros
```

### 7. El aviso del comprobante aparece en el log

```bash
docker logs libreria | grep Comprobante
```

### 8. Recrear el contenedor sin perder datos

```bash
docker rm -f libreria
docker run -d --name libreria -p 8000:8000 --restart unless-stopped \
  --env-file libreria.env libreria
docker ps
```

Los datos siguen: viven en la base del servidor, no en el contenedor. Y las
migraciones no se repiten (Alembic sabe en qué revisión está).

### 9. La imagen no tiene secretos

```bash
docker run --rm --entrypoint ls libreria -a /app
docker run --rm --entrypoint env libreria
```

No tiene que aparecer `.env` ni `DATABASE_URL`.

### 10. La aplicación no corre como root

```bash
docker exec libreria id
```

El `uid` no puede ser 0.

### 11. Correr la imagen sin `DATABASE_URL`

```bash
docker run --rm --env-file /dev/null libreria
```

Tiene que terminar con error: sin base no hay aplicación que atienda.

---

## Parte 3 — El despliegue en el VPS

### Datos que hay que tener a mano

| Dato | Para qué |
|------|----------|
| Host o IP del VPS | para conectarse por SSH |
| Usuario de SSH | para entrar |
| Puerto de SSH (si no es 22) | para conectarse |
| Puerto asignado por la cátedra para publicar la app | el `-p <puerto>:8000` |
| Host de la base de datos | el `DATABASE_URL` |
| Puerto de la base | el `DATABASE_URL` |
| Usuario y contraseña de la base | el `DATABASE_URL` |
| Nombre de la base | el `DATABASE_URL` |

### 1. Copiar el proyecto al servidor

Desde la máquina:

```bash
scp -r despliegue <usuario>@<host>:<ruta-del-servidor>/
```

O, desde el servidor:

```bash
git clone <url-del-repositorio> && cd Sistema_Libreria_Prog4/despliegue
```

### 2. Crear el archivo de variables en el servidor

```bash
nano libreria.env
```

```ini
DATABASE_URL=postgresql+asyncpg://<usuario>:<contraseña>@<host>:<puerto>/<base>
SQL_ECHO=false
```

Este archivo **no se sube al repositorio ni entra en la imagen**.

### 3. Construir y correr

```bash
docker build -t libreria .
docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped \
  --env-file libreria.env libreria
docker ps
docker logs libreria
```

### 4. Cargar los datos iniciales

```bash
docker exec libreria python scripts/seed.py
```

### 5. Probar desde afuera del servidor

```bash
curl http://<host>:<puerto>/health/ready
curl http://<host>:<puerto>/libros
```

### 6. Actualizar la aplicación

```bash
docker build -t libreria .
docker rm -f libreria
docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped \
  --env-file libreria.env libreria
```

Los datos no se pierden: viven en la base.

### 7. Completar `DEPLOY.md`

Con la URL pública, el día y la hora del despliegue, los comandos `docker
build` y `docker run` completos, los cambios que se le hicieron al TP y cómo
se actualiza. La salida de cada caso D va en `despliegue/evidencia/`.

---

## Problemas frecuentes

### `Connection refused` al levantar el servidor

La base no está donde dice el `.env`. Comprobar:

```bash
psql -U <usuario> -h <host> -p <puerto> -d <base> -c "SELECT 1"
```

### `localhost` dentro del contenedor

Dentro de un contenedor `localhost` es el propio contenedor. Si la base corre
en el servidor, usar `host.docker.internal` y, en Linux, agregar
`--add-host=host.docker.internal:host-gateway`.

### El contenedor queda `unhealthy` pero la app responde

El `HEALTHCHECK` tiene que usar **127.0.0.1**, no `localhost`: en Alpine
`localhost` resuelve primero a `::1` (IPv6) y uvicorn escucha sólo en IPv4.

```bash
docker exec libreria wget -qO- http://127.0.0.1:8000/health/live
```

### `alembic: Can't locate revision identified by '...'`

La base tiene una revisión que esta copia de las migraciones no conoce. O
falta una migración, o la base es de otra versión del proyecto. Para empezar de
cero:

```bash
alembic downgrade base
alembic upgrade head
```

### `Falta la variable de entorno ...` al arrancar

`SECRET_KEY` y la contraseña de la base **no tienen valor por defecto**: si
faltan, la aplicación no arranca. Revisar el `.env`.

### 401 o 403

- **401**: no hay cookie, el token venció o el usuario está inactivo. El token
  viaja **sólo** en la cookie `access_token`; mandar `Authorization: Bearer` no
  funciona (a propósito).
- **403**: el usuario no tiene el rol, o le falta cambiar la contraseña
  provisoria.

### El login dice 429

Hubo 5 intentos fallidos con el mismo correo desde la misma dirección en los
últimos 60 segundos. Se espera un minuto, o se borran los intentos:

```sql
DELETE FROM intento_acceso WHERE email = 'correo@example.com';
```

### `stock` no coincide con la suma de los movimientos

El stock sólo cambia a través de movimientos (RN-11). Para ver la diferencia:

```sql
SELECT l.id, l.titulo, l.stock, COALESCE(SUM(m.cantidad), 0) AS suma
FROM libro l
LEFT JOIN movimiento_stock m ON m.libro_id = l.id
GROUP BY l.id, l.titulo, l.stock;
```

### Un 500 en vez de un 422

Un contrato que no declara un campo lo rechaza con 422 (`extra="forbid"`).
Si aparece un 500, el dato pasó el contrato y lo rechazó la base: mirar el
`detail` de la respuesta, que nunca trae el texto interno de la base.
