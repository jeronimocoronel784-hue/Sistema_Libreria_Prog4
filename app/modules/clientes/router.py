"""Rutas del módulo clientes.

Todas van en el grupo **protegido**: exigen sesión y el control de cambio
obligatorio, y además rol VENDEDOR o ADMIN.
"""

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.dependencies import UsuarioActual, requiere_rol
from app.core.paginacion import Page, PageParamsDep
from app.modules.clientes import service
from app.modules.clientes.schemas import (
    ClienteConPerfil,
    ClienteCreate,
    ClienteRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
)
from app.modules.clientes.unit_of_work import ClientesUnitOfWork

router = APIRouter(prefix="/clientes", tags=["clientes"])


def get_clientes_uow(
    session: AsyncSession = Depends(get_session),
) -> ClientesUnitOfWork:
    """Construye el Unit of Work de clientes con la sesión de la petición."""
    return ClientesUnitOfWork(session)


@router.post("/", response_model=ClienteRead, status_code=201)
async def crear_cliente(
    data: ClienteCreate,
    personal: UsuarioActual = Depends(requiere_rol("ADMIN", "VENDEDOR")),
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> dict:
    """Alta de cliente en el mostrador. 201; 409 si el email ya existe; 422."""
    cliente = await service.crear(uow, data)
    return cliente.model_dump()


@router.get("/", response_model=Page[ClienteRead])
async def listar_clientes(
    params: PageParamsDep,
    personal: UsuarioActual = Depends(requiere_rol("ADMIN", "VENDEDOR")),
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> dict:
    """Listado paginado de clientes. 200; 422 si el paging no cumple el contrato."""
    pagina = await service.listar(uow, params)
    return pagina.model_dump()


@router.get("/{cliente_id}", response_model=ClienteConPerfil)
async def obtener_cliente(
    cliente_id: int,
    personal: UsuarioActual = Depends(requiere_rol("ADMIN", "VENDEDOR")),
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> dict:
    """Cliente con su perfil. 200; 404 si no existe; 409; 422."""
    cliente = await service.obtener_con_perfil(uow, cliente_id)
    return {
        "id": cliente.id,
        "nombre": cliente.nombre,
        "email": cliente.email,
        "perfil": (
            {
                "id": cliente.perfil.id,
                "cliente_id": cliente.perfil.cliente_id,
                "telefono": cliente.perfil.telefono,
                "direccion": cliente.perfil.direccion,
            }
            if cliente.perfil is not None
            else None
        ),
    }


@router.patch("/{cliente_id}", response_model=ClienteConPerfil)
async def actualizar_cliente(
    cliente_id: int,
    data: ClienteUpdate,
    personal: UsuarioActual = Depends(requiere_rol("ADMIN", "VENDEDOR")),
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> dict:
    """PATCH parcial del cliente. 200; 404; 409; 422."""
    await service.actualizar(uow, cliente_id, data)
    cliente = await service.obtener_con_perfil(uow, cliente_id)
    return {
        "id": cliente.id,
        "nombre": cliente.nombre,
        "email": cliente.email,
        "perfil": (
            {
                "id": cliente.perfil.id,
                "cliente_id": cliente.perfil.cliente_id,
                "telefono": cliente.perfil.telefono,
                "direccion": cliente.perfil.direccion,
            }
            if cliente.perfil is not None
            else None
        ),
    }


@router.post("/{cliente_id}/perfil", response_model=PerfilRead, status_code=201)
async def crear_perfil(
    cliente_id: int,
    data: PerfilCreate,
    personal: UsuarioActual = Depends(requiere_rol("ADMIN", "VENDEDOR")),
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> dict:
    """Alta del perfil del cliente (uno a uno). 201; 404; 409."""
    perfil = await service.crear_perfil(uow, cliente_id, data)
    return perfil.model_dump()


@router.get("/{cliente_id}/ventas")
async def ventas_del_cliente(
    cliente_id: int,
    params: PageParamsDep,
    personal: UsuarioActual = Depends(requiere_rol("ADMIN", "VENDEDOR")),
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> dict:
    """Ventas del cliente, paginadas. 200; 404 si el cliente no existe."""
    pagina = await service.ventas_del_cliente(uow, cliente_id, params)
    return pagina.model_dump()
