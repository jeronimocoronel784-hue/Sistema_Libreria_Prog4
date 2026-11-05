"""Motor asincrónico, fábrica de sesiones y dependencia por petición.

Reglas duras que este módulo implementa:

- El motor y la fábrica de sesiones se crean en el **lifespan**, no al importar
  un módulo: un recurso construido al importar se crea antes de que exista el
  bucle de eventos, y el síntoma (anda al levantar el servidor y falla en las
  pruebas, o al revés) no señala la causa.
- ``get_session`` toma la fábrica de ``app.state``, entrega una sesión por
  petición con ``expire_on_commit=False`` y la cierra al terminar.
- El motor se cierra con ``dispose()`` al apagar.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings


def init_engine_and_session() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Crea el motor y la fábrica de sesiones. Se llama en el lifespan.

    El tamaño del pool y el desbordamiento salen de la configuración.
    """
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.SQL_ECHO,
        pool_size=settings.POOL_SIZE,
        max_overflow=settings.MAX_OVERFLOW,
        pool_pre_ping=True,
        connect_args=settings.connect_args(),
        future=True,
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    return engine, session_factory


async def close_engine(engine: AsyncEngine) -> None:
    """Cierra el motor. Se llama al apagar la aplicación."""
    await engine.dispose()


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Entrega una sesión única por petición (``expire_on_commit=False``).

    La fábrica vive en ``request.app.state`` (cargada en el lifespan).

    FastAPI **cachea** la dependencia dentro de una misma petición: por eso
    el router, la dependencia del Unit of Work y las de usuario actual y rol
    reciben la **misma** sesión y la petición autenticada toma una sola
    conexión del pool.
    """
    factory: async_sessionmaker[AsyncSession] | None = getattr(
        request.app.state, "session_factory", None
    )
    if factory is None:
        raise RuntimeError("La fábrica de sesiones no está inicializada (lifespan).")
    async with factory() as session:
        yield session
