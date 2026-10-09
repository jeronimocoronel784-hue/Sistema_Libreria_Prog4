"""Lógica del módulo autores."""

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select

from app.modules.autores.models import Autor
from app.modules.autores.schemas import AutorCreate, AutorUpdate
from app.modules.libros.models import LibroAutor

_MSJ_CONFLICTO = "No se pudo guardar el autor: datos inválidos."


async def crear(session: AsyncSession, data: AutorCreate) -> Autor:
    autor = Autor(nombre=data.nombre, nacionalidad=data.nacionalidad)
    session.add(autor)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=_MSJ_CONFLICTO)
    await session.refresh(autor)
    return autor


async def listar(
    session: AsyncSession, limit: int = 20, offset: int = 0
) -> list[Autor]:
    res = await session.execute(select(Autor).offset(offset).limit(limit))
    return list(res.scalars().all())


async def obtener(session: AsyncSession, autor_id: int) -> Autor:
    autor = await session.get(Autor, autor_id)
    if autor is None:
        raise HTTPException(status_code=404, detail="Autor no encontrado.")
    return autor


async def actualizar(
    session: AsyncSession, autor_id: int, data: AutorUpdate
) -> Autor:
    autor = await obtener(session, autor_id)
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(autor, campo, valor)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=_MSJ_CONFLICTO)
    await session.refresh(autor)
    return autor


async def libros_del_autor(session: AsyncSession, autor_id: int) -> list[LibroAutor]:
    """Autorías del autor con su libro precargado (número fijo de consultas)."""
    await obtener(session, autor_id)
    res = await session.execute(
        select(LibroAutor)
        .where(LibroAutor.autor_id == autor_id)
        .options(joinedload(LibroAutor.libro))
    )
    return list(res.scalars().all())
