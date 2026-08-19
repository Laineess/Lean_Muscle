"""Marca de purga en el comprobante del cobro.

Revision: 0014_purga_comprobantes
Anterior: 0013_registro
Fecha: 2026-08-24

La imagen del comprobante se borra por antiguedad para no llenar el disco del VPS. La fila
se queda: el monto, la fecha y lo que leyo el OCR son la contabilidad. Esta columna es lo
que distingue «nunca subio comprobante» de «lo subio y su imagen ya vencio».
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0014_purga_comprobantes"
down_revision: str | None = "0013_registro"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cobro_programado",
        sa.Column("comprobante_purgado_en", mysql.DATETIME(fsp=3), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cobro_programado", "comprobante_purgado_en")
