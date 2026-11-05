"""Deja la base en el estado inicial conocido (idempotente).

Uso:
    python scripts/seed.py

Qué carga (son los datos que usan los casos de prueba):

- **Usuarios**: ``admin@example.com`` y ``admin2@example.com`` (ADMIN),
  ``vendedor@example.com`` (VENDEDOR), ``ana@example.com`` (CLIENTE) y
  ``nuevo@example.com`` (VENDEDOR, con el cambio de contraseña obligatorio).
- **Editoriales, géneros y autores**: 3, 3 y 6.
- **Libros**: los cinco del TP, con su stock actual (Rayuela 10, Antología de
  la literatura fantástica 5, Ficciones 8, Respiración artificial 3 y Bestiario
  1).
- **Clientes**: Lucía Fernández (con perfil) y Tomás Ríos (sin usuario), y Ana
  Paz, que sí tiene usuario.
- **La venta 1**: de Lucía, registrada por ``vendedor@example.com``: 1 Rayuela
  y 2 Ficciones, total 69000.00.
- **Movimientos**: un «Stock inicial» por libro y los dos de salida de la venta
  1, de modo que el stock de cada libro coincide con la suma de sus
  movimientos.
- **Historial de seguridad**: una línea con el actor ``SISTEMA``.

Las contraseñas son de mentira y viven sólo en este archivo.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    Usuario,
)
from app.modules.ventas.models import RenglonVenta, Venta  # noqa: F401 (registry)

# Contraseñas de mentira: viven sólo en este archivo.
PASSWORD = "Demo1234!"
PASSWORD_PROVISORIA = "Temporal1234!"

TABLAS = (
    "movimiento_stock",
    "renglon_venta",
    "venta",
    "perfil_cliente",
    "cliente",
    "libro_autor",
    "libro",
    "autor",
    "genero",
    "editorial",
    "evento_seguridad",
    "intento_acceso",
    "asignacion_rol",
    "usuario",
)

# Los cinco libros del TP con su stock actual y su precio.
LIBROS = (
    # (isbn, título, precio, stock final)
    ("978-950-00-0001-1", "Rayuela", Decimal("25000.00"), 10),
    ("978-950-00-0002-8", "Antología de la literatura fantástica", Decimal("30000.00"), 5),
    ("978-950-00-0003-5", "Ficciones", Decimal("22000.00"), 8),
    ("978-950-00-0004-2", "Respiración artificial", Decimal("27000.00"), 3),
    ("978-950-00-0005-9", "Bestiario", Decimal("24000.00"), 1),
)

# El stock inicial de cada libro es su stock final más lo que salió por la
# venta 1 (1 Rayuela y 2 Ficciones): así la suma de los movimientos de cada
# libro coincide con su stock.
STOCK_INICIAL = {
    "978-950-00-0001-1": 11,
    "978-950-00-0002-8": 5,
    "978-950-00-0003-5": 10,
    "978-950-00-0004-2": 3,
    "978-950-00-0005-9": 1,
}


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.SQL_ECHO,
        connect_args=settings.connect_args(),
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    ahora = datetime.now(timezone.utc)

    async with factory() as session:
        # Limpieza total con ids determinísticos (1, 2, 3, ...).
        # TRUNCATE no dispara los disparadores BEFORE UPDATE OR DELETE, así que
        # el reset funciona aunque la tabla sea de sólo agregado.
        await session.execute(
            text(
                "TRUNCATE " + ", ".join(TABLAS) + " RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()

        # --- Usuarios ---------------------------------------------------------
        hash_admin = await hash_password(PASSWORD)
        hash_provisoria = await hash_password(PASSWORD_PROVISORIA)

        admin = Usuario(
            email="admin@example.com",
            nombre="Administrador",
            password_hash=hash_admin,
            activo=True,
            debe_cambiar_password=False,
        )
        admin2 = Usuario(
            email="admin2@example.com",
            nombre="Segunda administradora",
            password_hash=hash_admin,
            activo=True,
            debe_cambiar_password=False,
        )
        vendedor = Usuario(
            email="vendedor@example.com",
            nombre="Vendedor",
            password_hash=hash_admin,
            activo=True,
            debe_cambiar_password=False,
        )
        ana_usuario = Usuario(
            email="ana@example.com",
            nombre="Ana Paz",
            password_hash=hash_admin,
            activo=True,
            debe_cambiar_password=False,
        )
        nuevo = Usuario(
            email="nuevo@example.com",
            nombre="Vendedor nuevo",
            password_hash=hash_provisoria,
            activo=True,
            # Clave provisoria: el grupo protegido le responde 403 hasta que la
            # cambie (RN-06).
            debe_cambiar_password=True,
        )
        session.add_all([admin, admin2, vendedor, ana_usuario, nuevo])
        await session.flush()

        session.add_all(
            [
                AsignacionRol(
                    usuario_id=admin.id,
                    rol="ADMIN",
                    desde=ahora,
                    otorgada_por="SISTEMA",
                ),
                AsignacionRol(
                    usuario_id=admin2.id,
                    rol="ADMIN",
                    desde=ahora,
                    otorgada_por="SISTEMA",
                ),
                AsignacionRol(
                    usuario_id=vendedor.id,
                    rol="VENDEDOR",
                    desde=ahora,
                    otorgada_por="SISTEMA",
                ),
                AsignacionRol(
                    usuario_id=ana_usuario.id,
                    rol="CLIENTE",
                    desde=ahora,
                    otorgada_por="SISTEMA",
                ),
                AsignacionRol(
                    usuario_id=nuevo.id,
                    rol="VENDEDOR",
                    desde=ahora,
                    otorgada_por="SISTEMA",
                ),
            ]
        )

        # --- Editoriales, géneros y autores ------------------------------------
        ed1 = Editorial(nombre="Sudamericana", pais="Argentina")
        ed2 = Editorial(nombre="Anagrama", pais="España")
        ed3 = Editorial(nombre="Seix Barral", pais="España")
        g1 = Genero(nombre="Novela")
        g2 = Genero(nombre="Ensayo")
        g3 = Genero(nombre="Cuento")
        session.add_all([ed1, ed2, ed3, g1, g2, g3])

        a1 = Autor(nombre="Julio Cortázar", nacionalidad="Argentina")
        a2 = Autor(nombre="Ricardo Piglia", nacionalidad="Argentina")
        a3 = Autor(nombre="Adolfo Bioy Casares", nacionalidad="Argentina")
        a4 = Autor(nombre="Silvina Ocampo", nacionalidad="Argentina")
        a5 = Autor(nombre="Jorge Luis Borges", nacionalidad="Argentina")
        a6 = Autor(nombre="Gabriel García Márquez", nacionalidad="Colombia")
        session.add_all([a1, a2, a3, a4, a5, a6])
        await session.flush()

        # --- Clientes ---------------------------------------------------------
        lucia = Cliente(nombre="Lucía Fernández", email="lucia@example.com")
        tomas = Cliente(nombre="Tomás Ríos", email="tomas@example.com")
        ana = Cliente(
            nombre="Ana Paz",
            email="ana@example.com",
            usuario_id=ana_usuario.id,
        )
        session.add_all([lucia, tomas, ana])
        await session.flush()

        session.add(
            PerfilCliente(
                cliente_id=lucia.id,
                telefono="11-5555-0001",
                direccion="Calle Falsa 123",
            )
        )

        # --- Libros -----------------------------------------------------------
        libros: dict[str, Libro] = {}
        for isbn, titulo, precio, stock in LIBROS:
            libro = Libro(
                isbn=isbn,
                titulo=titulo,
                precio=precio,
                stock=0,  # el stock sale de los movimientos (RN-11)
                editorial_id=ed1.id if isbn != "978-950-00-0005-9" else ed3.id,
                genero_id=g1.id if isbn in ("978-950-00-0001-1", "978-950-00-0003-5") else g2.id,
            )
            session.add(libro)
            await session.flush()
            libros[isbn] = libro

        session.add_all(
            [
                LibroAutor(libro_id=libros["978-950-00-0001-1"].id, autor_id=a1.id, rol="autor", orden=1),
                LibroAutor(libro_id=libros["978-950-00-0002-8"].id, autor_id=a5.id, rol="autor", orden=1),
                LibroAutor(libro_id=libros["978-950-00-0002-8"].id, autor_id=a4.id, rol="coautor", orden=2),
                LibroAutor(libro_id=libros["978-950-00-0003-5"].id, autor_id=a2.id, rol="autor", orden=1),
                LibroAutor(libro_id=libros["978-950-00-0004-2"].id, autor_id=a3.id, rol="autor", orden=1),
                LibroAutor(libro_id=libros["978-950-00-0005-9"].id, autor_id=a6.id, rol="autor", orden=1),
            ]
        )
        await session.flush()

        # --- Movimientos de stock inicial -------------------------------------
        # El stock de cada libro es la suma de sus movimientos (RN-11).
        for isbn, _titulo, _precio, _stock in LIBROS:
            session.add(
                MovimientoStock(
                    libro_id=libros[isbn].id,
                    venta_id=None,
                    usuario_id=admin.id,
                    cantidad=STOCK_INICIAL[isbn],
                    motivo="Stock inicial",
                    cuando=ahora,
                )
            )
            libros[isbn].stock = STOCK_INICIAL[isbn]
        await session.flush()

        # --- La venta 1 -------------------------------------------------------
        # De Lucía, registrada por vendedor@example.com: 1 Rayuela y 2 Ficciones.
        # Total 25000 + 2 * 22000 = 69000.
        rayuela = libros["978-950-00-0001-1"]
        ficciones = libros["978-950-00-0003-5"]
        venta = Venta(
            cliente_id=lucia.id,
            fecha=ahora,
            total=Decimal("69000.00"),
        )
        session.add(venta)
        await session.flush()

        session.add_all(
            [
                RenglonVenta(
                    venta_id=venta.id,
                    libro_id=rayuela.id,
                    cantidad=1,
                    precio_unitario=Decimal("25000.00"),
                ),
                RenglonVenta(
                    venta_id=venta.id,
                    libro_id=ficciones.id,
                    cantidad=2,
                    precio_unitario=Decimal("22000.00"),
                ),
            ]
        )

        # Los dos movimientos de salida de la venta 1 (−1 y −2).
        session.add_all(
            [
                MovimientoStock(
                    libro_id=rayuela.id,
                    venta_id=venta.id,
                    usuario_id=vendedor.id,
                    cantidad=-1,
                    motivo="Venta",
                    cuando=ahora,
                ),
                MovimientoStock(
                    libro_id=ficciones.id,
                    venta_id=venta.id,
                    usuario_id=vendedor.id,
                    cantidad=-2,
                    motivo="Venta",
                    cuando=ahora,
                ),
            ]
        )
        rayuela.stock -= 1
        ficciones.stock -= 2

        # --- Historial de seguridad -------------------------------------------
        session.add(
            EventoSeguridad(
                cuando=ahora,
                actor="SISTEMA",
                accion="Carga de los datos iniciales",
            )
        )

        await session.commit()

    await engine.dispose()
    print(
        "Seed OK: 5 usuarios, 3 editoriales, 3 generos, 6 autores, 5 libros, "
        "3 clientes, 1 venta, 7 movimientos y 1 evento de seguridad."
    )


if __name__ == "__main__":
    asyncio.run(main())
