"""Repositorios del módulo autores.

La precarga se declara **adentro del método** que la necesita (regla dura):
``listar_autorias`` trae el libro de cada autoría.
"""

from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlmodel import select

from app.core.paginacion import Page, PageParams
from app.core.repository import BaseRepository
from app.modules.autores.models import Autor
from app.modules.libros.models import LibroAutor


class AutorRepository(BaseRepository[Autor]):
    """Acceso a la tabla ``autor``."""

    _orden_por = (Autor.id,)

    async def listar_autorias(
        self, autor_id: int, params: PageParams
    ) -> Page[LibroAutor]:
        """Autorías del autor, paginadas, con su libro precargado.

        Dos consultas fijas (total + página) y ninguna carga perezosa.
        """
        total = int(
            await self.session.scalar(
                select(func.count())
                .select_from(LibroAutor)
                .where(LibroAutor.autor_id == autor_id)
            )
            or 0
        )

        statement = (
            select(LibroAutor)
            .where(LibroAutor.autor_id == autor_id)
            .options(joinedload(LibroAutor.libro))
            .order_by(LibroAutor.orden, LibroAutor.id)
            .offset(params.offset)
            .limit(params.size)
        )
        items = (await self.session.exec(statement)).all()
        return Page.create(items=items, total=total, params=params)
