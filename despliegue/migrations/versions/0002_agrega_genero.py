"""Agrega genero y libro.genero_id.

Revision ID: 0002_agrega_genero
Revises: 0001_inicial_sin_genero
Create Date: manual (equivale a `alembic revision --autogenerate`)

NOTA DE REVISIÓN (leída antes de aplicar):
- Generada con --autogenerate tras incorporar el modelo `Genero` y la
  columna `Libro.genero_id` (agregación opcional: nulleable).
- Se corrigió a mano el orden: primero se crea la tabla `genero`, después
  la columna y por último su FK. Autogenerate no garantiza ese orden si hay
  varias operaciones pendientes.
- Se verificó el UNIQUE de `genero.nombre` y el índice explícito de la FK
  `libro.genero_id` (PostgreSQL no lo crea solo).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_agrega_genero"
down_revision: Union[str, None] = "0001_inicial_sin_genero"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "genero",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )
    op.add_column("libro", sa.Column("genero_id", sa.Integer(), nullable=True))
    op.create_index("ix_libro_genero_id", "libro", ["genero_id"])
    op.create_foreign_key(
        "fk_libro_genero_id", "libro", "genero", ["genero_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_libro_genero_id", "libro", type_="foreignkey")
    op.drop_index("ix_libro_genero_id", table_name="libro")
    op.drop_column("libro", "genero_id")
    op.drop_table("genero")
