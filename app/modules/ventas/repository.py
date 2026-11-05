"""Repositorios del módulo ventas.

La precarga se declara **adentro del método** que la necesita (regla dura):
``get_detalle`` trae el cliente, los renglones y el libro de cada renglón
—incluso si el libro está dado de baja— en un número fijo de consultas.
"""

from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select

from app.core.paginacion import Page, PageParams
from app.core.repository import BaseRepository
from app.modules.ventas.models import RenglonVenta, Venta


class VentaRepository(BaseRepository[Venta]):
    """Acceso a la tabla ``venta``. Las ventas son inmutables: no hay update."""

    _orden_por = (Venta.id,)

    async def get_detalle(self, venta_id: int) -> Venta | None:
        """Venta con cliente, renglones y libros, en un número fijo de consultas.

        El libro de un renglón se carga aunque esté dado de baja: la venta
        vieja tiene que seguir mostrando el título.
        """
        statement = (
            select(Venta)
            .where(Venta.id == venta_id)
            .options(
                joinedload(Venta.cliente),
                selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
            )
        )
        return (await self.session.exec(statement)).first()

    async def listar(self, params: PageParams) -> Page[Venta]:
        """Listado paginado de ventas."""
        total = await self.count()
        statement = (
            select(Venta)
            .order_by(*self._orden_por)
            .offset(params.offset)
            .limit(params.size)
        )
        items = (await self.session.exec(statement)).all()
        return Page.create(items=items, total=total, params=params)

    async def listar_de_cliente(self, cliente_id: int, params: PageParams) -> Page[Venta]:
        """Ventas de un cliente, paginadas."""
        total = await self.count(Venta.cliente_id == cliente_id)
        statement = (
            select(Venta)
            .where(Venta.cliente_id == cliente_id)
            .order_by(*self._orden_por)
            .offset(params.offset)
            .limit(params.size)
        )
        items = (await self.session.exec(statement)).all()
        return Page.create(items=items, total=total, params=params)


class RenglonVentaRepository(BaseRepository[RenglonVenta]):
    """Acceso a la tabla ``renglon_venta`` (composición de la venta)."""
