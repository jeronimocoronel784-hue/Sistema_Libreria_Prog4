"""Aplicación FastAPI, lifespan y registro de routers."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import close_engine, init_engine_and_session
from app.modules.autores.router import router as autores_router
from app.modules.clientes.router import router as clientes_router
from app.modules.editoriales.router import router as editoriales_router
from app.modules.generos.router import router as generos_router
from app.modules.health.router import router as health_router
from app.modules.libros.router import router as libros_router
from app.modules.ventas.router import router as ventas_router


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
    app = FastAPI(title="Librería de barrio", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(editoriales_router)
    app.include_router(generos_router)
    app.include_router(autores_router)
    app.include_router(libros_router)
    app.include_router(clientes_router)
    app.include_router(ventas_router)
    return app


app = create_app()
