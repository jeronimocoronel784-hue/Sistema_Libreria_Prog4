"""Rutas del módulo libros."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.libros import service
from app.modules.libros.schemas import (
    LibroCreate,
    LibroDetalle,
    LibroEnLista,
    LibroUpdate,
)

router = APIRouter(prefix="/libros", tags=["libros"])


@router.post("/", response_model=LibroDetalle, status_code=201)
async def crear_libro(
    data: LibroCreate, session: AsyncSession = Depends(get_session)
) -> dict:
    return await service.crear(session, data)


@router.get("/", response_model=list[LibroEnLista])
async def listar_libros(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    titulo: str | None = Query(default=None),
    genero_id: int | None = Query(default=None),
) -> list:
    return await service.listar(session, limit, offset, titulo, genero_id)


@router.get("/{libro_id}", response_model=LibroDetalle)
async def obtener_libro(
    libro_id: int, session: AsyncSession = Depends(get_session)
) -> dict:
    return await service.obtener_detalle(session, libro_id)


@router.patch("/{libro_id}", response_model=LibroDetalle)
async def actualizar_libro(
    libro_id: int,
    data: LibroUpdate,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await service.actualizar(session, libro_id, data)
