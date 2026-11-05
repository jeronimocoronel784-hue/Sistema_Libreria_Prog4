"""Lógica del módulo clientes (incluye PerfilCliente, uno a uno).

El servicio recibe el Unit of Work y lo abre con ``async with``; nunca lo
construye (lo hace el router, con una dependencia).
"""

from sqlalchemy.exc import IntegrityError

from app.core.errors import Conflicto, RecursoNoEncontrado
from app.core.paginacion import Page, PageParams
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteUpdate,
    PerfilCreate,
)
from app.modules.clientes.unit_of_work import ClientesUnitOfWork

_MSJ_CONFLICTO = "No se pudo guardar el cliente: el email ya existe."
_MSJ_CONFLICTO_PERFIL = (
    "No se pudo crear el perfil: el cliente ya tiene uno o los datos son inválidos."
)


async def crear(uow: ClientesUnitOfWork, data: ClienteCreate) -> Cliente:
    """Alta de cliente (en el mostrador). La unicidad la garantiza la base."""
    cliente = Cliente(nombre=data.nombre, email=data.email)
    try:
        async with uow:
            await uow.clientes.add(cliente)
    except IntegrityError:
        raise Conflicto(_MSJ_CONFLICTO) from None
    return cliente


async def listar(uow: ClientesUnitOfWork, params: PageParams) -> Page[Cliente]:
    """Listado paginado de clientes."""
    async with uow:
        return await uow.clientes.list_page(params)


async def obtener_con_perfil(
    uow: ClientesUnitOfWork, cliente_id: int
) -> Cliente:
    """Cliente con su perfil precargado. 404 si no existe."""
    async with uow:
        cliente = await uow.clientes.get_con_perfil(cliente_id)
    if cliente is None:
        raise RecursoNoEncontrado("el cliente", cliente_id)
    return cliente


async def actualizar(
    uow: ClientesUnitOfWork, cliente_id: int, data: ClienteUpdate
) -> Cliente:
    """PATCH parcial: sólo se aplican los campos enviados."""
    async with uow:
        cliente = await uow.clientes.get_con_perfil(cliente_id)
        if cliente is None:
            raise RecursoNoEncontrado("el cliente", cliente_id)
        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(cliente, campo, valor)
        try:
            await uow.clientes.update(cliente)
        except IntegrityError:
            raise Conflicto(_MSJ_CONFLICTO) from None
    return cliente


async def crear_perfil(
    uow: ClientesUnitOfWork, cliente_id: int, data: PerfilCreate
) -> PerfilCliente:
    """Alta del perfil de un cliente (uno a uno). 404 si el cliente no existe."""
    async with uow:
        cliente = await uow.clientes.get_by_id(cliente_id)
        if cliente is None:
            raise RecursoNoEncontrado("el cliente", cliente_id)
        perfil = PerfilCliente(
            cliente_id=cliente_id, telefono=data.telefono, direccion=data.direccion
        )
        try:
            await uow.perfiles.add(perfil)
        except IntegrityError:
            raise Conflicto(_MSJ_CONFLICTO_PERFIL) from None
    return perfil


async def ventas_del_cliente(
    uow: ClientesUnitOfWork, cliente_id: int, params: PageParams
) -> Page:
    """Ventas de un cliente, paginadas. 404 si el cliente no existe."""
    async with uow:
        cliente = await uow.clientes.get_by_id(cliente_id)
        if cliente is None:
            raise RecursoNoEncontrado("el cliente", cliente_id)
        pagina = await uow.clientes.listar_ventas(cliente_id, params)

    return Page.create(
        items=[
            {"id": v.id, "fecha": v.fecha, "total": v.total} for v in pagina.items
        ],
        total=pagina.total,
        params=params,
    )
