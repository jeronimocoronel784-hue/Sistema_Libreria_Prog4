"""Genera la evidencia de los casos D (el despliegue en contenedor).

Uso:
    python scripts/capturar_d.py

Corre sobre la carpeta ``despliegue/`` (el TP de los capítulos 1 a 4 tal como
se entregó) y deja la salida de cada caso en ``despliegue/evidencia/``.

Necesita Docker con el motor Linux corriendo y un archivo de variables con la
base de datos. Por defecto usa ``despliegue/libreria.env``; se puede pasar
otro con el primer argumento.

Casos:

- D-01: la imagen base y ``python:3.12-alpine`` por debajo de los 100 MB, y el
  ``Dockerfile`` parte de ella.
- D-02: servidor limpio: ``docker build`` y ``docker run``; después
  ``docker ps``; el contenedor en estado ``healthy`` y las migraciones del TP
  aplicadas al arrancar.
- D-03: desde afuera: ``GET /health/ready``, ``GET /libros`` y ``POST
  /ventas/`` con los precios copiados y el total calculado.
- D-04: ``docker rm -f libreria`` y el mismo ``docker run`` otra vez: vuelve a
  estar healthy, los datos siguen y las migraciones no se repiten.
- D-05: correr la imagen sin ``DATABASE_URL``: el contenedor no queda
  sirviendo.
- D-06: contenido de la imagen: no hay ``.env`` ni ``DATABASE_URL``.
- D-07: el usuario del proceso no es root.
- D-08: el aviso del comprobante aparece en ``docker logs`` después de la
  línea de la respuesta.
"""

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESPLIEGUE = os.path.join(RAIZ, "despliegue")
EVIDENCIA = os.path.join(DESPLIEGUE, "evidencia")

IMAGEN = "libreria"
CONTENEDOR = "libreria"
PUERTO = os.environ.get("PUERTO_D", "8000")
ARCHIVO_ENV = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DESPLIEGUE, "libreria.env")


def _docker(*args: str, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, encoding="utf-8", **kwargs
    )


def _texto(comando) -> str:
    if isinstance(comando, subprocess.CompletedProcess):
        return (comando.stdout or "") + (comando.stderr or "")
    return str(comando)


