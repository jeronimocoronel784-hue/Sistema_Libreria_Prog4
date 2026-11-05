"""Unit of Work del módulo de acceso.

``clientes`` está porque el auto-registro crea el usuario, su rol CLIENTE y su
ficha de cliente en **una sola transacción** (RN-02): o quedan las tres filas,
o ninguna.
"""

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.models import Cliente
from app.modules.clientes.repository import ClienteRepository
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Usuario,
)
from app.modules.usuarios.repository import (
    AsignacionRolRepository,
    EventoSeguridadRepository,
    IntentoAccesoRepository,
    UsuarioRepository,
)


class UsuariosUnitOfWork(UnitOfWork):
    """Repositorios que las operaciones del módulo de acceso necesitan."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.usuarios = UsuarioRepository(session, Usuario)
        self.roles = AsignacionRolRepository(session, AsignacionRol)
        self.intentos = IntentoAccesoRepository(session, IntentoAcceso)
        self.eventos = EventoSeguridadRepository(session, EventoSeguridad)
        self.clientes = ClienteRepository(session, Cliente)
