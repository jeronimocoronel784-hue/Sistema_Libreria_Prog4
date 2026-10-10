"""Rutas del módulo generos."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.generos import service
from app.modules.generos.schemas import (
    GeneroCreate,
    GeneroRead,
    GeneroUpdate,
    LibroResumen,
)

router = APIRouter(prefix="/generos", tags=["generos"])


@router.post("/", response_model=GeneroRead, status_code=201)
async def crear_genero(
    data: GeneroCreate, session: AsyncSession = Depends(get_session)
) -> service.Genero:
    return await service.crear(session, data)


@router.get("/", response_model=list[GeneroRead])
async def listar_generos(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list:
    return await service.listar(session, limit, offset)


@router.get("/{genero_id}", response_model=GeneroRead)
async def obtener_genero(
    genero_id: int, session: AsyncSession = Depends(get_session)
) -> service.Genero:
    return await service.obtener(session, genero_id)


@router.patch("/{genero_id}", response_model=GeneroRead)
async def actualizar_genero(
    genero_id: int,
    data: GeneroUpdate,
    session: AsyncSession = Depends(get_session),
) -> service.Genero:
    return await service.actualizar(session, genero_id, data)


@router.get("/{genero_id}/libros", response_model=list[LibroResumen])
async def libros_del_genero(
    genero_id: int,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list:
    return await service.libros_del_genero(session, genero_id, limit, offset)
