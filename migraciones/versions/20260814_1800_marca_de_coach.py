"""Nombre comercial de la coach.

Revision: 0003_marca
Anterior: 0002_plataforma
Fecha: 2026-08-14

`coach.nombre` es el de la persona y `coach.marca` el que ven las alumnas. Hasta ahora se
usaba el mismo para las dos cosas, así que la barra de la app decía «Mariana Cervantes»
donde debía decir «LeanMuscle».

Nulo significa «usa el nombre», que es lo que ya pasaba: nadie tiene que rellenarlo para que
todo siga funcionando igual.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_marca"
down_revision: str | None = "0002_plataforma"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columnas = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("coach")}
    if "marca" not in columnas:
        op.add_column("coach", sa.Column("marca", sa.String(120), nullable=True))


def downgrade() -> None:
    columnas = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("coach")}
    if "marca" in columnas:
        op.drop_column("coach", "marca")
