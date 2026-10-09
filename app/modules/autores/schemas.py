"""Contratos del módulo autores."""

from sqlmodel import Field, SQLModel


class AutorCreate(SQLModel):
    nombre: str = Field(min_length=1)
    nacionalidad: str | None = None


class AutorUpdate(SQLModel):
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
