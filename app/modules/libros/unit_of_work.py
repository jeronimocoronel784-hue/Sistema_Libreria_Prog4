"""Unit of Work del módulo libros."""

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock
from app.modules.libros.repository import (
    LibroRepository,
    LibroAutorRepository,
    MovimientoStockRepository,
)


class LibrosUnitOfWork(UnitOfWork):
    """Repositorios que las operaciones del módulo libros necesitan.

    ``movimientos`` está porque el stock sólo cambia a través de movimientos
    (RN-11) y porque el alta, la reposición y la venta los escriben.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.libros = LibroRepository(session, Libro)
        self.autorias = LibroAutorRepository(session, LibroAutor)
        self.movimientos = MovimientoStockRepository(session, MovimientoStock)
