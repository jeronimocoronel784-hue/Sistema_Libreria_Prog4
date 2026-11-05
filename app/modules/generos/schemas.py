"""Contratos del módulo géneros.

Los contratos de entrada rechazan los campos que no declaran
(``extra="forbid"``).
"""

from sqlmodel import Field, SQLModel

from app.modules.common.schemas import EntradaBase, LibroResumen

__all__ = [
    "GeneroCreate",
    "GeneroUpdate",
    "GeneroRead",
    "LibroResumen",  # re-exportado desde common (compatibilidad)
]


class GeneroCreate(EntradaBase):
    nombre: str = Field(min_length=1)


class GeneroUpdate(EntradaBase):
    nombre: str | None = Field(default=None, min_length=1)


class GeneroRead(SQLModel):
    id: int
    nombre: str
