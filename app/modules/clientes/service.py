"""Lógica del módulo clientes (incluye PerfilCliente uno a uno)."""

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlmodel import select

from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteUpdate,
    PerfilCreate,
)
from app.modules.ventas.models import Venta

_MSJ_CONFLICTO = "No se pudo guardar el cliente: el email ya existe."
_MSJ_CONFLICTO_PERFIL = (
    "No se pudo crear el perfil: el cliente ya tiene uno o los datos son inválidos."
)


async def crear(session: AsyncSession, data: ClienteCreate) -> Cliente:
    cliente = Cliente(nombre=data.nombre, email=data.email)
    session.add(cliente)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=_MSJ_CONFLICTO)
    await session.refresh(cliente)
    return cliente


async def listar(
    session: AsyncSession, limit: int = 20, offset: int = 0
) -> list[Cliente]:
    # sin relaciones en respuesta: el listado no precarga a propósito.
    res = await session.execute(select(Cliente).offset(offset).limit(limit))
    return list(res.scalars().all())


async def obtener_con_perfil(session: AsyncSession, cliente_id: int) -> Cliente:
    res = await session.execute(
        select(Cliente)
        .where(Cliente.id == cliente_id)
        .options(joinedload(Cliente.perfil))
    )
    cliente = res.scalars().first()
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return cliente


async def actualizar(
    session: AsyncSession, cliente_id: int, data: ClienteUpdate
) -> Cliente:
    cliente = await obtener_con_perfil(session, cliente_id)
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=_MSJ_CONFLICTO)
    return await obtener_con_perfil(session, cliente_id)


async def crear_perfil(
    session: AsyncSession, cliente_id: int, data: PerfilCreate
) -> PerfilCliente:
    res = await session.execute(select(Cliente).where(Cliente.id == cliente_id))
    if res.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    perfil = PerfilCliente(
        cliente_id=cliente_id, telefono=data.telefono, direccion=data.direccion
    )
    session.add(perfil)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=_MSJ_CONFLICTO_PERFIL)
    await session.refresh(perfil)
    return perfil


async def ventas_del_cliente(
    session: AsyncSession, cliente_id: int, limit: int = 20, offset: int = 0
) -> list[Venta]:
    res = await session.execute(select(Cliente).where(Cliente.id == cliente_id))
    if res.scalars().first() is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    res = await session.execute(
        select(Venta)
        .where(Venta.cliente_id == cliente_id)
        .order_by(Venta.id)
        .offset(offset)
        .limit(limit)
    )
    return list(res.scalars().all())
