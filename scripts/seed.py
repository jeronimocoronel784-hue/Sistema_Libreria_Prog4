"""Deja la base en un estado inicial conocido (idempotente).

Uso:
    python scripts/seed.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import SQL_ECHO, get_database_url
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor
from app.modules.ventas.models import RenglonVenta, Venta  # noqa: F401 (completa el registry)


async def main() -> None:
    engine = create_async_engine(get_database_url(), echo=SQL_ECHO)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        # Limpieza total con ids determinísticos (1, 2, 3, ...).
        await session.execute(
            text(
                "TRUNCATE editorial, genero, autor, libro, libro_autor, "
                "cliente, perfil_cliente, venta, renglon_venta "
                "RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()

        ed1 = Editorial(nombre="Sudamericana", pais="Argentina")
        ed2 = Editorial(nombre="Anagrama", pais="España")
        g1 = Genero(nombre="Novela")
        g2 = Genero(nombre="Ensayo")
        a1 = Autor(nombre="Julio Cortázar", nacionalidad="Argentina")
        a2 = Autor(nombre="Ricardo Piglia", nacionalidad="Argentina")
        a3 = Autor(nombre="Adolfo Bioy Casares", nacionalidad="Argentina")
        a4 = Autor(nombre="Silvina Ocampo", nacionalidad="Argentina")
        c1 = Cliente(nombre="Ana López", email="ana@example.com")
        c2 = Cliente(nombre="Tomás Ríos", email="tomas@example.com")
        session.add_all([ed1, ed2, g1, g2, a1, a2, a3, a4, c1, c2])
        await session.flush()

        session.add(PerfilCliente(cliente_id=c1.id, telefono="11-5555-0001",
                                  direccion="Calle Falsa 123"))
        l1 = Libro(isbn="978-950-00-0001-1", titulo="Rayuela",
                   precio=Decimal("25000.00"), stock=10,
                   editorial_id=ed1.id, genero_id=g1.id)
        l2 = Libro(isbn="978-950-00-0002-8", titulo="Respiración artificial",
                   precio=Decimal("27000.00"), stock=5,
                   editorial_id=ed1.id, genero_id=g1.id)
        l3 = Libro(isbn="978-950-00-0003-5", titulo="Los que aman, odian",
                   precio=Decimal("21000.00"), stock=4,
                   editorial_id=ed1.id, genero_id=g1.id)
        l4 = Libro(isbn="978-950-00-0004-2", titulo="Ensayos sobre la lectura",
                   precio=Decimal("15000.00"), stock=7,
                   editorial_id=ed2.id, genero_id=g2.id)
        session.add_all([l1, l2, l3, l4])
        await session.flush()

        session.add_all(
            [
                LibroAutor(libro_id=l1.id, autor_id=a1.id, rol="autor", orden=1),
                LibroAutor(libro_id=l2.id, autor_id=a2.id, rol="autor", orden=1),
                LibroAutor(libro_id=l3.id, autor_id=a3.id, rol="coautor", orden=1),
                LibroAutor(libro_id=l3.id, autor_id=a4.id, rol="coautor", orden=2),
                LibroAutor(libro_id=l4.id, autor_id=a2.id, rol="autor", orden=1),
            ]
        )
        await session.commit()
    await engine.dispose()
    print("Seed OK: 2 editoriales, 2 generos, 4 autores, 4 libros, 2 clientes.")


if __name__ == "__main__":
    asyncio.run(main())
