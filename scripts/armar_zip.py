"""Arma el zip de entrega del parcial.

Uso:
    python scripts/armar_zip.py "<Nombre del grupo>"

Deja ``Parcial_Cap1a6_<Nombre del grupo>.zip`` en la raíz del proyecto, con
dos carpetas:

- ``parcial/``: el proyecto ampliado (todo lo que pide el parcial, salvo el
  despliegue).
- ``despliegue/``: el TP de los capítulos 1 a 4 tal como se entregó, con el
  Dockerfile, el .dockerignore, el env.example y el DEPLOY.md.

El zip **no** lleva las carpetas ``.venv`` ni ``__pycache__`` (en ninguna de
las dos) ni el archivo ``.env``: el entorno virtual se reconstruye con
``requirements.txt`` y los ``__pycache__`` los genera Python solo.
"""

import os
import shutil
import sys
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Lo que nunca entra en el zip.
EXCLUIDOS_DIRS = {
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
    ".idea",
    ".vscode",
}
EXCLUIDOS_ARCHIVOS = {".env", ".env.local", ".DS_Store"}

# Contenido de la carpeta ``parcial/`` (todo menos la de despliegue).
CONTENIDO_PARCIAL = (
    "app",
    "migrations",
    "scripts",
    "test",
    "evidencia",
    "docs",
    "alembic.ini",
    "env.example",
    "requirements.txt",
    "README.md",
    "MANUAL.md",
    ".gitignore",
)


def _excluir(nombre: str) -> bool:
    if nombre in EXCLUIDOS_DIRS:
        return True
    if nombre in EXCLUIDOS_ARCHIVOS:
        return True
    # Cualquier archivo de variables: `.env`, `libreria.env`, `algo.env`.
    if nombre.endswith(".env"):
        return True
    if nombre.endswith(".pyc"):
        return True
    return False


def _agregar(origen: str, destino: str, prefijo: str) -> int:
    """Agrega el contenido de ``origen`` al zip, bajo ``prefijo``."""
    agregados = 0
    for carpeta_raiz, carpetas, archivos in os.walk(origen):
        carpetas[:] = [c for c in carpetas if not _excluir(c)]
        for archivo in archivos:
            if _excluir(archivo):
                continue
            ruta = os.path.join(carpeta_raiz, archivo)
            relativa = os.path.relpath(ruta, origen).replace("\\", "/")
            destino.write(ruta, f"{prefijo}/{relativa}")
            agregados += 1
    return agregados


def main() -> None:
    grupo = sys.argv[1] if len(sys.argv) > 1 else ""
    if not grupo:
        print("Uso: python scripts/armar_zip.py \"<Nombre del grupo>\"")
        sys.exit(1)

    nombre_zip = f"Parcial_Cap1a6_{grupo.replace(' ', '_')}.zip"
    ruta_zip = os.path.join(RAIZ, nombre_zip)

    if os.path.exists(ruta_zip):
        os.remove(ruta_zip)

    total = 0
    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as zip:
        for entrada in CONTENIDO_PARCIAL:
            origen = os.path.join(RAIZ, entrada)
            if not os.path.exists(origen):
                continue
            if os.path.isdir(origen):
                total += _agregar(origen, zip, f"parcial/{entrada}")
            else:
                zip.write(origen, f"parcial/{entrada}")
                total += 1

        despliegue = os.path.join(RAIZ, "despliegue")
        if os.path.isdir(despliegue):
            total += _agregar(despliegue, zip, "despliegue")

    print(f"{nombre_zip} escrito con {total} archivos.")

    # Verificación: ni .venv, ni __pycache__, ni .env.
    with zipfile.ZipFile(ruta_zip) as zip:
        nombres = zip.namelist()
    prohibido = [
        n
        for n in nombres
        if "__pycache__" in n
        or "/.venv/" in n
        or n.endswith(".env")
        or n.endswith(".pyc")
    ]
    if prohibido:
        print("FALLO: el zip contiene archivos que no deben ir:")
        for n in prohibido[:20]:
            print("   ", n)
        sys.exit(1)
    print("Verificación OK: sin .venv, sin __pycache__ y sin .env.")


if __name__ == "__main__":
    main()
