"""Contratos del módulo generos."""

from sqlmodel import Field, SQLModel

from app.modules.common.schemas import LibroResumen

__all__ = [
    "GeneroCreate",
    "GeneroUpdate",
    "GeneroRead",
    "LibroResumen",  # re-exportado desde common (compatibilidad)
]


class GeneroCreate(SQLModel):
    nombre: str = Field(min_length=1)


class GeneroUpdate(SQLModel):
    nombre: str | None = Field(default=None, min_length=1)


class GeneroRead(SQLModel):
    id: int
    nombre: str
