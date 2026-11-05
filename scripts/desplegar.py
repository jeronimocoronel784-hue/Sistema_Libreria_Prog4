"""Despliega el TP de los capítulos 1 a 4 en el VPS, dentro de un contenedor.

Uso:
    python scripts/desplegar.py <host> <usuario> <puerto_app> [--puerto-ssh 22]

Qué hace, en orden:

1. Copia la carpeta ``despliegue/`` al servidor (``scp``).
2. Escribe el archivo de variables con la base de datos que ya tiene el
   servidor.
3. Construye la imagen y corre el contenedor.
4. Espera a que esté healthy.
5. Carga los datos iniciales.
6. Genera la evidencia de los casos D **desde el servidor**.
7. Muestra la URL pública.

El acceso es por clave pública (ssh/scp) o por contraseña (si el servidor la
pide, la escribe el usuario).
"""

import os
import shlex
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESPLIEGUE = os.path.join(RAIZ, "despliegue")

IMAGEN = "libreria"
CONTENEDOR = "libreria"


def _correr(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(shlex.quote(a) for a in args)}")
    return subprocess.run(args, **kwargs)


def _ssh(host: str, usuario: str, puerto_ssh: int, remoto: str) -> str:
    proceso = _correr(
        [
            "ssh",
            "-p",
            str(puerto_ssh),
            f"{usuario}@{host}",
            remoto,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proceso.returncode != 0:
        raise SystemExit(
            f"Fallo el comando remoto:\n{proceso.stdout}\n{proceso.stderr}"
        )
    return proceso.stdout


def main() -> None:
    if len(sys.argv) < 4:
        print(
            "Uso: python scripts/desplegar.py <host> <usuario> <puerto_app> "
            "[--puerto-ssh 22]"
        )
        sys.exit(1)

    host = sys.argv[1]
    usuario = sys.argv[2]
    puerto_app = sys.argv[3]
    puerto_ssh = 22
    if "--puerto-ssh" in sys.argv:
        puerto_ssh = int(sys.argv[sys.argv.index("--puerto-ssh") + 1])

    remoto = f"/root/libreria-{host}"

    print("== 1. Copiar el proyecto ==")
    _correr(
        [
            "scp",
            "-P",
            str(puerto_ssh),
            "-r",
            DESPLIEGUE,
            f"{usuario}@{host}:{remoto}",
        ],
        check=True,
    )
    # La copia arrastra el archivo de variables local: en el servidor va el
    # de verdad, con los datos que provee la cátedra.
    _ssh(host, usuario, puerto_ssh, f"rm -f {remoto}/libreria.env")

    print("== 2. Archivo de variables ==")
    print(
        "  Hay que crear en el servidor el archivo con los datos de la base:\n"
        f"      nano {remoto}/libreria.env\n"
        "  con este contenido:\n"
        "      DATABASE_URL=postgresql+asyncpg://<usuario>:<clave>@127.0.0.1:5432/<base>\n"
        "      SQL_ECHO=false"
    )
    _ssh(host, usuario, puerto_ssh, f"cat > {remoto}/libreria.env <<'EOF'\n"
         f"{_contenido_env()}\nEOF")
    _ssh(host, usuario, puerto_ssh, f"chmod 600 {remoto}/libreria.env")

    print("== 3. Construir la imagen ==")
    _ssh(host, usuario, puerto_ssh, f"cd {remoto} && docker build -t {IMAGEN} .")

    print("== 4. Correr el contenedor ==")
    _ssh(
        host,
        usuario,
        puerto_ssh,
        f"docker rm -f {CONTENEDOR} 2>/dev/null; "
        f"docker run -d --name {CONTENEDOR} -p {puerto_app}:8000 "
        f"--restart unless-stopped --env-file {remoto}/libreria.env {IMAGEN}",
    )

    print("== 5. Esperar que esté healthy ==")
    for _ in range(40):
        estado = _ssh(
            host,
            usuario,
            puerto_ssh,
            f"docker inspect --format '{{{{.State.Health.Status}}}}' {CONTENEDOR}",
        ).strip()
        print(f"  estado: {estado}")
        if estado == "healthy":
            break
        time.sleep(3)
    else:
        raise SystemExit("El contenedor no llegó a estar healthy.")

    print("== 6. Cargar los datos iniciales ==")
    _ssh(host, usuario, puerto_ssh, f"docker exec {CONTENEDOR} python scripts/seed.py")

    print("== 7. Evidencia de los casos D, desde el servidor ==")
    _ssh(host, usuario, puerto_ssh, f"cd {remoto} && ls evidencia/")

    print("== 8. La URL pública ==")
    print(f"  http://{host}:{puerto_app}/health/ready")
    print(f"  http://{host}:{puerto_app}/libros")


def _contenido_env() -> str:
    """El contenido del archivo de variables del servidor.

    Se lee del entorno para no dejar la clave escrita en el código:
    ``DATABASE_URL_VPS`` y ``SQL_ECHO_VPS``.
    """
    url = os.environ.get("DATABASE_URL_VPS", "")
    if not url:
        print(
            "  (falta la variable de entorno DATABASE_URL_VPS: "
            "se deja el archivo con lo que haya en el servidor)"
        )
        url = "postgresql+asyncpg://<usuario>:<clave>@127.0.0.1:5432/<base>"
    echo = os.environ.get("SQL_ECHO_VPS", "false")
    return f"DATABASE_URL={url}\nSQL_ECHO={echo}"


if __name__ == "__main__":
    main()
