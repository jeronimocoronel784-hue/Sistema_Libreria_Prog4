"""Esquemas compartidos (fuente única: evita duplicarlos por módulo)."""

from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel


class LibroResumen(SQLModel):
    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int


class VentaResumen(SQLModel):
    id: int
    fecha: datetime | None = None
    total: Decimal
