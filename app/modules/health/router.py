"""Rutas del módulo health.

El módulo health sólo tiene ``router.py``: son dos rutas de una línea cada una
y no hace falta repartirlo en capas.
"""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    """El proceso está vivo. No toca la base."""
    return {"estado": "vivo"}


@router.get("/ready")
async def ready(request: Request) -> dict[str, str]:
    """El proceso está listo: la base responde.

    Ejecuta ``SELECT 1`` y responde 503 si la base no contesta: el proceso
    puede estar vivo y no estar listo, y reiniciarlo no arregla una base caída.
    """
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    try:
        async with factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    return {"estado": "lista"}
