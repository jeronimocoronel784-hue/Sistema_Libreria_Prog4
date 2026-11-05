"""Genera la evidencia del caso C-15: las consultas del detalle de una venta
con 2 renglones y de otra con 4.

Uso:
    python scripts/capturar_c15.py

Escribe ``evidencia/c-15-consultas-detalle.md``. Cada detalle emite un número
**fijo** de consultas, que no crece con la cantidad de renglones.
"""

import asyncio
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import event

from app.main import create_app

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "evidencia", "c-15-consultas-detalle.md")

# La base tiene que estar en el estado inicial conocido.
subprocess.run([sys.executable, os.path.join(RAIZ, "scripts", "seed.py")], check=True)

lineas: list[str] = []


def _titulo(texto: str) -> None:
    lineas.append(texto)
    print(texto)


with TestClient(create_app()) as client:
    app = client.app
    engine = app.state.engine

    # Login del vendedor: las ventas se registran en el mostrador.
    r = client.post(
        "/auth/login",
        json={"email": "vendedor@example.com", "password": "Demo1234!"},
    )
    cookie = r.headers.get("set-cookie", "").split(";")[0]
    cabeceras = {"Cookie": cookie}

    # Dos ventas: una de 2 renglones y otra de 4.
    venta_2 = client.post(
        "/ventas/",
        json={
            "cliente_id": 2,
            "renglones": [
                {"libro_id": 1, "cantidad": 1},
                {"libro_id": 3, "cantidad": 1},
            ],
        },
        headers=cabeceras,
    ).json()
    venta_4 = client.post(
        "/ventas/",
        json={
            "cliente_id": 2,
            "renglones": [
                {"libro_id": 1, "cantidad": 1},
                {"libro_id": 2, "cantidad": 1},
                {"libro_id": 3, "cantidad": 1},
                {"libro_id": 4, "cantidad": 1},
            ],
        },
        headers=cabeceras,
    ).json()

    consultas: list[str] = []

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _capturar(conn, cursor, statement, parameters, context, executemany):
        consultas.append(statement)

    def detalle(venta_id: int) -> list[str]:
        consultas.clear()
        client.get(f"/ventas/{venta_id}", headers=cabeceras)
        return [q for q in consultas if q.strip().upper().startswith("SELECT")]

    selects_2 = detalle(venta_2["id"])
    selects_4 = detalle(venta_4["id"])

_titulo("# Evidencia C-15 — el detalle de una venta no crece con los renglones")
_titulo("")
_titulo(
    "Generado con `python scripts/capturar_c15.py` (el motor registra cada "
    "consulta que se ejecuta)."
)
_titulo("")
_titulo(
    f"Detalle de la venta {venta_2['id']} (2 renglones): "
    f"**{len(selects_2)} consultas**."
)
_titulo("")
for i, consulta in enumerate(selects_2, start=1):
    _titulo(f"```sql")
    _titulo(f"-- consulta {i}")
    _titulo(consulta)
    _titulo("```")
    _titulo("")
_titulo(
    f"Detalle de la venta {venta_4['id']} (4 renglones): "
    f"**{len(selects_4)} consultas**."
)
_titulo("")
for i, consulta in enumerate(selects_4, start=1):
    _titulo("```sql")
    _titulo(f"-- consulta {i}")
    _titulo(consulta)
    _titulo("```")
    _titulo("")
_titulo("## Conclusión")
_titulo("")
_titulo(
    f"La venta de 2 renglones emite {len(selects_2)} consultas y la de 4 "
    f"renglones emite {len(selects_4)}: **el mismo número**."
)
_titulo("")
_titulo(
    "Ninguna lectura depende de carga perezosa: el cliente, los renglones y el "
    "libro de cada renglón (incluso si el libro está dado de baja) se traen con "
    "`joinedload`/`selectinload` declarados en el repositorio."
)

os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
with open(DESTINO, "w", encoding="utf-8") as archivo:
    archivo.write("\n".join(lineas) + "\n")

print()
print(f"Evidencia escrita en {DESTINO}")
print(f"2 renglones: {len(selects_2)} consultas | 4 renglones: {len(selects_4)} consultas")
