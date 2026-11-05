"""Modelos de tabla del módulo clientes: Cliente y PerfilCliente (uno a uno).

``cliente`` cambia respecto del TP de los capítulos 1 a 4: se le agrega
``usuario_id``, nulo y UNIQUE. Un cliente puede tener, o no, acceso por la web:
si tiene, ese acceso es de un solo usuario, y dos clientes no pueden apuntar
al mismo usuario.

``Cliente.usuario`` devuelve **un objeto** y no una lista (es uno a uno).
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, ForeignKey, Index, Integer, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.usuarios.models import Usuario
    from app.modules.ventas.models import Venta


class Cliente(SQLModel, table=True):
    __tablename__ = "cliente"

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("usuario.id", name="fk_cliente_usuario", ondelete="RESTRICT"),
            nullable=True,
            unique=True,
            index=True,
        ),
    )
    nombre: str
    email: str = Field(unique=True)

    usuario: Optional["Usuario"] = Relationship(
        back_populates="cliente",
        sa_relationship_kwargs={"uselist": False},
    )
    perfil: Optional["PerfilCliente"] = Relationship(
        back_populates="cliente",
        sa_relationship_kwargs={"uselist": False},
    )
    ventas: list["Venta"] = Relationship(back_populates="cliente")


class PerfilCliente(SQLModel, table=True):
    """Perfil del cliente (uno a uno con ``cliente``).

    La unicidad de ``cliente_id`` se declara como **restricción** y no como
    índice único: es como quedó en el esquema del TP de los capítulos 1 a 4, y
    la tabla no cambia respecto de aquel TP. Con la declaración equivalente en
    el modelo, la comparación automática de Alembic no proposede cambios que
    no existen.
    """

    __tablename__ = "perfil_cliente"
    __table_args__ = (
        UniqueConstraint("cliente_id"),
        Index("ix_perfil_cliente_cliente_id", "cliente_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id")
    telefono: str | None = Field(default=None)
    direccion: str | None = Field(default=None)

    cliente: Optional["Cliente"] = Relationship(back_populates="perfil")
