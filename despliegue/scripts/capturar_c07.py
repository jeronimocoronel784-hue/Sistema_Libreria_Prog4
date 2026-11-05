"""Emite el detalle de un libro y una venta con SQL_ECHO para evidencia C-07."""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SQL_ECHO"] = "true"

logging.basicConfig(level=logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

from fastapi.testclient import TestClient

from app.main import create_app

with TestClient(create_app()) as client:
    v = client.post(
        "/ventas/",
        json={"cliente_id": 2, "renglones": [{"libro_id": 1, "cantidad": 1}]},
    ).json()
    print("=== DETALLE LIBRO 3 (dos autores) ===")
    print("status:", client.get("/libros/3").status_code)
    print("=== DETALLE VENTA (un renglon) ===")
    print("status:", client.get(f"/ventas/{v['id']}").status_code)
