"""Lógica del módulo libros (incluye la asociación LibroAutor)."""

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select

from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.schemas import LibroCreate, LibroUpdate

_MSJ_CONFLICTO = (
    "No se pudo guardar el libro: ISBN duplicado o "
    "editorial, género o autor inexistente."
)


async def crear(session: AsyncSession, data: LibroCreate) -> dict:
    """Alta con ids existentes. Sin `if` previos: la base valida las FK (409)."""
    libro = Libro(
        isbn=data.isbn,
        titulo=data.titulo,
        precio=data.precio,
        stock=data.stock,
        editorial_id=data.editorial_id,
        genero_id=data.genero_id,
    )
    session.add(libro)
    try:
        await session.flush()
        for item in data.autores:
            session.add(
                LibroAutor(
                    libro_id=libro.id,
                    autor_id=item.autor_id,
                    rol=item.rol,
                    orden=item.orden,
                )
            )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=_MSJ_CONFLICTO)
    return await obtener_detalle(session, libro.id)


async def listar(
    session: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    titulo: str | None = None,
    genero_id: int | None = None,
) -> list[Libro]:
    consulta = (
        select(Libro)
        .options(joinedload(Libro.editorial), joinedload(Libro.genero))
        .offset(offset)
        .limit(limit)
    )
    if titulo:
        # Parámetro ligado: SQLAlchemy lo envía como bind parameter, nunca
        # concatena texto del usuario en el SQL.
        consulta = consulta.where(Libro.titulo.ilike(f"%{titulo}%"))
    if genero_id is not None:
        consulta = consulta.where(Libro.genero_id == genero_id)
    res = await session.execute(consulta)
    return list(res.scalars().all())


async def obtener_detalle(session: AsyncSession, libro_id: int) -> dict:
    """Detalle con editorial, género y autores en un número fijo de consultas."""
    res = await session.execute(
        select(Libro)
        .where(Libro.id == libro_id)
        .options(
            joinedload(Libro.editorial),
            joinedload(Libro.genero),
            selectinload(Libro.autorias).joinedload(LibroAutor.autor),
        )
    )
    libro = res.scalars().first()
    if libro is None:
        raise HTTPException(status_code=404, detail="Libro no encontrado.")
    return {
        "id": libro.id,
        "isbn": libro.isbn,
        "titulo": libro.titulo,
        "precio": libro.precio,
        "stock": libro.stock,
        "editorial_id": libro.editorial_id,
        "genero_id": libro.genero_id,
        "editorial": (
            {
                "id": libro.editorial.id,
                "nombre": libro.editorial.nombre,
                "pais": libro.editorial.pais,
            }
            if libro.editorial is not None
            else None
        ),
        "genero": (
            {"id": libro.genero.id, "nombre": libro.genero.nombre}
            if libro.genero is not None
            else None
        ),
        "autores": [
            {
                "autor_id": a.autor_id,
                "rol": a.rol,
                "orden": a.orden,
                "autor": (
                    {
                        "id": a.autor.id,
                        "nombre": a.autor.nombre,
                        "nacionalidad": a.autor.nacionalidad,
                    }
                    if a.autor is not None
                    else None
                ),
            }
            for a in sorted(libro.autorias, key=lambda x: x.orden)
        ],
    }


async def actualizar(
    session: AsyncSession, libro_id: int, data: LibroUpdate
) -> dict:
    res = await session.execute(select(Libro).where(Libro.id == libro_id))
    libro = res.scalars().first()
    if libro is None:
        raise HTTPException(status_code=404, detail="Libro no encontrado.")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(libro, campo, valor)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=_MSJ_CONFLICTO)
    return await obtener_detalle(session, libro_id)
