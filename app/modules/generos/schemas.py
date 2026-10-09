"""Contratos del módulo generos."""

from decimal import Decimal

from sqlmodel import Field, SQLModel


class GeneroCreate(SQLModel):
    nombre: str = Field(min_length=1)


class GeneroRead(SQLModel):
    id: int
    nombre: str


class LibroResumen(SQLModel):
    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
