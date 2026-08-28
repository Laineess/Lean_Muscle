"""Idioma por cuenta.

Revision: 0002_idioma
Anterior: 0001_esquema
Fecha: 2026-08-28

El idioma era del dispositivo (localStorage compartido entre cuentas). Ahora cada usuario
guarda el suyo en `usuario.idioma`: si una cuenta se pone en inglés, las demás en el mismo
navegador siguen viendo la suya.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_idioma"
down_revision: str | None = "0001_esquema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usuario",
        sa.Column("idioma", sa.String(length=2), nullable=False, server_default=sa.text("'es'")),
    )
    op.create_check_constraint(
        "ck_usuario_idioma_valido", "usuario", "idioma in ('es','en')"
    )
    op.alter_column("usuario", "idioma", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_usuario_idioma_valido", "usuario", type_="check")
    op.drop_column("usuario", "idioma")