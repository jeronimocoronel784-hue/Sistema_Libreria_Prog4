"""Verificación funcional de punta a punta (casos C-01..C-08 + rutas felices).

Uso:
    python scripts/e2e_check.py
Requiere: Postgres con `alembic upgrade head` + `python scripts/seed.py`.
No usa red: ejerce la app ASGI real con TestClient (lifespan incluido).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.main import create_app

fallos: list[str] = []


def check(nombre: str, cond: bool, detalle: str = "") -> None:
    estado = "PASS" if cond else "FAIL"
    print(f"[{estado}] {nombre} {detalle}")
    if not cond:
        fallos.append(nombre)


with TestClient(create_app()) as client:
    r = client.get("/health/live")
    check("live 200", r.status_code == 200 and r.json() == {"estado": "vivo"}, str(r.json()))
    r = client.get("/health/ready")
    check("ready 200", r.status_code == 200, str(r.json()))

    # --- C-01: ruta no entera -> 422 ---
    r = client.get("/editoriales/abc")
    check("C-01 editorial abc -> 422", r.status_code == 422, str(r.status_code))
    r = client.get("/libros/xyz")
    check("C-01 libro xyz -> 422", r.status_code == 422, str(r.status_code))

    # --- Listados + paginación ---
    r = client.get("/editoriales/?limit=20&offset=0")
    check("GET editoriales 200", r.status_code == 200 and len(r.json()) >= 2, str(r.status_code))
    r = client.get("/libros/?limit=200")
    check("limit>100 -> 422", r.status_code == 422, str(r.status_code))
    r = client.patch("/editoriales/1", json={"pais": "Argentina!"})
    check("PATCH editorial 200 parcial", r.status_code == 200 and r.json()["pais"] == "Argentina!", str(r.json()))
    r = client.get("/editoriales/9999")
    check("editorial inexistente -> 404", r.status_code == 404, str(r.status_code))

    # --- C-02: duplicados -> 409 ---
    r = client.post("/libros/", json={
        "isbn": "978-950-00-0001-1", "titulo": "Dup", "precio": "100.00",
        "stock": 1, "editorial_id": 1, "genero_id": 1,
        "autores": [{"autor_id": 1, "rol": "autor", "orden": 1}]})
    check("C-02 isbn duplicado -> 409", r.status_code == 409, f"{r.status_code} {r.json()}")
    check("C-02 mensaje propio", "isbn" not in str(r.json()).lower() or "ISBN" in str(r.json()) or "libro" in str(r.json()).lower(), str(r.json()))
    r = client.post("/clientes/", json={"nombre": "X", "email": "ana@example.com"})
    check("C-02 email duplicado -> 409", r.status_code == 409, f"{r.status_code} {r.json()}")

    # --- C-03: segundo perfil -> 409 ---
    r = client.post("/clientes/1/perfil", json={"telefono": "1", "direccion": "X"})
    check("C-03 segundo perfil -> 409", r.status_code == 409, f"{r.status_code} {r.json()}")

    # --- C-04: libro con FK inexistente -> 409 ---
    base_libro = {"isbn": "978-950-00-0100-1", "titulo": "T", "precio": "100.00",
                  "stock": 1, "editorial_id": 1, "genero_id": 1,
                  "autores": [{"autor_id": 1, "rol": "autor", "orden": 1}]}
    r = client.post("/libros/", json={**base_libro, "editorial_id": 9999})
    check("C-04 editorial inexistente -> 409", r.status_code == 409, f"{r.status_code} {r.json()}")
    r = client.post("/libros/", json={**base_libro, "autores": [{"autor_id": 9999, "rol": "autor", "orden": 1}]})
    check("C-04 autor inexistente -> 409", r.status_code == 409, f"{r.status_code} {r.json()}")

    # --- C-05: venta con FK inexistente -> 409 ---
    r = client.post("/ventas/", json={"cliente_id": 9999, "renglones": [{"libro_id": 1, "cantidad": 1}]})
    check("C-05 cliente inexistente -> 409", r.status_code == 409, f"{r.status_code} {r.json()}")
    r = client.post("/ventas/", json={"cliente_id": 2, "renglones": [{"libro_id": 9999, "cantidad": 1}]})
    check("C-05 libro inexistente -> 409", r.status_code == 409, f"{r.status_code} {r.json()}")

    # --- C-06: venta válida con dos renglones -> 201 ---
    r = client.post("/ventas/", json={"cliente_id": 2, "renglones": [
        {"libro_id": 1, "cantidad": 2}, {"libro_id": 4, "cantidad": 1}]})
    check("C-06 venta válida -> 201", r.status_code == 201, str(r.status_code))
    venta = r.json()
    check("C-06 total 65000.00", str(venta.get("total")) == "65000.00", str(venta.get("total")))
    reng = {x["libro_id"]: x for x in venta.get("renglones", [])}
    check("C-06 precios copiados", str(reng.get(1, {}).get("precio_unitario")) == "25000.00"
          and str(reng.get(4, {}).get("precio_unitario")) == "15000.00", str(venta.get("renglones")))
    check("C-06 subtotales", str(reng.get(1, {}).get("subtotal")) == "50000.00"
          and str(reng.get(4, {}).get("subtotal")) == "15000.00", str(venta.get("renglones")))
    venta_id = venta.get("id")
    r = client.post("/ventas/", json={"cliente_id": 2, "renglones": []})
    check("venta sin renglones -> 422", r.status_code == 422, str(r.status_code))
    r = client.post("/ventas/", json={"cliente_id": 2, "renglones": [
        {"libro_id": 1, "cantidad": 1}, {"libro_id": 1, "cantidad": 2}]})
    check("venta libro repetido -> 422", r.status_code == 422, str(r.status_code))

    # --- C-07: detalles con relaciones ---
    r = client.get("/libros/3")
    detalle = r.json()
    check("C-07 detalle libro 200", r.status_code == 200, str(r.status_code))
    check("C-07 libro con editorial+genero+2 autores",
          detalle.get("editorial", {}).get("nombre") == "Sudamericana"
          and detalle.get("genero", {}).get("nombre") == "Novela"
          and len(detalle.get("autores", [])) == 2, str(detalle))
    r = client.get(f"/ventas/{venta_id}")
    dv = r.json()
    check("C-07 detalle venta 200", r.status_code == 200, str(r.status_code))
    check("C-07 venta con cliente+2 renglones",
          dv.get("cliente", {}).get("email") == "tomas@example.com"
          and len(dv.get("renglones", [])) == 2, str(dv))

    # --- C-08: inyección en título -> 200 [] ---
    r = client.get("/libros/", params={"titulo": "' OR '1'='1"})
    check("C-08 inyección -> 200 vacía", r.status_code == 200 and r.json() == [], f"{r.status_code} {r.json()}")
    r = client.get("/libros/", params={"titulo": "RAYUELA"})
    check("filtro case-insensitive", r.status_code == 200 and len(r.json()) == 1, str(r.json()))

    # --- Rutas relacionadas ---
    r = client.get("/editoriales/1/libros")
    check("libros de editorial", r.status_code == 200 and len(r.json()) >= 3, str(r.status_code))
    r = client.get("/generos/1/libros")
    check("libros de género", r.status_code == 200 and len(r.json()) >= 3, str(r.status_code))
    r = client.get("/autores/2/libros")
    check("libros de autor", r.status_code == 200 and len(r.json()) == 2, str(r.json()))
    r = client.get("/clientes/2/ventas")
    check("ventas de cliente", r.status_code == 200 and len(r.json()) >= 1, str(r.status_code))
    r = client.get("/clientes/1")
    check("cliente con perfil", r.status_code == 200 and r.json().get("perfil") is not None, str(r.json()))

    print()
    if fallos:
        print(f"FALLARON {len(fallos)}: {fallos}")
        raise SystemExit(1)
    print("TODO OK")
