"""El comprobante cuelga del cobro programado.

Revision: 0005_comprobante
Anterior: 0004_cobros
Fecha: 2026-08-15

El flujo estaba cortado por la mitad: la alumna subía su comprobante contra `pago` —atado al
ciclo— mientras que lo que determina su adeudo, y lo que le pausa el plan, son los cobros que
la coach marca en el calendario. La coach no tenía forma de ver ese comprobante.

Ahora el comprobante cuelga del cobro. La alumna elige de sus pendientes cuál está pagando,
así que la coach lo recibe ya emparejado y solo confirma contra su estado de cuenta.

Estado nuevo: `en_revision`, entre que la alumna sube y la coach decide.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0005_comprobante"
down_revision: str | None = "0004_cobros"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNAS = (
    ("comprobante_key", sa.String(255)),
    ("subido_en", mysql.DATETIME(fsp=3)),
    ("ocr", mysql.JSON()),
    ("confianza", sa.Numeric(4, 3)),
    ("motivo_rechazo", sa.Text()),
    ("revisado_en", mysql.DATETIME(fsp=3)),
)


def _columnas() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("cobro_programado")}


def upgrade() -> None:
    existentes = _columnas()
    for nombre, tipo in COLUMNAS:
        if nombre not in existentes:
            op.add_column("cobro_programado", sa.Column(nombre, tipo, nullable=True))

    # El CHECK admite ahora `en_revision`. Se recrea porque MySQL no lo modifica en sitio.
    op.drop_constraint(
        "estado_cobro_valido", "cobro_programado", type_="check"
    )
    op.create_check_constraint(
        "estado_cobro_valido",
        "cobro_programado",
        "estado in ('pendiente','en_revision','pagado','cancelado')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "estado_cobro_valido", "cobro_programado", type_="check"
    )
    op.create_check_constraint(
        "estado_cobro_valido",
        "cobro_programado",
        "estado in ('pendiente','pagado','cancelado')",
    )
    existentes = _columnas()
    for nombre, _ in COLUMNAS:
        if nombre in existentes:
            op.drop_column("cobro_programado", nombre)
