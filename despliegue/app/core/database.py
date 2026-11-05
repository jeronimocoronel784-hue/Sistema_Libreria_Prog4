"""Motor asincrónico, fábrica de sesiones y dependencia por petición."""

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import SQL_ECHO, get_database_url

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine_and_session(database_url: str | None = None) -> AsyncEngine:
    """Crea el motor y la fábrica de sesiones. Se llama en el lifespan."""
    global _engine, _session_factory
    url = database_url or get_database_url()
    _engine = create_async_engine(url, echo=SQL_ECHO, future=True)
    _session_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )
    return _engine


async def close_engine() -> None:
    """Cierra el motor. Se llama al apagar la aplicación."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_engine() -> AsyncEngine | None:
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    return _session_factory


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Entrega una sesión única por petición (expire_on_commit=False).

    La fábrica vive en ``request.app.state`` (cargada en el lifespan).
    """
    factory = getattr(request.app.state, "session_factory", None) or _session_factory
    if factory is None:
        raise RuntimeError("La fábrica de sesiones no está inicializada (lifespan).")
    async with factory() as session:
        yield session
