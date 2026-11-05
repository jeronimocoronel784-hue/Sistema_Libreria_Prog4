"""Unit of Work del módulo editoriales."""

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.editoriales.models import Editorial
from app.modules.editoriales.repository import EditorialRepository
from app.modules.libros.models import Libro
from app.modules.libros.repository import LibroRepository


class EditorialesUnitOfWork(UnitOfWork):
    """Repositorios que las operaciones del módulo editoriales necesitan.

    ``libros`` está porque la subruta ``GET /editoriales/{id}/libros`` devuelve
    libros: la ruta es de la editorial, los datos son del catálogo.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.editoriales = EditorialRepository(session, Editorial)
        self.libros = LibroRepository(session, Libro)
