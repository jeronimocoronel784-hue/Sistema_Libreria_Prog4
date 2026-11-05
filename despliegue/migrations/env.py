"""Entorno de Alembic con plantilla asincrónica.

La URL se lee de DATABASE_URL (.env); alembic.ini no guarda secretos.
target_metadata sale de los modelos SQLModel (se importan todos para
que autogenerate los vea).
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context

# Que `alembic upgrade head` funcione desde la raíz sin PYTHONPATH extra.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

# Importar TODOS los modelos para que SQLModel.metadata esté completo.
from app.modules.autores.models import Autor  # noqa: F401
from app.modules.clientes.models import Cliente, PerfilCliente  # noqa: F401
from app.modules.editoriales.models import Editorial  # noqa: F401
from app.modules.generos.models import Genero  # noqa: F401
from app.modules.libros.models import Libro, LibroAutor  # noqa: F401
from app.modules.ventas.models import RenglonVenta, Venta  # noqa: F401
from app.core.config import get_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# La URL real viene del entorno, nunca de alembic.ini.
config.set_main_option("sqlalchemy.url", get_database_url())

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
