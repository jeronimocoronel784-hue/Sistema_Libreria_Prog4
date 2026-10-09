"""Lógica del módulo editoriales."""

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload, joinedload

from app.modules.editoriales.models import Editorial
from app.modules.editoriales.schemas import EditorialCreate, EditorialUpdate
from app.modules.libros.models import Libro

_MSJ_CONFLICTO = "No se pudo guardar la editorial: el nombre ya existe."


async def crear(session: AsyncSession, data: EditorialCreate) -> Editorial:
    editorial = Editorial(nombre=data.nombre, pais=data.pais)
    session.add(editorial)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=_MSJ_CONFLICTO)
    await session.refresh(editorial)
    return editorial


async def listar(
    session: AsyncSession, limit: int = 20, offset: int = 0
) -> list[Editorial]:
    res = await session.execute(select(Editorial).offset(offset).limit(limit))
    return list(res.scalars().all())


async def obtener(session: AsyncSession, editorial_id: int) -> Editorial:
    editorial = await session.get(Editorial, editorial_id)
    if editorial is None:
        raise HTTPException(status_code=404, detail="Editorial no encontrada.")
    return editorial


async def actualizar(
    session: AsyncSession, editorial_id: int, data: EditorialUpdate
) -> Editorial:
    editorial = await obtener(session, editorial_id)
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(editorial, campo, valor)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=_MSJ_CONFLICTO)
    await session.refresh(editorial)
    return editorial


async def libros_de_editorial(
    session: AsyncSession, editorial_id: int
) -> list[Libro]:
    await obtener(session, editorial_id)
    res = await session.execute(
        select(Libro)
        .where(Libro.editorial_id == editorial_id)
        .options(joinedload(Libro.editorial), joinedload(Libro.genero))
    )
    return list(res.scalars().all())
