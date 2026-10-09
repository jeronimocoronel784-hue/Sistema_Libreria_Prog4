"""Contratos del módulo editoriales."""

from decimal import Decimal

from sqlmodel import Field, SQLModel


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


class LibroResumen(SQLModel):
    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
