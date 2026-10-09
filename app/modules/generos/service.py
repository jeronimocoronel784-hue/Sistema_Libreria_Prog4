"""Lógica del módulo generos."""

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlmodel import select

from app.modules.generos.models import Genero
from app.modules.generos.schemas import GeneroCreate
from app.modules.libros.models import Libro

_MSJ_CONFLICTO = "No se pudo guardar el género: el nombre ya existe."


async def crear(session: AsyncSession, data: GeneroCreate) -> Genero:
    genero = Genero(nombre=data.nombre)
    session.add(genero)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=_MSJ_CONFLICTO)
    await session.refresh(genero)
    return genero


async def listar(
    session: AsyncSession, limit: int = 20, offset: int = 0
) -> list[Genero]:
    res = await session.execute(select(Genero).offset(offset).limit(limit))
    return list(res.scalars().all())


async def obtener(session: AsyncSession, genero_id: int) -> Genero:
    genero = await session.get(Genero, genero_id)
    if genero is None:
        raise HTTPException(status_code=404, detail="Género no encontrado.")
    return genero


async def libros_del_genero(session: AsyncSession, genero_id: int) -> list[Libro]:
    await obtener(session, genero_id)
    res = await session.execute(
        select(Libro)
        .where(Libro.genero_id == genero_id)
        .options(joinedload(Libro.editorial), joinedload(Libro.genero))
    )
    return list(res.scalars().all())
