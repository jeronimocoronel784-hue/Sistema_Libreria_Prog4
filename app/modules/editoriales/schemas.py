"""Contratos del módulo editoriales.

Los contratos de entrada rechazan los campos que no declaran
(``extra="forbid"``).
"""

from sqlmodel import Field, SQLModel

from app.modules.common.schemas import EntradaBase, LibroResumen

__all__ = [
    "EditorialCreate",
    "EditorialUpdate",
    "EditorialRead",
    "LibroResumen",  # re-exportado desde common (compatibilidad)
]


class EditorialCreate(EntradaBase):
    nombre: str = Field(min_length=1)
    pais: str | None = None


class EditorialUpdate(EntradaBase):
    nombre: str | None = Field(default=None, min_length=1)
    pais: str | None = None


class EditorialRead(SQLModel):
    id: int
    nombre: str
    pais: str | None = None
