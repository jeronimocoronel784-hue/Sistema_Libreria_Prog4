"""Rutas del módulo ventas. Las ventas son inmutables: no hay PATCH."""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.ventas import service
from app.modules.ventas.schemas import VentaCreate, VentaEnLista, VentaRead

logger = logging.getLogger("libreria.ventas")

router = APIRouter(prefix="/ventas", tags=["ventas"])


async def _avisar_comprobante(venta_id: int, email: str | None) -> None:
    """Aviso simulado al cliente: corre en segundo plano tras la respuesta."""
    await asyncio.sleep(0.5)
    logger.info(
        "Comprobante de la venta %s enviado a %s", venta_id, email or "cliente"
    )


@router.post("/", response_model=VentaRead, status_code=201)
async def crear_venta(
    data: VentaCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    venta = await service.crear(session, data)
    cliente = venta.get("cliente") or {}
    background_tasks.add_task(
        _avisar_comprobante, venta["id"], cliente.get("email")
    )
    return venta


@router.get("/", response_model=list[VentaEnLista])
async def listar_ventas(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list:
    ventas = await service.listar(session, limit, offset)
    return [
        {"id": v.id, "cliente_id": v.cliente_id, "fecha": v.fecha, "total": v.total}
        for v in ventas
    ]


@router.get("/{venta_id}", response_model=VentaRead)
async def obtener_venta(
    venta_id: int, session: AsyncSession = Depends(get_session)
) -> dict:
    return await service.obtener_detalle(session, venta_id)
