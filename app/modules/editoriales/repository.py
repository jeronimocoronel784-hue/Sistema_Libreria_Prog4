"""Repositorios del módulo editoriales.

La precarga se declara **adentro del método** que la necesita (regla dura).
"""

from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlmodel import select

from app.core.paginacion import Page, PageParams
from app.core.repository import BaseRepository
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro


class EditorialRepository(BaseRepository[Editorial]):
    """Acceso a la tabla ``editorial``."""

    _orden_por = (Editorial.id,)

    async def listar_libros(
        self, editorial_id: int, params: PageParams
    ) -> Page[Libro]:
        """Libros de la editorial, paginados, con editorial y género precargados."""
        total = int(
            await self.session.scalar(
                select(func.count())
                .select_from(Libro)
                .where(Libro.editorial_id == editorial_id, Libro.borrado_en.is_(None))
            )
            or 0
        )

        statement = (
            select(Libro)
            .where(Libro.editorial_id == editorial_id, Libro.borrado_en.is_(None))
            .options(joinedload(Libro.editorial), joinedload(Libro.genero))
            .order_by(Libro.id)
            .offset(params.offset)
            .limit(params.size)
        )
        items = (await self.session.exec(statement)).all()
        return Page.create(items=items, total=total, params=params)
