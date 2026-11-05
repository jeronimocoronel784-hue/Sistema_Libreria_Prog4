# DEPLOY — TP de los capítulos 1 a 4

Este documento es el que pide la consigna del parcial (Ejercicio 10). Todo lo
que está marcado como **PENDIENTE** se completa cuando el grupo haga el
despliegue en el VPS.

## 1. Datos del despliegue

| Dato | Valor |
|------|-------|
| URL pública | **PENDIENTE** |
| Día y hora del despliegue | **PENDIENTE** |
| Servidor (host y puerto asignado por la cátedra) | **PENDIENTE** |
| Nombre del contenedor | `libreria` |
| Nombre de la imagen | `libreria` |
| Archivo de variables | `libreria.env` (vive en el servidor, fuera del repositorio y de la imagen) |
| Puerto publicado en el host | **PENDIENTE** |

## 2. Comandos completos

Construir la imagen (en el servidor):

```bash
docker build -t libreria .
```

Correr el contenedor:

```bash
docker run -d --name libreria -p <PUERTO>:8000 --restart unless-stopped \
  --env-file libreria.env libreria
```

En Linux, si la base corre directamente en el servidor, se agrega el alias del
host:

```bash
docker run -d --name libreria -p <PUERTO>:8000 --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  --env-file libreria.env libreria
```

Cargar los datos iniciales (la base es la del servidor, no la del contenedor):

```bash
docker exec libreria python scripts/seed.py
```

## 3. Cambios que se le hicieron al TP para que corra en el contenedor

La consigna permite corregir defectos propios del TP y anotarlos acá.

| Archivo | Cambio | Por qué |
|---------|--------|---------|
| `app/modules/ventas/router.py` | El aviso del comprobante pasó de `logging.getLogger("libreria.ventas")` a `logging.getLogger("uvicorn.error")` | Con un logger propio sin configurar el aviso **no** aparecía ni en la consola ni en `docker logs` (caso D-08). Con el logger de uvicorn el mensaje se ve en el registro del contenedor. |

**Sin otros cambios**: la lógica del TP no se tocó. Lo único que se agregó al
proyecto fueron `Dockerfile`, `.dockerignore`, este `env.example` y este
`DEPLOY.md`.

## 4. HEALTHCHECK y `localhost`

Dentro de una imagen Alpine no hay `curl`; viene `wget`. Y `localhost` resuelve
primero a `::1` (IPv6) mientras uvicorn escucha sólo en IPv4 (`--host 0.0.0.0`):
un `HEALTHCHECK` contra `http://localhost:8000/...` fallaría con "Connection
refused" aunque el servidor respondiera bien. Por eso el `HEALTHCHECK` del
`Dockerfile` usa **127.0.0.1**.

Para comprobarlo a mano:

```bash
docker exec libreria wget -qO- http://127.0.0.1:8000/health/live
```

## 5. La base no está en localhost

Dentro de un contenedor, `localhost` es el propio contenedor. Si la base corre
directamente en el servidor, el `DATABASE_URL` del archivo de variables apunta
a `host.docker.internal` (no a `localhost`). Con `localhost` la conexión falla
con "Connection refused" aunque PostgreSQL esté funcionando.

## 6. Cómo se actualiza la aplicación

Los datos no se pierden: viven en la base del servidor, no en el contenedor.

```bash
# 1. Reconstruir la imagen con los cambios
docker build -t libreria .

# 2. Sacar el contenedor viejo
docker rm -f libreria

# 3. Volver a correrlo con el mismo archivo de variables
docker run -d --name libreria -p <PUERTO>:8000 --restart unless-stopped \
  --env-file libreria.env libreria

# 4. Verificar que quedó sano
docker ps
docker logs libreria
```

El contenedor aplica `alembic upgrade head` al arrancar, así que las
migraciones nuevas se aplican solas: no hay que correrlas a mano.

## 7. Evidencia

En `evidencia/` está la salida de cada caso D:

| Caso | Archivo | Qué demuestra |
|------|---------|---------------|
| D-01 | `evidencia/d-01-imagenes.txt` | La imagen base y `python:3.12-alpine` por debajo de 100 MB, y el `Dockerfile` parte de ella |
| D-02 | `evidencia/d-02-build-run.txt` | Build y run en un servidor limpio; contenedor `healthy`; migraciones aplicadas en el log |
| D-03 | `evidencia/d-03-desde-afuera.txt` | Desde afuera del VPS: `/health/ready`, `/libros` y `POST /ventas/` |
| D-04 | `evidencia/d-04-recrear.txt` | `docker rm -f` y el mismo `docker run`: vuelve a estar healthy, los datos siguen, las migraciones no se repiten |
| D-05 | `evidencia/d-05-sin-database-url.txt` | Correr la imagen sin `DATABASE_URL`: el contenedor no queda sirviendo |
| D-06 | `evidencia/d-06-contenido-imagen.txt` | La imagen no tiene `.env` ni `DATABASE_URL` |
| D-07 | `evidencia/d-07-usuario.txt` | `docker exec libreria id` no es root |
| D-08 | `evidencia/d-08-aviso-comprobante.txt` | El aviso del comprobante aparece en `docker logs` después de la respuesta |