def _escribir(nombre: str, contenido: str) -> None:
    os.makedirs(EVIDENCIA, exist_ok=True)
    with open(os.path.join(EVIDENCIA, nombre), "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
    print(f"  -> evidencia/{nombre}")


def _esperar_sano(intentos: int = 30) -> bool:
    """Espera a que el contenedor esté healthy."""
    for _ in range(intentos):
        estado = _docker("inspect", "--format", "{{.State.Health.Status}}", CONTENEDOR)
        if estado.stdout.strip() == "healthy":
            return True
        time.sleep(2)
    return False


def _pedir(ruta: str, metodo: str = "GET", cuerpo: dict | None = None) -> tuple[int, str]:
    url = f"http://127.0.0.1:{PUERTO}{ruta}"
    datos = None
    cabeceras = {}
    if cuerpo is not None:
        import json

        datos = json.dumps(cuerpo).encode("utf-8")
        cabeceras["Content-Type"] = "application/json"
    peticion = urllib.request.Request(url, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(peticion, timeout=15) as respuesta:
            return respuesta.status, respuesta.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8")
    except Exception as error:  # noqa: BLE001
        return 0, str(error)


def main() -> None:
    if not os.path.isfile(ARCHIVO_ENV):
        print(
            f"Falta el archivo de variables {ARCHIVO_ENV}.\n"
            "Copiá despliegue/env.example a despliegue/libreria.env y completalo "
            "con los datos de la base."
        )
        sys.exit(1)

    print("== D-01: la imagen base y python:3.12-alpine ==")
    imagenes = _docker("images")
    salida = "=== docker images ===\n" + _texto(imagenes)
    _escribir("d-01-imagenes.txt", salida)
    base = _docker("images", "python:3.12-alpine", "--format", "{{.Size}}")
    print(f"  python:3.12-alpine = {base.stdout.strip() or 'no descargada'} bytes")

    print("== D-02: build y run en limpio ==")
    _docker("rm", "-f", CONTENEDOR)
    _docker("rmi", "-f", IMAGEN)
    construccion = _docker("build", "-t", IMAGEN, ".", cwd=DESPLIEGUE)
    corrida = _docker(
        "run",
        "-d",
        "--name",
        CONTENEDOR,
        "-p",
        f"{PUERTO}:8000",
        "--restart",
        "unless-stopped",
        "--env-file",
        ARCHIVO_ENV,
        IMAGEN,
    )
    sano = _esperar_sano()
    estado = _docker("ps")
    logs = _docker("logs", CONTENEDOR)
    salida = (
        "=== docker build ===\n"
        + _texto(construccion)
        + "\n=== docker run ===\n"
        + _texto(corrida)
        + f"\n=== healthy: {sano} ===\n"
        + "=== docker ps ===\n"
        + _texto(estado)
        + "\n=== docker logs libreria ===\n"
        + _texto(logs)
    )
    _escribir("d-02-build-run.txt", salida)

    print("== D-03: desde afuera ==")
    codigo_ready, cuerpo_ready = _pedir("/health/ready")
    codigo_libros, cuerpo_libros = _pedir("/libros")
    codigo_venta, cuerpo_venta = _pedir(
        "/ventas/",
        "POST",
        {
            "cliente_id": 1,
            "renglones": [
                {"libro_id": 1, "cantidad": 1},
                {"libro_id": 2, "cantidad": 1},
            ],
        },
    )
    salida = (
        f"=== GET /health/ready -> {codigo_ready} ===\n{codigo_ready and cuerpo_ready}\n\n"
        f"=== GET /libros -> {codigo_libros} ===\n{codigo_libros and cuerpo_libros}\n\n"
        f"=== POST /ventas/ -> {codigo_venta} ===\n{codigo_venta and cuerpo_venta}\n"
    )
    _escribir("d-03-desde-afuera.txt", salida)

    print("== D-04: recrear el contenedor ==")
    _docker("rm", "-f", CONTENEDOR)
    segunda = _docker(
        "run",
        "-d",
        "--name",
        CONTENEDOR,
        "-p",
        f"{PUERTO}:8000",
        "--restart",
        "unless-stopped",
        "--env-file",
        ARCHIVO_ENV,
        IMAGEN,
    )
    sano2 = _esperar_sano()
    logs2 = _docker("logs", CONTENEDOR)
    estado2 = _docker("ps")
    codigo2, cuerpo2 = _pedir("/libros")
    salida = (
        "=== docker rm -f libreria ===\n"
        + "=== docker run (el mismo) ===\n"
        + _texto(segunda)
        + f"\n=== healthy: {sano2} ===\n"
        + "=== docker ps ===\n"
        + _texto(estado2)
        + "\n=== docker logs libreria (las migraciones no se repiten) ===\n"
        + _texto(logs2)
        + f"\n=== GET /libros -> {codigo2} (los datos siguen) ===\n{codigo2 and cuerpo2}\n"
    )
    _escribir("d-04-recrear.txt", salida)

    print("== D-05: correr la imagen sin DATABASE_URL ==")
    sin_env = _docker(
        "run", "--rm", "--env-file", os.devnull, "-e", "PATH=/usr/local/bin", IMAGEN
    )
    salida = (
        "=== docker run --rm --env-file /dev/null libreria ===\n"
        + _texto(sin_env)
        + "\nEl contenedor tiene que terminar con error: sin base no hay "
        "aplicación que atienda.\n"
    )
    _escribir("d-05-sin-database-url.txt", salida)

    print("== D-06: contenido de la imagen ==")
    listado = _docker("run", "--rm", "--entrypoint", "ls", IMAGEN, "-a", "/app")
    entorno = _docker("run", "--rm", "--entrypoint", "env", IMAGEN)
    salida = (
        "=== docker run --rm --entrypoint ls libreria -a /app ===\n"
        + _texto(listado)
        + "\n=== docker run --rm --entrypoint env libreria ===\n"
        + _texto(entorno)
    )
    _escribir("d-06-contenido-imagen.txt", salida)

    print("== D-07: el usuario del proceso ==")
    identificacion = _docker("exec", CONTENEDOR, "id")
    salida = "=== docker exec libreria id ===\n" + _texto(identificacion)
    _escribir("d-07-usuario.txt", salida)

    print("== D-08: el aviso del comprobante en el log ==")
    logs3 = _docker("logs", CONTENEDOR)
    lineas_aviso = [
        linea for linea in _texto(logs3).splitlines() if "Comprobante" in linea
    ]
    salida = (
        "=== docker logs libreria | grep Comprobante ===\n"
        + ("\n".join(lineas_aviso) if lineas_aviso else "(no hay líneas con Comprobante)")
        + "\n"
    )
    _escribir("d-08-aviso-comprobante.txt", salida)

    print()
    print("Listo: la evidencia de los casos D quedó en despliegue/evidencia/")


if __name__ == "__main__":
    main()
