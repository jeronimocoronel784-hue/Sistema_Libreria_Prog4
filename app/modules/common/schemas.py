"""Esquemas compartidos (fuente única: evita duplicarlos por módulo).

``EntradaBase`` es la base de todos los contratos de **entrada**: rechaza los
campos que no declaran (``extra="forbid"``). De ese modo nadie se registra con
un rol, ni edita el stock por PATCH, ni manda un ``password_hash``.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict
from sqlmodel import SQLModel


class EntradaBase(SQLModel):
    """Base de los contratos de entrada: rechaza lo que no declaran."""

    model_config = ConfigDict(extra="forbid")


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
