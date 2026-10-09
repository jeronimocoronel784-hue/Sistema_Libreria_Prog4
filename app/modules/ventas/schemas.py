"""Contratos del módulo ventas."""

from decimal import Decimal
from typing import Self

from pydantic import model_validator
from sqlmodel import Field, SQLModel


class RenglonIn(SQLModel):
    libro_id: int
    cantidad: int = Field(gt=0)


class VentaCreate(SQLModel):
    cliente_id: int
    renglones: list[RenglonIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _sin_libros_repetidos(self) -> Self:
        ids = [r.libro_id for r in self.renglones]
        if len(ids) != len(set(ids)):
            raise ValueError("Un mismo libro no puede repetirse en dos renglones.")
        return self


class ClienteResumido(SQLModel):
    id: int
    nombre: str
    email: str


class RenglonRead(SQLModel):
    libro_id: int
    titulo: str | None = None
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


class VentaRead(SQLModel):
    id: int
    fecha: str | None = None
    total: Decimal
    cliente: ClienteResumido | None = None
    renglones: list[RenglonRead] = Field(default_factory=list)


class VentaEnLista(SQLModel):
    id: int
    cliente_id: int
    fecha: str | None = None
    total: Decimal
