# Imagen del TP de los capítulos 1 a 4 (el proyecto que va al VPS).
#
# Decisiones y por qué:
#
# - Base `python:3.12-alpine`: la imagen base queda por debajo de los 100 MB
#   (la alternativa habitual, `python:3.12-slim`, ronda los 180 MB). Cada MB de
#   la base se paga en disco y en tiempo de descarga en cada despliegue.
# - Las dependencias se instalan ANTES de copiar el código: mientras
#   `requirements.txt` no cambie, esa capa sale de la caché y un cambio en el
#   código no reinstala todo.
# - La aplicación no corre como root: se crea un usuario sin privilegios.
# - No hay secretos en la imagen: ni `.env` ni la dirección de la base. Lo que
#   se hornea en una capa queda ahí para siempre, aunque una capa posterior lo
#   borre. La configuración entra como variables de entorno al correr el
#   contenedor (`--env-file`).
# - Al arrancar se aplican las migraciones y sólo después se levanta uvicorn:
#   si la base no responde, Alembic falla y el contenedor termina con error,
#   que es lo que se quiere (una aplicación que no llega a su base no debería
#   quedar atendiendo).
# - El HEALTHCHECK usa `wget` contra 127.0.0.1: en Alpine no hay `curl`, y
#   `localhost` resuelve primero a ::1 (IPv6) mientras uvicorn escucha sólo en
#   IPv4, así que un chequeo contra `localhost` fallaría con "Connection
#   refused" aunque el servidor respondiera perfecto.

FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# --- Capa 1: dependencias (se cachea mientras requirements.txt no cambie) ---
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# --- Capa 2: código de la aplicación ---
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./

# --- Usuario sin privilegios ---
RUN addgroup -S app && adduser -S app -G app && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8000/health/ready || exit 1

# `exec` deja a uvicorn como PID 1 para que reciba las señales del contenedor.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
