"""Contratos del módulo autores.

Los contratos de entrada rechazan los campos que no declaran
(``extra="forbid"``).
"""

from sqlmodel import Field, SQLModel

from app.modules.common.schemas import EntradaBase


class AutorCreate(EntradaBase):
    nombre: str = Field(min_length=1)
    nacionalidad: str | None = None


class AutorUpdate(EntradaBase):
    nombre: str | None = Field(default=None, min_length=1)
    nacionalidad: str | None = None


class AutorRead(SQLModel):
    id: int
    nombre: str
    nacionalidad: str | None = None


class LibroConRol(SQLModel):
    libro_id: int
    isbn: str
    titulo: str
    rol: str
    orden: int
