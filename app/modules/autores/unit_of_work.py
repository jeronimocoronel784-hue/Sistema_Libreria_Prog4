"""Unit of Work del módulo autores."""

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.autores.models import Autor
from app.modules.autores.repository import AutorRepository


class AutoresUnitOfWork(UnitOfWork):
    """Repositorios que las operaciones del módulo autores necesitan.

    La sesión es siempre la misma para todos: los repositorios no crean
    sesiones ni confirman.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.autores = AutorRepository(session, Autor)
