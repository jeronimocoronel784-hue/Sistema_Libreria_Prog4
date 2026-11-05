"""Modelos de tabla del módulo libros: Libro, LibroAutor y MovimientoStock.

Reglas que viven en la base y no en el código:

- ``libro.precio > 0`` y ``libro.stock >= 0`` (CHECK).
- El ISBN **deja de ser un UNIQUE común**: el libro tiene borrado lógico
  (``borrado_en``) y la fila dada de baja sigue en la tabla porque las ventas
  viejas la apuntan. Con un UNIQUE común la librería no podría volver a cargar
  un libro con un ISBN que dio de baja, y la base respondería "ya existe" de un
  libro que la aplicación no muestra en ningún listado. Por eso la unicidad es
  sólo entre los vigentes: índice único parcial con ``WHERE borrado_en IS NULL``.
- ``movimiento_stock`` es de **sólo agregado** (RN-12): el disparador que
  rechaza UPDATE y DELETE lo instala la cuarta migración, a mano.

``libro.stock`` es el resultado de sumar los movimientos de ese libro: el stock
sólo cambia a través de movimientos (RN-11) y nunca se edita por PATCH.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.autores.models import Autor
    from app.modules.editoriales.models import Editorial
    from app.modules.generos.models import Genero
    from app.modules.usuarios.models import Usuario
    from app.modules.ventas.models import RenglonVenta, Venta


def _ahora() -> datetime:
    """Marca de tiempo con zona horaria (todas las fechas del esquema son timestamptz)."""
    return datetime.now(timezone.utc)


class Libro(SQLModel, table=True):
    __tablename__ = "libro"
    __table_args__ = (
        CheckConstraint("precio > 0", name="ck_libro_precio_positivo"),
        CheckConstraint("stock >= 0", name="ck_libro_stock_no_negativo"),
        Index(
            "uq_libro_isbn_vigente",
            "isbn",
            unique=True,
            postgresql_where=text("borrado_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    isbn: str = Field(sa_column=Column(String(40), nullable=False))
    titulo: str = Field(index=True)
    precio: Decimal = Field(sa_type=Numeric(10, 2))
    stock: int = Field(default=0)
    editorial_id: int = Field(foreign_key="editorial.id", index=True)
    genero_id: int | None = Field(default=None, foreign_key="genero.id", index=True)
    # Borrado lógico: la fila no se borra nunca (las ventas viejas la muestran).
    borrado_en: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    editorial: Optional["Editorial"] = Relationship(back_populates="libros")
    genero: Optional["Genero"] = Relationship(back_populates="libros")
    autorias: list["LibroAutor"] = Relationship(back_populates="libro")
    renglones: list["RenglonVenta"] = Relationship(back_populates="libro")
    movimientos: list["MovimientoStock"] = Relationship(back_populates="libro")


class LibroAutor(SQLModel, table=True):
    """Objeto de asociación: el rol y el orden son datos de la relación."""

    __tablename__ = "libro_autor"
    __table_args__ = (
        CheckConstraint(
            "rol IN ('autor', 'coautor', 'traductor', 'ilustrador')",
            name="ck_libro_autor_rol_valido",
        ),
        CheckConstraint("orden >= 1", name="ck_libro_autor_orden_positivo"),
    )

    libro_id: int = Field(foreign_key="libro.id", primary_key=True, index=True)
    autor_id: int = Field(foreign_key="autor.id", primary_key=True, index=True)
    rol: str
    orden: int = Field(default=1)

    libro: Optional["Libro"] = Relationship(back_populates="autorias")
    autor: Optional["Autor"] = Relationship(back_populates="autorias")


class MovimientoStock(SQLModel, table=True):
    """Punto único de escritura del stock (RN-11). Sólo agregado (RN-12).

    ``cantidad`` es **con signo**: positiva cuando entra stock (alta con stock
    inicial, reposición) y negativa cuando sale (venta). El CHECK es
    ``cantidad <> 0``: un movimiento siempre mueve algo.

    La suma de los movimientos de un libro es su ``stock``. Esa igualdad es la
    que se verifica después de cada venta, y se rompe si alguna parte del
    código escribe el stock sin dejar un movimiento.
    """

    __tablename__ = "movimiento_stock"
    __table_args__ = (
        CheckConstraint("cantidad <> 0", name="ck_movimiento_stock_cantidad_no_cero"),
        Index("ix_movimiento_stock_libro_id", "libro_id"),
        Index("ix_movimiento_stock_venta_id", "venta_id"),
        Index("ix_movimiento_stock_usuario_id", "usuario_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    libro_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("libro.id", name="fk_movimiento_stock_libro", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    # Nulo: los movimientos que no vienen de una venta (alta, reposición).
    venta_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("venta.id", name="fk_movimiento_stock_venta", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    usuario_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("usuario.id", name="fk_movimiento_stock_usuario", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    cantidad: int = Field(sa_column=Column(Integer, nullable=False))
    motivo: str = Field(sa_column=Column(String(120), nullable=False))
    cuando: datetime = Field(
        default_factory=_ahora,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=func.now()
        ),
    )

    libro: "Libro" = Relationship(
        back_populates="movimientos",
        sa_relationship_kwargs={"foreign_keys": "MovimientoStock.libro_id"},
    )
    venta: Optional["Venta"] = Relationship(
        back_populates="movimientos",
        sa_relationship_kwargs={"foreign_keys": "MovimientoStock.venta_id"},
    )
    usuario: "Usuario" = Relationship(
        back_populates="movimientos_stock",
        sa_relationship_kwargs={"foreign_keys": "MovimientoStock.usuario_id"},
    )
