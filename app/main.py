"""Aplicación FastAPI, lifespan y registro de routers."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import close_engine, init_engine_and_session
from app.modules.health.router import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    engine = init_engine_and_session()
    app.state.engine = engine
    from app.core import database as db

    app.state.session_factory = db.get_session_factory()
    try:
        yield
    finally:
        await close_engine()


def create_app() -> FastAPI:
    app = FastAPI(title="Librería de barrio")
    app.router.lifespan_context = lifespan
    app.include_router(health_router)
    return app


app = create_app()
