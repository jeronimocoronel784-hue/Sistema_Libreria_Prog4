"""sÃ³lo agregado: rechaza UPDATE y DELETE sobre movimiento_stock

LEER ANTES DE APLICAR (Ejercicio 2 del parcial).

Esta revisiÃ³n se escribe **a mano** porque la comparaciÃ³n automÃ¡tica de Alembic
no ve funciones ni disparadores: la tercera migraciÃ³n (autogenerada) trae las
tablas, pero el disparador que protege ``movimiento_stock`` hay que escribirlo.

QuÃ© hace y por quÃ©:

- ``movimiento_stock`` es de **sÃ³lo agregado** (RN-12): nadie puede modificar
  ni borrar sus filas, venga de donde venga (API, seed o psql). INSERT sigue
  permitido: un movimiento que se equivoca se **compensa** con otro, no se
  corrige.
- El disparador va ``BEFORE UPDATE OR DELETE``, asÃ­ que el rechazo ocurre antes
  de que la fila cambie.
- ``ERRCODE = 'integrity_constraint_violation'`` (SQLSTATE 23000) hace que el
  rechazo se comporte como una violaciÃ³n de integridad y no como un error
  inesperado del servidor.
- El mensaje usa ``TG_TABLE_NAME`` y ``TG_OP``: un solo cuerpo para cualquier
  tabla, sin copiar el texto.
- El ``downgrade`` borra el disparador y la funciÃ³n: bajar sÃ³lo esta revisiÃ³n
  deja las tablas existentes y usables.
- ``seed.py`` reinicia con ``TRUNCATE``, que **no** dispara
  ``BEFORE UPDATE OR DELETE``; si se intenta un reset con ``DELETE``, el
  disparador lo rechaza (es lo buscado).

Revision ID: 0004_solo_agregado
Revises: 0003_acceso_y_movimientos
Create Date: 2026-11-05

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_solo_agregado"
down_revision: Union[str, Sequence[str], None] = "0003_acceso_y_movimientos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FUNCION = "solo_agregado_rechazar_modificacion"
TABLAS = ("movimiento_stock",)


def upgrade() -> None:
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {FUNCION}()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION
                'La tabla % es de sÃ³lo agregado: % no estÃ¡ permitido',
                TG_TABLE_NAME, TG_OP
                USING ERRCODE = 'integrity_constraint_violation',
                      HINT = 'AgregÃ¡ una fila nueva en lugar de modificar o borrar la existente.';
        END;
        $$;
        """
    )

    for tabla in TABLAS:
        op.execute(
            f"""
            CREATE TRIGGER trg_{tabla}_solo_agregado
            BEFORE UPDATE OR DELETE ON {tabla}
            FOR EACH ROW
            EXECUTE FUNCTION {FUNCION}();
            """
        )


def downgrade() -> None:
    for tabla in TABLAS:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tabla}_solo_agregado ON {tabla};")

    op.execute(f"DROP FUNCTION IF EXISTS {FUNCION}();")

