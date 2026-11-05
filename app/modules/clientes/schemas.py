"""Contratos del módulo clientes.

Los contratos de entrada rechazan los campos que no declaran
(``extra="forbid"``).
"""

from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from app.modules.common.schemas import EntradaBase, VentaResumen

__all__ = [
    "ClienteCreate",
    "ClienteUpdate",
    "ClienteRead",
    "PerfilCreate",
    "PerfilRead",
    "ClienteConPerfil",
    "VentaResumen",  # re-exportado desde common (compatibilidad)
]


class ClienteCreate(EntradaBase):
    nombre: str = Field(min_length=1)
    email: EmailStr = Field(min_length=3)


class ClienteUpdate(EntradaBase):
    nombre: str | None = Field(default=None, min_length=1)
    email: EmailStr | None = Field(default=None, min_length=3)


class ClienteRead(SQLModel):
    id: int
    nombre: str
    email: str


class PerfilCreate(EntradaBase):
    telefono: str | None = None
    direccion: str | None = None


class PerfilRead(SQLModel):
    id: int
    cliente_id: int
    telefono: str | None = None
    direccion: str | None = None


class ClienteConPerfil(SQLModel):
    id: int
    nombre: str
    email: str
    perfil: PerfilRead | None = None
