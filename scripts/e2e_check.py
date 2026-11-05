"""Verificación funcional de punta a punta (casos C-01..C-16).

Uso:
    python scripts/seed.py     # antes: la base en el estado inicial conocido
    python scripts/e2e_check.py

No usa red: ejerce la app ASGI real con TestClient (lifespan incluido).
Cada caso de la consigna tiene su bloque y su resultado esperado.
"""

import asyncio
import logging
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import event, text

from app.main import create_app

# La base tiene que estar en el estado inicial conocido: el script deja datos
# (ventas, roles, intentos) y no es idempotente.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
subprocess.run([sys.executable, os.path.join(RAIZ, "scripts", "seed.py")], check=True)

fallos: list[str] = []
avisos: list[str] = []


def check(nombre: str, cond: bool, detalle: str = "") -> None:
    estado = "PASS" if cond else "FAIL"
    print(f"[{estado}] {nombre} {detalle}")
    if not cond:
        fallos.append(nombre)


class CapturadorLog(logging.Handler):
    """Guarda los mensajes del logger ``uvicorn.error`` (el aviso del comprobante)."""

    def emit(self, record: logging.LogRecord) -> None:
        avisos.append(record.getMessage())


with TestClient(create_app()) as client:
    app = client.app
    engine = app.state.engine

    # Contador de consultas para el caso C-15 y event loop de la app.
    consultas: list[str] = []
    loop_app: list = []

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _contar(conn, cursor, statement, parameters, context, executemany):
        consultas.append(statement)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        if not loop_app:
            loop_app.append(loop)

    def ejecutar_sql(texto_sql: str) -> list[tuple]:
        """Corre SQL crudo en el **mismo** event loop que la app.

        Las conexiones del motor están atadas al loop del TestClient: abrirlas
        desde otro loop da error (o se queda colgado).
        """
        assert loop_app, "La app todavía no ejecutó ninguna consulta."

        async def _run():
            async with engine.connect() as conn:
                result = await conn.execute(text(texto_sql))
                return list(result.fetchall())

        return asyncio.run_coroutine_threadsafe(_run(), loop_app[0]).result()

    # Una consulta cualquiera para que el listener capture el loop.
    client.get("/health/ready")

    # =====================================================================
    # C-01: parámetro de ruta no entero -> 422 sin ejecutar el handler
    # =====================================================================
    r = client.get("/libros/abc")
    check("C-01 libro abc -> 422", r.status_code == 422, str(r.status_code))
    r = client.get("/editoriales/xyz")
    check("C-01 editorial xyz -> 422", r.status_code == 422, str(r.status_code))
    r = client.get("/ventas/no-es-un-id")
    check(
        "C-01 venta no entera sin sesión -> 401",
        r.status_code == 401,
        str(r.status_code),
    )

    # =====================================================================
    # Catálogo público (sin sesión) y envoltorio de paginación
    # =====================================================================
    r = client.get("/libros?size=2")
    cuerpo = r.json()
    check(
        "catálogo público 200",
        r.status_code == 200,
        str(r.status_code),
    )
    check(
        "envoltorio {items,total,page,size,pages}",
        set(cuerpo) == {"items", "total", "page", "size", "pages"},
        str(sorted(cuerpo)),
    )
    check(
        "page=1 size=2 y total=5",
        cuerpo["page"] == 1
        and cuerpo["size"] == 2
        and cuerpo["total"] == 5
        and cuerpo["pages"] == 3,
        str(cuerpo),
    )
    r = client.get("/libros?page=4&size=2")
    check("page fuera de rango -> 422", r.status_code == 422, str(r.status_code))
    r = client.get("/libros?size=500")
    check("size=500 -> 422", r.status_code == 422, str(r.status_code))
    r = client.get("/libros?page=0")
    check("page=0 -> 422", r.status_code == 422, str(r.status_code))

    # =====================================================================
    # C-16: búsqueda con ' OR '1'='1 ; paginación con filtro; PATCH parcial;
    #        PATCH del stock -> 422
    # =====================================================================
    r = client.get("/libros?titulo=%27%20OR%20%271%27%3D%271")
    cuerpo = r.json()
    check(
        "C-16 inyección de SQL -> lista vacía",
        r.status_code == 200 and cuerpo["total"] == 0 and cuerpo["items"] == [],
        str(cuerpo),
    )
    r = client.get("/libros?titulo=ficc&size=1")
    cuerpo = r.json()
    check(
        "C-16 filtro con total 1 y pages 1",
        cuerpo["total"] == 1 and cuerpo["pages"] == 1,
        str(cuerpo),
    )
    r = client.get("/libros?titulo=ficc&size=1&page=2")
    check("C-16 page=2 con 1 resultado -> 422", r.status_code == 422, str(r.status_code))

    # =====================================================================
    # Login: cookie HttpOnly, cuerpo sin token, 401 con Bearer
    # =====================================================================
    r = client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "Demo1234!"}
    )
    check("login admin -> 200", r.status_code == 200, str(r.status_code))
    cookie = r.headers.get("set-cookie", "")
    check("C-03 cookie HttpOnly", "HttpOnly" in cookie, cookie[:80])
    check("C-03 cookie SameSite=Lax", "samesite=lax" in cookie.lower(), cookie[:80])
    check("C-03 cookie Max-Age", "max-age=1800" in cookie.lower(), cookie[:80])
    check(
        "C-03 el cuerpo no trae el token",
        "token" not in r.text.lower() and r.json().get("expira_en_segundos") == 1800,
        r.text[:120],
    )
    admin_cookie = cookie.split(";")[0]

    r = client.get("/auth/yo", headers={"Cookie": admin_cookie})
    check(
        "C-03 /auth/yo con cookie -> 200",
        r.status_code == 200 and r.json()["usuario"]["email"] == "admin@example.com",
        r.text[:160],
    )
    check(
        "/auth/yo devuelve roles vigentes y del token",
        set(r.json()) == {"usuario", "roles_vigentes", "roles_del_token"},
        str(sorted(r.json())),
    )
    # El TestClient guarda cookies: hay que vaciar el jar para probar el caso
    # "sin cookie".
    client.cookies.clear()
    r = client.get("/auth/yo")
    check("C-03 sin cookie -> 401", r.status_code == 401, str(r.status_code))
    r = client.get(
        "/auth/yo", headers={"Authorization": "Bearer " + admin_cookie.split("=")[1]}
    )
    check(
        "C-03 Authorization: Bearer -> 401",
        r.status_code == 401,
        str(r.status_code),
    )

    # C-01 con la sesión iniciada: el parámetro de ruta no entero es 422.
    r = client.get("/ventas/no-es-un-id", headers={"Cookie": admin_cookie})
    check(
        "C-01 venta no entera con sesión -> 422",
        r.status_code == 422,
        str(r.status_code),
    )

    # =====================================================================
    # C-02: registro; correo repetido de usuario y de cliente
    # =====================================================================
    nuevo_cliente = {
        "email": "nuevo_cliente@example.com",
        "nombre": "Cliente Nuevo",
        "password": "Demo1234!",
    }
    r = client.post("/auth/registro", json=nuevo_cliente)
    check("C-02 registro -> 201", r.status_code == 201, f"{r.status_code} {r.text[:120]}")
    r = client.post("/auth/registro", json=nuevo_cliente)
    check("C-02 registro repetido -> 409", r.status_code == 409, str(r.status_code))
    filas = ejecutar_sql(
        "SELECT count(*) FROM usuario WHERE email = 'nuevo_cliente@example.com'"
    )
    check(
        "C-02 el registro rechazado no deja filas sueltas",
        filas[0][0] == 1,
        str(filas),
    )
    r = client.post(
        "/auth/registro",
        json={"email": "lucia@example.com", "nombre": "Impostor", "password": "Demo1234!"},
    )
    check(
        "C-02 correo de cliente repetido -> 409",
        r.status_code == 409,
        str(r.status_code),
    )

    # =====================================================================
    # C-04: contraseña mala y correo inexistente -> 401 con el mismo cuerpo
    # =====================================================================
    r1 = client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "incorrecta"}
    )
    r2 = client.post(
        "/auth/login",
        json={"email": "no_existe@example.com", "password": "incorrecta"},
    )
    check("C-04 contraseña mala -> 401", r1.status_code == 401, str(r1.status_code))
    check("C-04 correo inexistente -> 401", r2.status_code == 401, str(r2.status_code))
    check(
        "C-04 el mismo cuerpo en los dos casos",
        r1.json() == r2.json(),
        f"{r1.text} vs {r2.text}",
    )

    # =====================================================================
    # C-05: seis intentos fallidos -> el sexto 429 con Retry-After
    # =====================================================================
    for i in range(5):
        r = client.post(
            "/auth/login",
            json={"email": "c05@example.com", "password": f"mala{i}"},
        )
    check("C-05 los cinco primeros -> 401", r.status_code == 401, str(r.status_code))
    r = client.post(
        "/auth/login", json={"email": "c05@example.com", "password": "otra"}
    )
    check("C-05 el sexto -> 429", r.status_code == 429, str(r.status_code))
    check(
        "C-05 el sexto trae Retry-After",
        "retry-after" in {k.lower() for k in r.headers},
        str(dict(r.headers)),
    )
    filas = ejecutar_sql(
        "SELECT count(*) FROM intento_acceso WHERE email = 'c05@example.com' AND exito = false"
    )
    check("C-05 los cinco fallos están en la tabla", filas[0][0] == 5, str(filas))

    # =====================================================================
    # C-06: 401 sin sesión, 403 sin rol, y lo propio
    # =====================================================================
    r = client.post("/libros/", json={"isbn": "1", "titulo": "x", "precio": "1.00"})
    check("C-06 sin sesión -> 401", r.status_code == 401, str(r.status_code))

    r = client.post(
        "/auth/login",
        json={"email": "vendedor@example.com", "password": "Demo1234!"},
    )
    vendedor_cookie = r.headers.get("set-cookie", "").split(";")[0]
    check("login vendedor -> 200", r.status_code == 200, str(r.status_code))

    r = client.post(
        "/libros/",
        json={
            "isbn": "978-950-00-9999-9",
            "titulo": "No permitido",
            "precio": "100.00",
            "stock_inicial": 1,
            "editorial_id": 1,
            "genero_id": 1,
            "autores": [],
        },
        headers={"Cookie": vendedor_cookie},
    )
    check("C-06 un vendedor que crea un libro -> 403", r.status_code == 403, str(r.status_code))

    # Cliente: sus ventas y ninguna otra.
    r = client.post(
        "/auth/login", json={"email": "ana@example.com", "password": "Demo1234!"}
    )
    ana_cookie = r.headers.get("set-cookie", "").split(";")[0]
    check("login cliente -> 200", r.status_code == 200, str(r.status_code))

    r = client.get("/mis-ventas", headers={"Cookie": ana_cookie})
    check("C-06 /mis-ventas -> 200", r.status_code == 200, str(r.status_code))
    r = client.get("/ventas/1", headers={"Cookie": ana_cookie})
    check(
        "C-06 la cliente ve la venta ajena -> 403",
        r.status_code == 403,
        str(r.status_code),
    )

    # =====================================================================
    # C-09: cambio obligatorio de contraseña
    # =====================================================================
    r = client.post(
        "/auth/login",
        json={"email": "nuevo@example.com", "password": "Temporal1234!"},
    )
    nuevo_cookie = r.headers.get("set-cookie", "").split(";")[0]
    check("C-09 login con clave provisoria -> 200", r.status_code == 200, str(r.status_code))
    r = client.get("/ventas/", headers={"Cookie": nuevo_cookie})
    check(
        "C-09 ruta protegida con cambio pendiente -> 403",
        r.status_code == 403,
        str(r.status_code),
    )
    r = client.get("/auth/yo", headers={"Cookie": nuevo_cookie})
    check(
        "C-09 /auth/yo no exige el cambio",
        r.status_code == 200,
        str(r.status_code),
    )
    r = client.post(
        "/auth/cambiar-password",
        json={"password_actual": "Temporal1234!", "password_nueva": "NuevaClave123!"},
        headers={"Cookie": nuevo_cookie},
    )
    check("C-09 cambio de contraseña -> 200", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
    r = client.get("/ventas/", headers={"Cookie": nuevo_cookie})
    check(
        "C-09 la misma cookie sirve después del cambio",
        r.status_code == 200,
        str(r.status_code),
    )
    r = client.get("/auth/yo", headers={"Cookie": nuevo_cookie})
    check(
        "C-09 debe_cambiar_password queda en falso",
        r.json()["usuario"]["debe_cambiar_password"] is False,
        r.text[:160],
    )

    # =====================================================================
    # C-07: revocar un rol con la sesión abierta
    # =====================================================================
    r = client.post(
        "/usuarios/4/roles",
        json={"rol": "VENDEDOR"},
        headers={"Cookie": admin_cookie},
    )
    check(
        "C-07 asignar rol -> 201",
        r.status_code == 201,
        f"{r.status_code} {r.text[:120]}",
    )
    r = client.get("/ventas/", headers={"Cookie": ana_cookie})
    check(
        "C-07 con el rol asignado puede entrar",
        r.status_code == 200,
        str(r.status_code),
    )
    r = client.delete("/usuarios/4/roles/VENDEDOR", headers={"Cookie": admin_cookie})
    check(
        "C-07 revocar el rol -> 200",
        r.status_code == 200,
        f"{r.status_code} {r.text[:120]}",
    )
    r = client.get("/ventas/", headers={"Cookie": ana_cookie})
    check(
        "C-07 la misma cookie recibe 403 en la petición siguiente",
        r.status_code == 403,
        str(r.status_code),
    )
    r = client.get("/usuarios/4/roles", headers={"Cookie": admin_cookie})
    check(
        "C-07 la fila revocada sigue en el historial",
        r.status_code == 200
        and any(
            rol["revocada_en"] is not None for rol in r.json()
        ),
        str(r.text[:200]),
    )
    r = client.post(
        "/usuarios/4/roles",
        json={"rol": "VENDEDOR", "vence_en": "2020-01-01T00:00:00+00:00"},
        headers={"Cookie": admin_cookie},
    )
    check("C-07 vencimiento en el pasado -> 422", r.status_code == 422, str(r.status_code))
    r = client.post(
        "/usuarios/4/roles",
        json={"rol": "VENDEDOR", "vence_en": "2030-01-01T00:00:00"},
        headers={"Cookie": admin_cookie},
    )
    check("C-07 vencimiento sin zona horaria -> 422", r.status_code == 422, str(r.status_code))

    # =====================================================================
    # C-08: autoprotección
    # =====================================================================
    r = client.delete("/usuarios/1/roles/ADMIN", headers={"Cookie": admin_cookie})
    check("C-08 revocarse el propio ADMIN -> 409", r.status_code == 409, str(r.status_code))

    # =====================================================================
    # C-10: venta válida con dos renglones
    # =====================================================================
    stock_antes = dict(
        (row[0], row[1])
        for row in ejecutar_sql("SELECT id, stock FROM libro ORDER BY id")
    )
    logger_uvicorn = logging.getLogger("uvicorn.error")
    # Uvicorn configura ese logger con nivel INFO y su propio handler: sin
    # esa configuración (que es lo que pasa en un test) el mensaje se pierde.
    logger_uvicorn.setLevel(logging.INFO)
    capturador = CapturadorLog()
    logger_uvicorn.addHandler(capturador)
    avisos.clear()

    r = client.post(
        "/ventas/",
        json={
            "cliente_id": 2,
            "renglones": [
                {"libro_id": 1, "cantidad": 1},
                {"libro_id": 3, "cantidad": 1},
            ],
        },
        headers={"Cookie": vendedor_cookie},
    )
    check("C-10 venta válida -> 201", r.status_code == 201, f"{r.status_code} {r.text[:160]}")
    cuerpo = r.json()
    check(
        "C-10 el precio se copia del libro y el total lo calcula el servidor",
        cuerpo["total"] == "47000.00"
        and {rg["precio_unitario"] for rg in cuerpo["renglones"]} == {"25000.00", "22000.00"},
        str(cuerpo),
    )
    stock_despues = dict(
        (row[0], row[1])
        for row in ejecutar_sql("SELECT id, stock FROM libro ORDER BY id")
    )
    check(
        "C-10 el stock de cada libro bajó",
        stock_despues[1] == stock_antes[1] - 1
        and stock_despues[3] == stock_antes[3] - 1,
        f"{stock_antes} -> {stock_despues}",
    )
    movimientos = ejecutar_sql(
        "SELECT count(*) FROM movimiento_stock WHERE venta_id = "
        f"{cuerpo['id']} "
    )
    check("C-10 hay un movimiento por renglón", movimientos[0][0] == 2, str(movimientos))
    check(
        "C-10 el aviso sale en el registro",
        any("Comprobante" in m for m in avisos),
        str(avisos),
    )
    logger_uvicorn.removeHandler(capturador)

    # =====================================================================
    # C-11: stock insuficiente -> 409 y ninguna escritura
    # =====================================================================
    movimientos_antes = ejecutar_sql("SELECT count(*) FROM movimiento_stock")[0][0]
    ventas_antes = ejecutar_sql("SELECT count(*) FROM venta")[0][0]
    r = client.post(
        "/ventas/",
        json={
            "cliente_id": 2,
            "renglones": [
                {"libro_id": 1, "cantidad": 1},
                {"libro_id": 5, "cantidad": 2},
            ],
        },
        headers={"Cookie": vendedor_cookie},
    )
    check("C-11 stock insuficiente -> 409", r.status_code == 409, str(r.status_code))
    check(
        "C-11 no queda ninguna escritura",
        ejecutar_sql("SELECT count(*) FROM movimiento_stock")[0][0] == movimientos_antes
        and ejecutar_sql("SELECT count(*) FROM venta")[0][0] == ventas_antes,
        "conteos cambiados",
    )
    cuadra = ejecutar_sql(
        "SELECT bool_and(l.stock = COALESCE(s.suma, 0)) FROM libro l "
        "LEFT JOIN (SELECT libro_id, SUM(cantidad) suma FROM movimiento_stock GROUP BY libro_id) s "
        "ON s.libro_id = l.id"
    )
    check("C-11 el stock sigue cuadrando con los movimientos", cuadra[0][0] is True, str(cuadra))

    # =====================================================================
    # C-12: cliente inexistente, libro inexistente y libro dado de baja
    # =====================================================================
    r = client.post(
        "/ventas/",
        json={"cliente_id": 999, "renglones": [{"libro_id": 1, "cantidad": 1}]},
        headers={"Cookie": vendedor_cookie},
    )
    check("C-12 cliente inexistente -> 409", r.status_code == 409, str(r.status_code))
    r = client.post(
        "/ventas/",
        json={"cliente_id": 2, "renglones": [{"libro_id": 999, "cantidad": 1}]},
        headers={"Cookie": vendedor_cookie},
    )
    check("C-12 libro inexistente -> 409", r.status_code == 409, str(r.status_code))

    # =====================================================================
    # C-13: reponer, dar de baja, volver a cargar el mismo ISBN
    # =====================================================================
    r = client.post(
        "/libros/5/reponer",
        json={"cantidad": 10},
        headers={"Cookie": admin_cookie},
    )
    check("C-13 reposición -> 200", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
    check(
        "C-13 la reposición deja su movimiento",
        ejecutar_sql(
            "SELECT count(*) FROM movimiento_stock WHERE libro_id = 5 AND cantidad = 10"
        )[0][0]
        == 1,
        "movimiento de reposición",
    )
    r = client.delete("/libros/5", headers={"Cookie": admin_cookie})
    check("C-13 baja -> 204", r.status_code == 204, str(r.status_code))
    r = client.get("/libros/5")
    check("C-13 el libro desaparece del catálogo", r.status_code == 404, str(r.status_code))
    r = client.post(
        "/libros/",
        json={
            "isbn": "978-950-00-0005-9",
            "titulo": "Bestiario (nuevo)",
            "precio": "24000.00",
            "stock_inicial": 1,
            "editorial_id": 1,
            "genero_id": 1,
            "autores": [],
        },
        headers={"Cookie": admin_cookie},
    )
    check("C-13 el mismo ISBN se puede volver a cargar -> 201", r.status_code == 201, str(r.status_code))
    r = client.post(
        "/libros/",
        json={
            "isbn": "978-950-00-0005-9",
            "titulo": "Bestiario (otro)",
            "precio": "24000.00",
            "stock_inicial": 1,
            "editorial_id": 1,
            "genero_id": 1,
            "autores": [],
        },
        headers={"Cookie": admin_cookie},
    )
    check("C-13 un segundo vigente con el mismo ISBN -> 409", r.status_code == 409, str(r.status_code))
    r = client.get("/ventas/1", headers={"Cookie": admin_cookie})
    check(
        "C-13 la venta vieja sigue mostrando el libro",
        r.status_code == 200 and len(r.json()["renglones"]) == 2,
        str(r.status_code),
    )

    # =====================================================================
    # C-15: el detalle de una venta no crece con la cantidad de renglones
    # =====================================================================
    def consultas_detalle(venta_id: int) -> int:
        consultas.clear()
        client.get(f"/ventas/{venta_id}", headers={"Cookie": admin_cookie})
        return len([q for q in consultas if q.strip().upper().startswith("SELECT")])

    r = client.post(
        "/ventas/",
        json={
            "cliente_id": 2,
            "renglones": [
                {"libro_id": 1, "cantidad": 1},
                {"libro_id": 3, "cantidad": 1},
            ],
        },
        headers={"Cookie": vendedor_cookie},
    )
    venta_2 = r.json()["id"]
    r = client.post(
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
        headers={"Cookie": vendedor_cookie},
    )
    venta_4 = r.json()["id"]
    consultas_2 = consultas_detalle(venta_2)
    consultas_4 = consultas_detalle(venta_4)
    check(
        "C-15 el detalle usa el mismo número de consultas con 2 y con 4 renglones",
        consultas_2 == consultas_4,
        f"2 renglones: {consultas_2}, 4 renglones: {consultas_4}",
    )

    # =====================================================================
    # PATCH parcial y PATCH del stock
    # =====================================================================
    r = client.patch(
        "/libros/2", json={"titulo": "Antología (edición revisada)"},
        headers={"Cookie": admin_cookie},
    )
    check("PATCH parcial -> 200", r.status_code == 200, str(r.status_code))
    check(
        "PATCH parcial cambia sólo lo enviado",
        r.json()["titulo"] == "Antología (edición revisada)"
        and r.json()["precio"] == "30000.00",
        r.text[:160],
    )
    r = client.patch(
        "/libros/2", json={"stock": 99}, headers={"Cookie": admin_cookie}
    )
    check("C-16 PATCH del stock -> 422", r.status_code == 422, str(r.status_code))

    # =====================================================================
    # RN-15: ningún error devuelve texto interno de la base
    # =====================================================================
    r = client.post(
        "/editoriales/",
        json={"nombre": "Sudamericana", "pais": "Argentina"},
        headers={"Cookie": admin_cookie},
    )
    detalle = r.text.lower()
    check(
        "RN-15 el 409 no filtra el esquema de la base",
        r.status_code == 409
        and "duplicate key" not in detalle
        and "pg_catalog" not in detalle,
        r.text[:160],
    )

print()
if fallos:
    print(f"FALLARON {len(fallos)}: " + "; ".join(fallos))
    sys.exit(1)
print("TODO OK")
