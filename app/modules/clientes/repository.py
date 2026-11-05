"""Repositorios del módulo clientes.

La precarga se declara **adentro del método** que la necesita (regla dura).
"""

from sqlalchemy.orm import joinedload
from sqlmodel import select

from app.core.paginacion import Page, PageParams
from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.ventas.models import Venta


class ClienteRepository(BaseRepository[Cliente]):
    """Acceso a la tabla ``cliente``."""

    _orden_por = (Cliente.id,)

    async def get_by_email(self, email: str) -> Cliente | None:
        """Cliente por correo (el correo es UNIQUE en la base)."""
        statement = select(Cliente).where(Cliente.email == email)
        return (await self.session.exec(statement)).first()

    async def get_by_usuario(self, usuario_id: int) -> Cliente | None:
        """Cliente que corresponde a un usuario de acceso (UNIQUE)."""
        statement = select(Cliente).where(Cliente.usuario_id == usuario_id)
        return (await self.session.exec(statement)).first()

    async def get_con_perfil(self, cliente_id: int) -> Cliente | None:
        """Cliente con su perfil precargado (relación uno a uno)."""
        statement = (
            select(Cliente)
            .where(Cliente.id == cliente_id)
            .options(joinedload(Cliente.perfil))
        )
        return (await self.session.exec(statement)).first()

    async def listar_ventas(
        self, cliente_id: int, params: PageParams
    ) -> Page[Venta]:
        """Ventas de un cliente, paginadas."""
        total = await self.count(Venta.cliente_id == cliente_id)
        statement = (
            select(Venta)
            .where(Venta.cliente_id == cliente_id)
            .order_by(Venta.id)
            .offset(params.offset)
            .limit(params.size)
        )
        items = (await self.session.exec(statement)).all()
        return Page.create(items=items, total=total, params=params)


class PerfilClienteRepository(BaseRepository[PerfilCliente]):
    """Acceso a la tabla ``perfil_cliente`` (uno a uno con ``cliente``)."""
