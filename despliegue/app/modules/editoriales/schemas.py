"""Contratos del módulo editoriales."""

from sqlmodel import Field, SQLModel

from app.modules.common.schemas import LibroResumen

__all__ = [
    "EditorialCreate",
    "EditorialUpdate",
    "EditorialRead",
    "LibroResumen",  # re-exportado desde common (compatibilidad)
]


class EditorialCreate(SQLModel):
    nombre: str = Field(min_length=1)
    pais: str | None = None


class EditorialUpdate(SQLModel):
    nombre: str | None = Field(default=None, min_length=1)
    pais: str | None = None


class EditorialRead(SQLModel):
    id: int
    nombre: str
    pais: str | None = None
