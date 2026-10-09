"""Rutas del módulo editoriales."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.editoriales import service
from app.modules.editoriales.schemas import (
    EditorialCreate,
    EditorialRead,
    EditorialUpdate,
    LibroResumen,
)

router = APIRouter(prefix="/editoriales", tags=["editoriales"])


@router.post("/", response_model=EditorialRead, status_code=201)
async def crear_editorial(
    data: EditorialCreate, session: AsyncSession = Depends(get_session)
) -> service.Editorial:
    return await service.crear(session, data)


@router.get("/", response_model=list[EditorialRead])
async def listar_editoriales(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list:
    return await service.listar(session, limit, offset)


@router.get("/{editorial_id}", response_model=EditorialRead)
async def obtener_editorial(
    editorial_id: int, session: AsyncSession = Depends(get_session)
) -> service.Editorial:
    return await service.obtener(session, editorial_id)


@router.patch("/{editorial_id}", response_model=EditorialRead)
async def actualizar_editorial(
    editorial_id: int,
    data: EditorialUpdate,
    session: AsyncSession = Depends(get_session),
) -> service.Editorial:
    return await service.actualizar(session, editorial_id, data)


@router.get("/{editorial_id}/libros", response_model=list[LibroResumen])
async def libros_de_editorial(
    editorial_id: int, session: AsyncSession = Depends(get_session)
) -> list:
    return await service.libros_de_editorial(session, editorial_id)
