"""Modelos de tabla del módulo clientes: Cliente y PerfilCliente (uno a uno)."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.ventas.models import Venta


class Cliente(SQLModel, table=True):
    __tablename__ = "cliente"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str
    email: str = Field(unique=True)

    perfil: "PerfilCliente | None" = Relationship(
        back_populates="cliente",
        sa_relationship_kwargs={"uselist": False},
    )
    ventas: list["Venta"] = Relationship(back_populates="cliente")


class PerfilCliente(SQLModel, table=True):
    __tablename__ = "perfil_cliente"

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", unique=True, index=True)
    telefono: str | None = Field(default=None)
    direccion: str | None = Field(default=None)

    cliente: "Cliente | None" = Relationship(back_populates="perfil")  # type: ignore[valid-type]
