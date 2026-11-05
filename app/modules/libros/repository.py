"""Repositorios del módulo libros.

La precarga se declara **adentro del método** que la necesita (regla dura):
``get_detalle`` trae editorial, género y autores; ``listar`` trae editorial y
género. Ninguna lectura depende de carga perezosa.
"""

from typing import Sequence

from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select

from app.core.paginacion import Page, PageParams
from app.core.repository import BaseRepository, SoftDeleteRepository
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock


class LibroRepository(SoftDeleteRepository[Libro]):
    """Acceso a la tabla ``libro``.

    Es un ``SoftDeleteRepository``: las lecturas normales excluyen los libros
    dados de baja y ``soft_delete`` anota ``borrado_en`` sin borrar la fila
    (las ventas viejas la siguen mostrando).
    """

    _orden_por = (Libro.id,)

    async def get_detalle(self, libro_id: int) -> Libro | None:
        """Libro con editorial, género y autores, en un número fijo de consultas."""
        statement = (
            select(Libro)
            .where(Libro.id == libro_id, Libro.borrado_en.is_(None))
            .options(
                joinedload(Libro.editorial),
                joinedload(Libro.genero),
                selectinload(Libro.autorias).joinedload(LibroAutor.autor),
            )
        )
        return (await self.session.exec(statement)).first()

    async def get_detalle_including_deleted(self, libro_id: int) -> Libro | None:
        """Como ``get_detalle`` pero también devuelve los libros dados de baja."""
        statement = (
            select(Libro)
            .where(Libro.id == libro_id)
            .options(
                joinedload(Libro.editorial),
                joinedload(Libro.genero),
                selectinload(Libro.autorias).joinedload(LibroAutor.autor),
            )
        )
        return (await self.session.exec(statement)).first()

    async def obtener_varios_including_deleted(
        self, ids: Sequence[int]
    ) -> dict[int, Libro]:
        """Libros por id, **incluyendo los dados de baja**, en una sola consulta.

        La usa el registro de una venta: un libro dado de baja no se puede
        vender, pero la comprobación tiene que poder distinguir "no existe" de
        "está dado de baja" (RN-13).
        """
        if not ids:
            return {}
        statement = select(Libro).where(Libro.id.in_(list(ids)))
        libros = (await self.session.exec(statement)).all()
        return {libro.id: libro for libro in libros}

    async def listar(
        self,
        params: PageParams,
        titulo: str | None = None,
        genero_id: int | None = None,
    ) -> Page[Libro]:
        """Listado paginado del catálogo, con los mismos filtros que el total.

        Los dados de baja no aparecen: el catálogo es lo que está vigente.
        La búsqueda por título usa **parámetro ligado** (``ilike``), nunca
        concatenación de texto del usuario en el SQL.
        """
        filtros = []
        if titulo:
            filtros.append(Libro.titulo.ilike(f"%{titulo}%"))
        if genero_id is not None:
            filtros.append(Libro.genero_id == genero_id)

        total = await self.count(*filtros)

        statement = (
            select(Libro)
            .where(*self._filtros(filtros))
            .options(joinedload(Libro.editorial), joinedload(Libro.genero))
            .order_by(*self._orden_por)
            .offset(params.offset)
            .limit(params.size)
        )
        items = (await self.session.exec(statement)).all()
        return Page.create(items=items, total=total, params=params)


class LibroAutorRepository(BaseRepository[LibroAutor]):
    """Acceso a la tabla de asociación ``libro_autor``."""

    async def agregar(
        self, libro_id: int, autor_id: int, rol: str, orden: int
    ) -> LibroAutor:
        """Agrega una autoría y hace ``flush()``. No confirma."""
        return await self.add(
            LibroAutor(
                libro_id=libro_id, autor_id=autor_id, rol=rol, orden=orden
            )
        )


class MovimientoStockRepository(BaseRepository[MovimientoStock]):
    """Acceso a ``movimiento_stock``: el punto único de escritura del stock.

    La tabla es de **sólo agregado**: ningún repositorio (ni ningún servicio)
    modifica o borra sus filas. Sólo se agregan.
    """

    _orden_por = (MovimientoStock.id,)

    async def listar_por_libro(
        self, libro_id: int, params: PageParams
    ) -> Page[MovimientoStock]:
        """Movimientos de un libro, paginados."""
        total = await self.count(MovimientoStock.libro_id == libro_id)
        statement = (
            select(MovimientoStock)
            .where(MovimientoStock.libro_id == libro_id)
            .order_by(*self._orden_por)
            .offset(params.offset)
            .limit(params.size)
        )
        items = (await self.session.exec(statement)).all()
        return Page.create(items=items, total=total, params=params)

    async def sumar_cantidades(self, libro_id: int) -> int:
        """Suma de las cantidades de los movimientos de un libro.

        Es el stock del libro: la igualdad ``stock == suma de movimientos`` es
        la que se verifica después de cada venta.
        """
        total = await self.session.scalar(
            select(func.coalesce(func.sum(MovimientoStock.cantidad), 0)).where(
                MovimientoStock.libro_id == libro_id
            )
        )
        return int(total or 0)
