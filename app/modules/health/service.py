"""Lógica del módulo health."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_ready(session: AsyncSession) -> None:
    """Ejecuta SELECT 1 en crudo. Levanta si la base no responde."""
    await session.execute(text("SELECT 1"))
