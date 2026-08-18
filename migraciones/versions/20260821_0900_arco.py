"""La solicitud ARCO guarda lo que se pidió y lo que se contestó.

Revision: 0011_arco
Anterior: 0010_anuncios
Fecha: 2026-08-21

La tabla existía sin las dos columnas que hacen falta para que sirva de constancia: el
texto de la alumna y el de la respuesta.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_arco"
down_revision: str | None = "0010_anuncios"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("solicitud_arco", sa.Column("detalle", sa.Text(), nullable=True))
    op.add_column("solicitud_arco", sa.Column("respuesta", sa.Text(), nullable=True))
    op.create_index(
        "ix_solicitud_arco_coach_estado", "solicitud_arco", ["coach_id", "estado", "recibida_en"]
    )


def downgrade() -> None:
    op.drop_index("ix_solicitud_arco_coach_estado", table_name="solicitud_arco")
    op.drop_column("solicitud_arco", "respuesta")
    op.drop_column("solicitud_arco", "detalle")
