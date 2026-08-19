"""Baja con borrado a los quince dias.

Revision: 0015_baja
Anterior: 0014_purga_comprobantes
Fecha: 2026-08-25

`baja_en` fija el plazo: de ahi salen los quince dias de lectura y el dia del borrado.

`usuario_id` pasa a admitir nulo porque al borrar se elimina la cuenta —y con ella el
correo, que es unico en toda la plataforma y tiene que quedar libre para que pueda volver a
registrarse— mientras la ficha vacia se queda sosteniendo los consentimientos, la bitacora
de accesos y los movimientos de dinero, que la ley obliga a conservar cinco anios.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0015_baja"
down_revision: str | None = "0014_purga_comprobantes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("alumna", sa.Column("baja_en", mysql.DATETIME(fsp=3), nullable=True))
    op.alter_column(
        "alumna", "usuario_id", existing_type=sa.BigInteger(), nullable=True
    )


def downgrade() -> None:
    # Las fichas ya borradas no tienen cuenta a la que volver, asi que se van con el
    # downgrade: dejarlas romperia la llave foranea al restaurar el NOT NULL.
    op.execute("delete from alumna where usuario_id is null")
    op.alter_column(
        "alumna", "usuario_id", existing_type=sa.BigInteger(), nullable=False
    )
    op.drop_column("alumna", "baja_en")
