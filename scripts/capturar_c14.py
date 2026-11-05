"""Genera la evidencia del caso C-14: UPDATE y DELETE sobre
``movimiento_stock`` rechazados por el disparador (RN-12).

Uso:
    python scripts/capturar_c14.py

Escribe ``evidencia/c-14-solo-agregado.txt``.

Las mismas Ã³rdenes que estÃ¡n en ``test/solo_agregado.sql`` (el archivo que se
entrega para correr a mano en ``psql``), pero capturadas desde Python para que
la evidencia quede con la codificaciÃ³n correcta y con los mensajes de error
textuales de PostgreSQL.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg

from app.core.config import get_settings

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "evidencia", "c-14-solo-agregado.txt")

lineas: list[str] = []


def _reparar(texto: str) -> str:
    """Deshace la doble codificaciÃ³n del mensaje de error.

    En Windows, ``asyncpg`` decodifica el mensaje de error de PostgreSQL con la
    codificaciÃ³n de la consola (cp1252) en lugar de con UTF-8: el texto queda
    doblemente codificado (``sÃ³lo`` -> ``sÃƒÂ³lo``). Los datos que devuelve la
    base sÃ­ estÃ¡n bien: esto es sÃ³lo de la presentaciÃ³n del error.
    """
    try:
        return texto.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto


def _titulo(texto: str) -> None:
    lineas.append(texto)
    print(texto)


async def main() -> None:
    settings = get_settings()
    # asyncpg habla el protocolo nativo: se cambia el driver de la URL.
    url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    if settings.POSTGRES_SCHEMA:
        url = f"{url}?options=-csearch_path%3D{settings.POSTGRES_SCHEMA}"

    conexion = await asyncpg.connect(url)
    try:
        _titulo("=== 1. Estado inicial: un movimiento de la venta 1 ===")
        fila = await conexion.fetch(
            "SELECT id, libro_id, venta_id, usuario_id, cantidad, motivo "
            "FROM movimiento_stock WHERE venta_id IS NOT NULL ORDER BY id LIMIT 1"
        )
        _titulo(
            f"  id={fila[0]['id']}  libro_id={fila[0]['libro_id']}  "
            f"venta_id={fila[0]['venta_id']}  usuario_id={fila[0]['usuario_id']}  "
            f"cantidad={fila[0]['cantidad']}  motivo={fila[0]['motivo']}"
        )
        _titulo("")

        _titulo("=== 2. UPDATE sobre movimiento_stock -> debe ser RECHAZADO ===")
        try:
            await conexion.execute(
                "UPDATE movimiento_stock SET cantidad = 999 WHERE venta_id IS NOT NULL"
            )
            _titulo("  ERROR: el UPDATE NO fue rechazado (esto no deberÃ­a pasar)")
        except asyncpg.PostgresError as error:
            _titulo(f"  ERROR:  {_reparar(error.message)}")
            _titulo(f"  SQLSTATE: {error.sqlstate}")
        _titulo("")

        _titulo("=== 3. DELETE sobre movimiento_stock -> debe ser RECHAZADO ===")
        try:
            await conexion.execute(
                "DELETE FROM movimiento_stock WHERE venta_id IS NOT NULL"
            )
            _titulo("  ERROR: el DELETE NO fue rechazado (esto no deberÃ­a pasar)")
        except asyncpg.PostgresError as error:
            _titulo(f"  ERROR:  {_reparar(error.message)}")
            _titulo(f"  SQLSTATE: {error.sqlstate}")
        _titulo("")

        _titulo("=== 4. La tabla sigue intacta (los movimientos no se tocaron) ===")
        total = await conexion.fetchrow(
            "SELECT count(*) AS movimientos, coalesce(sum(cantidad), 0) AS total "
            "FROM movimiento_stock"
        )
        _titulo(
            f"  movimientos={total['movimientos']}  suma de cantidades={total['total']}"
        )
        _titulo("")

        _titulo("=== 5. INSERT: un movimiento nuevo sÃ­ se acepta ===")
        await conexion.execute(
            "INSERT INTO movimiento_stock "
            "(libro_id, venta_id, usuario_id, cantidad, motivo, cuando) "
            "SELECT libro_id, NULL, usuario_id, 1, 'ReposiciÃ³n', now() "
            "FROM movimiento_stock WHERE venta_id IS NOT NULL ORDER BY id LIMIT 1"
        )
        _titulo("  INSERT 0 1")
        _titulo("")

        _titulo(
            "=== 6. INSERT con cantidad 0 -> el CHECK lo rechaza (cantidad <> 0) ==="
        )
        try:
            await conexion.execute(
                "INSERT INTO movimiento_stock "
                "(libro_id, venta_id, usuario_id, cantidad, motivo, cuando) "
                "SELECT libro_id, NULL, usuario_id, 0, 'ReposiciÃ³n', now() "
                "FROM movimiento_stock WHERE venta_id IS NOT NULL ORDER BY id LIMIT 1"
            )
            _titulo("  ERROR: el INSERT NO fue rechazado (esto no deberÃ­a pasar)")
        except asyncpg.PostgresError as error:
            _titulo(f"  ERROR:  {_reparar(error.message)}")
            _titulo(f"  SQLSTATE: {error.sqlstate}")
    finally:
        await conexion.close()

    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    with open(DESTINO, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas) + "\n")

    print()
    print(f"Evidencia escrita en {DESTINO}")


if __name__ == "__main__":
    asyncio.run(main())

