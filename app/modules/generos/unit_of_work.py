"""Unit of Work del módulo géneros."""

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.generos.models import Genero
from app.modules.generos.repository import GeneroRepository
from app.modules.libros.models import Libro
from app.modules.libros.repository import LibroRepository


class GenerosUnitOfWork(UnitOfWork):
    """Repositorios que las operaciones del módulo géneros necesitan.

    ``libros`` está porque la subruta ``GET /generos/{id}/libros`` devuelve
    libros: la ruta es del género, los datos son del catálogo.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.generos = GeneroRepository(session, Genero)
        self.libros = LibroRepository(session, Libro)
