"""Contratos del módulo libros."""

from decimal import Decimal
from typing import Literal

from sqlmodel import Field, SQLModel

RolAutoria = Literal["autor", "coautor", "traductor", "ilustrador"]


class AutoriaIn(SQLModel):
    autor_id: int
    rol: RolAutoria = "autor"
    orden: int = Field(default=1, ge=1)


class LibroCreate(SQLModel):
    isbn: str = Field(min_length=1)
    titulo: str = Field(min_length=1)
    precio: Decimal = Field(gt=0)
    stock: int = Field(default=0, ge=0)
    editorial_id: int
    genero_id: int | None = None
    autores: list[AutoriaIn] = Field(default_factory=list)


class LibroUpdate(SQLModel):
    isbn: str | None = Field(default=None, min_length=1)
    titulo: str | None = Field(default=None, min_length=1)
    precio: Decimal | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    editorial_id: int | None = None
    genero_id: int | None = None


class AutorResumido(SQLModel):
    id: int
    nombre: str
    nacionalidad: str | None = None


class AutoriaRead(SQLModel):
    autor_id: int
    rol: str
    orden: int
    autor: AutorResumido


class EditorialResumida(SQLModel):
    id: int
    nombre: str
    pais: str | None = None


class GeneroResumido(SQLModel):
    id: int
    nombre: str


class LibroEnLista(SQLModel):
    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial_id: int
    genero_id: int | None = None
    editorial: EditorialResumida | None = None
    genero: GeneroResumido | None = None


class LibroDetalle(SQLModel):
    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial_id: int
    genero_id: int | None = None
    editorial: EditorialResumida | None = None
    genero: GeneroResumido | None = None
    autores: list[AutoriaRead] = Field(default_factory=list)
