"""Datos bancarios de la coach.

Revision: 0003_datos_bancarios
Anterior: 0002_idioma
Fecha: 2026-09-01

La coach declara su cuenta, CLABE y lo que haga falta para que la alumna le pague. Es un
solo campo de texto libre: cada banco se declara distinto, así que no hay campos
estructurados.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_datos_bancarios"
down_revision: str | None = "0002_idioma"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("coach", sa.Column("datos_bancarios", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("coach", "datos_bancarios")