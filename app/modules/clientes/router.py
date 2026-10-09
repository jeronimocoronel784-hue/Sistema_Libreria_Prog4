"""Rutas del módulo clientes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.clientes import service
from app.modules.clientes.schemas import (
    ClienteConPerfil,
    ClienteCreate,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
    VentaResumen,
)
from app.modules.clientes.schemas import ClienteRead

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.post("/", response_model=ClienteRead, status_code=201)
async def crear_cliente(
    data: ClienteCreate, session: AsyncSession = Depends(get_session)
) -> service.Cliente:
    return await service.crear(session, data)


@router.get("/", response_model=list[ClienteRead])
async def listar_clientes(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list:
    return await service.listar(session, limit, offset)


@router.get("/{cliente_id}", response_model=ClienteConPerfil)
async def obtener_cliente(
    cliente_id: int, session: AsyncSession = Depends(get_session)
) -> service.Cliente:
    return await service.obtener_con_perfil(session, cliente_id)


@router.patch("/{cliente_id}", response_model=ClienteConPerfil)
async def actualizar_cliente(
    cliente_id: int,
    data: ClienteUpdate,
    session: AsyncSession = Depends(get_session),
) -> service.Cliente:
    return await service.actualizar(session, cliente_id, data)


@router.post("/{cliente_id}/perfil", response_model=PerfilRead, status_code=201)
async def crear_perfil(
    cliente_id: int,
    data: PerfilCreate,
    session: AsyncSession = Depends(get_session),
) -> service.PerfilCliente:
    return await service.crear_perfil(session, cliente_id, data)


@router.get("/{cliente_id}/ventas", response_model=list[VentaResumen])
async def ventas_del_cliente(
    cliente_id: int, session: AsyncSession = Depends(get_session)
) -> list:
    ventas = await service.ventas_del_cliente(session, cliente_id)
    return [
        {
            "id": v.id,
            "fecha": v.fecha.isoformat() if v.fecha is not None else None,
            "total": v.total,
        }
        for v in ventas
    ]
