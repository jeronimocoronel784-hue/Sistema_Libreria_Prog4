"""Rutas del módulo health."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.health import service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    """No toca la base."""
    return {"estado": "vivo"}


@router.get("/ready")
async def ready(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    try:
        await service.check_ready(session)
    except Exception:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    return {"estado": "lista"}
