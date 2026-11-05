"""Unit of Work del módulo ventas.

El registro de una venta toca **cuatro** clases de escritura (venta,
renglones, stock y movimientos): todas en la misma transacción, que es lo que
agrupa este Unit of Work (RN-10).
"""

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.models import Cliente
from app.modules.clientes.repository import ClienteRepository
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.libros.repository import LibroRepository, MovimientoStockRepository
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.repository import RenglonVentaRepository, VentaRepository
from app.modules.usuarios.models import AsignacionRol
from app.modules.usuarios.repository import AsignacionRolRepository


class VentasUnitOfWork(UnitOfWork):
    """Repositorios que las operaciones del módulo ventas necesitan.

    ``libros`` y ``movimientos`` están porque registrar una venta descuenta el
    stock de cada libro y deja un movimiento por renglón (RN-10). ``clientes``
    está porque hay que comprobar que el cliente existe y que un cliente sólo
    ve sus propias ventas (RN-14). ``roles`` está porque la comprobación de
    dueño compara los roles **vigentes** del usuario (RN-04).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.ventas = VentaRepository(session, Venta)
        self.renglones = RenglonVentaRepository(session, RenglonVenta)
        self.libros = LibroRepository(session, Libro)
        self.movimientos = MovimientoStockRepository(session, MovimientoStock)
        self.clientes = ClienteRepository(session, Cliente)
        self.roles = AsignacionRolRepository(session, AsignacionRol)
