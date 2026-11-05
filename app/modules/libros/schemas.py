"""Contratos del módulo libros.

Reglas duras que este módulo implementa:

- Los contratos de entrada rechazan los campos que no declaran
  (``extra="forbid"``): de ese modo **nadie edita el stock por PATCH**
  (RN-11) ni manda un ``stock`` en el alta.
- El alta lleva ``stock_inicial``, no ``stock``: el stock inicial no se escribe
  directo en el libro, se deja como un movimiento (RN-11).
- El PATCH sólo acepta ``titulo`` y ``precio``.
"""

from decimal import Decimal
from datetime import datetime
from typing import Literal

from sqlmodel import Field, SQLModel

from app.modules.common.schemas import EntradaBase

RolAutoria = Literal["autor", "coautor", "traductor", "ilustrador"]


class AutoriaIn(EntradaBase):
    autor_id: int
    rol: RolAutoria = "autor"
    orden: int = Field(default=1, ge=1)


class LibroCreate(EntradaBase):
    isbn: str = Field(min_length=1, max_length=40)
    titulo: str = Field(min_length=1)
    precio: Decimal = Field(gt=0)
    stock_inicial: int = Field(default=0, ge=0)
    editorial_id: int
    genero_id: int | None = None
    autores: list[AutoriaIn] = Field(default_factory=list)


class LibroUpdate(EntradaBase):
    """PATCH parcial. **No** acepta ``stock``: el stock no se edita (RN-11)."""

    titulo: str | None = Field(default=None, min_length=1)
    precio: Decimal | None = Field(default=None, gt=0)


class Reposicion(EntradaBase):
    """Reposición de stock: se convierte en un movimiento (RN-11)."""

    cantidad: int = Field(gt=0)


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


class MovimientoRead(SQLModel):
    """Movimiento de stock. La tabla es de sólo agregado: no se edita."""

    id: int
    libro_id: int
    venta_id: int | None = None
    usuario_id: int
    cantidad: int
    motivo: str
    cuando: datetime
