"""Unit of Work del módulo clientes."""

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.repository import (
    ClienteRepository,
    PerfilClienteRepository,
)
from app.modules.ventas.models import Venta
from app.modules.ventas.repository import VentaRepository


class ClientesUnitOfWork(UnitOfWork):
    """Repositorios que las operaciones del módulo clientes necesitan.

    ``ventas`` está porque ``GET /clientes/{id}/ventas`` devuelve ventas.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.clientes = ClienteRepository(session, Cliente)
        self.perfiles = PerfilClienteRepository(session, PerfilCliente)
        self.ventas = VentaRepository(session, Venta)
