"""Contratos del módulo clientes."""

from decimal import Decimal

from sqlmodel import Field, SQLModel


class ClienteCreate(SQLModel):
    nombre: str = Field(min_length=1)
    email: str = Field(min_length=3)


class ClienteUpdate(SQLModel):
    nombre: str | None = Field(default=None, min_length=1)
    email: str | None = Field(default=None, min_length=3)


class ClienteRead(SQLModel):
    id: int
    nombre: str
    email: str


class PerfilCreate(SQLModel):
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


class VentaResumen(SQLModel):
    id: int
    fecha: str | None = None
    total: Decimal
