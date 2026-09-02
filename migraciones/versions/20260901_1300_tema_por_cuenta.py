"""Tema por cuenta.

Revision: 0004_tema
Anterior: 0003_datos_bancarios
Fecha: 2026-09-01

El tema (claro, oscuro o sistema) era del dispositivo: se guardaba en localStorage y lo
compartían todas las cuentas del mismo navegador. Ahora cada usuario guarda el suyo en
`usuario.tema`, igual que el idioma: si una cuenta se pone en oscuro, las demás en el mismo
navegador siguen viendo la suya.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_tema"
down_revision: str | None = "0003_datos_bancarios"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usuario",
        sa.Column(
            "tema",
            sa.String(length=10),
            nullable=False,
            server_default=sa.text("'sistema'"),
        ),
    )
    op.create_check_constraint(
        "ck_usuario_tema_valido", "usuario", "tema in ('sistema','claro','oscuro')"
    )
    op.alter_column("usuario", "tema", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_usuario_tema_valido", "usuario", type_="check")
    op.drop_column("usuario", "tema")