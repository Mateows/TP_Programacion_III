"""solo_agregado

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30 11:26:39.167759

Disparadores de inmutabilidad (RN-15): las tablas de sólo agregado
``historial_estado_orden``, ``movimiento_stock`` e
``historial_precio_repuesto`` rechazan cualquier ``UPDATE`` o ``DELETE``.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLAS_SOLO_AGREGADO: tuple[str, ...] = (
    "historial_estado_orden",
    "movimiento_stock",
    "historial_precio_repuesto",
)


def _nombre_trigger(tabla: str) -> str:
    """Nombre estable del trigger de inmutabilidad de una tabla."""
    return f"trg_{tabla}_solo_agregado"


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION rechazar_modificacion_o_borrado()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION
                'Operación no permitida: tabla de sólo agregado (RN-15)'
                USING ERRCODE = '23505';
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    for tabla in TABLAS_SOLO_AGREGADO:
        op.execute(
            f"""
            CREATE TRIGGER {_nombre_trigger(tabla)}
            BEFORE UPDATE OR DELETE ON {tabla}
            FOR EACH ROW
            EXECUTE FUNCTION rechazar_modificacion_o_borrado();
            """
        )


def downgrade() -> None:
    for tabla in TABLAS_SOLO_AGREGADO:
        op.execute(
            f"DROP TRIGGER IF EXISTS {_nombre_trigger(tabla)} ON {tabla};"
        )

    op.execute("DROP FUNCTION IF EXISTS rechazar_modificacion_o_borrado();")
