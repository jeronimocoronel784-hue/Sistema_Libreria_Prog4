"""Esquema inicial sin genero ni libro.genero_id.

Revision ID: 0001_inicial_sin_genero
Revises:
Create Date: manual (equivale a `alembic revision --autogenerate`)

NOTA DE REVISIÓN (leída antes de aplicar):
- Generada con --autogenerate contra los modelos y luego revisada a mano.
- Se excluyen a propósito la tabla `genero` y la columna
  `libro.genero_id`: llegan en la migración 0002.
- Se verificó: UNIQUE (nombre, isbn, email, cliente_id), CHECK con nombre
  explícito, NUMERIC con precisión (10,2)/(12,2), fecha con zona horaria
  (timestamptz) e índices explícitos en cada clave foránea (PostgreSQL no
  los crea solo).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_inicial_sin_genero"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "editorial",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("pais", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_table(
        "autor",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("nacionalidad", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cliente",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "libro",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("isbn", sa.String(), nullable=False),
        sa.Column("titulo", sa.String(), nullable=False),
        sa.Column("precio", sa.Numeric(10, 2), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("editorial_id", sa.Integer(), nullable=False),
        sa.CheckConstraint("precio > 0", name="ck_libro_precio_positivo"),
        sa.CheckConstraint("stock >= 0", name="ck_libro_stock_no_negativo"),
        sa.ForeignKeyConstraint(["editorial_id"], ["editorial.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("isbn"),
    )
    op.create_index("ix_libro_editorial_id", "libro", ["editorial_id"])
    op.create_index("ix_libro_titulo", "libro", ["titulo"])
    op.create_table(
        "libro_autor",
        sa.Column("libro_id", sa.Integer(), nullable=False),
        sa.Column("autor_id", sa.Integer(), nullable=False),
        sa.Column("rol", sa.String(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "rol IN ('autor', 'coautor', 'traductor', 'ilustrador')",
            name="ck_libro_autor_rol_valido",
        ),
        sa.CheckConstraint("orden >= 1", name="ck_libro_autor_orden_positivo"),
        sa.ForeignKeyConstraint(["autor_id"], ["autor.id"]),
        sa.ForeignKeyConstraint(["libro_id"], ["libro.id"]),
        sa.PrimaryKeyConstraint("libro_id", "autor_id"),
    )
    op.create_index("ix_libro_autor_autor_id", "libro_autor", ["autor_id"])
    op.create_index("ix_libro_autor_libro_id", "libro_autor", ["libro_id"])
    op.create_table(
        "perfil_cliente",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("telefono", sa.String(), nullable=True),
        sa.Column("direccion", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cliente_id"),
    )
    op.create_index("ix_perfil_cliente_cliente_id", "perfil_cliente", ["cliente_id"])
    op.create_table(
        "venta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("total >= 0", name="ck_venta_total_no_negativo"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_venta_cliente_id", "venta", ["cliente_id"])
    op.create_table(
        "renglon_venta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("venta_id", sa.Integer(), nullable=False),
        sa.Column("libro_id", sa.Integer(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(10, 2), nullable=False),
        sa.CheckConstraint("cantidad > 0", name="ck_renglon_cantidad_positiva"),
        sa.CheckConstraint(
            "precio_unitario > 0", name="ck_renglon_precio_positivo"
        ),
        sa.ForeignKeyConstraint(["libro_id"], ["libro.id"]),
        sa.ForeignKeyConstraint(["venta_id"], ["venta.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_renglon_venta_libro_id", "renglon_venta", ["libro_id"])
    op.create_index("ix_renglon_venta_venta_id", "renglon_venta", ["venta_id"])


def downgrade() -> None:
    op.drop_index("ix_renglon_venta_venta_id", table_name="renglon_venta")
    op.drop_index("ix_renglon_venta_libro_id", table_name="renglon_venta")
    op.drop_table("renglon_venta")
    op.drop_index("ix_venta_cliente_id", table_name="venta")
    op.drop_table("venta")
    op.drop_index("ix_perfil_cliente_cliente_id", table_name="perfil_cliente")
    op.drop_table("perfil_cliente")
    op.drop_index("ix_libro_autor_libro_id", table_name="libro_autor")
    op.drop_index("ix_libro_autor_autor_id", table_name="libro_autor")
    op.drop_table("libro_autor")
    op.drop_index("ix_libro_titulo", table_name="libro")
    op.drop_index("ix_libro_editorial_id", table_name="libro")
    op.drop_table("libro")
    op.drop_table("cliente")
    op.drop_table("autor")
    op.drop_table("editorial")
