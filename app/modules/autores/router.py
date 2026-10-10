"""Rutas del módulo autores."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.autores import service
from app.modules.autores.schemas import (
    AutorCreate,
    AutorRead,
    AutorUpdate,
    LibroConRol,
)

router = APIRouter(prefix="/autores", tags=["autores"])


@router.post("/", response_model=AutorRead, status_code=201)
async def crear_autor(
    data: AutorCreate, session: AsyncSession = Depends(get_session)
) -> service.Autor:
    return await service.crear(session, data)


@router.get("/", response_model=list[AutorRead])
async def listar_autores(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list:
    return await service.listar(session, limit, offset)


@router.get("/{autor_id}", response_model=AutorRead)
async def obtener_autor(
    autor_id: int, session: AsyncSession = Depends(get_session)
) -> service.Autor:
    return await service.obtener(session, autor_id)


@router.patch("/{autor_id}", response_model=AutorRead)
async def actualizar_autor(
    autor_id: int,
    data: AutorUpdate,
    session: AsyncSession = Depends(get_session),
) -> service.Autor:
    return await service.actualizar(session, autor_id, data)


@router.get("/{autor_id}/libros", response_model=list[LibroConRol])
async def libros_del_autor(
    autor_id: int,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    autorias = await service.libros_del_autor(session, autor_id, limit, offset)
    return [
        {
            "libro_id": a.libro_id,
            "isbn": a.libro.isbn,
            "titulo": a.libro.titulo,
            "rol": a.rol,
            "orden": a.orden,
        }
        for a in autorias
        if a.libro is not None
    ]
