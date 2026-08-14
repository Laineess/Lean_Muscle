"""Fotos de comida, con borrado a las 36 horas.

Revision: 0008_fotos_comida
Anterior: 0007_intentos
Fecha: 2026-08-18

La coach elige al armar el plan de nutrición cada cuánto le toca a la alumna mandar fotos de
sus platos: diario, semanal, quincenal o mensual. `ninguna` es el valor de fábrica.

Las fotos se borran a las 36 horas de subirlas. No es una política revisable: es lo único
que hace razonable pedirle a alguien que fotografíe lo que come. Nada que ver con las fotos
de chequeo, que viven cuatro meses porque son el registro del método.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0008_fotos_comida"
down_revision: str | None = "0007_intentos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "plan",
        sa.Column(
            "frecuencia_fotos", sa.String(12), nullable=False, server_default="ninguna"
        ),
    )

    op.create_table(
        "foto_de_comida",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(26), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "creado_en", mysql.DATETIME(fsp=3), nullable=False, server_default=sa.text("now(3)")
        ),
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=True),
        sa.Column("subida_en", mysql.DATETIME(fsp=3), nullable=False),
        sa.Column("purgada_en", mysql.DATETIME(fsp=3), nullable=True),
        sa.Column("tiempo", sa.String(60), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ulid"),
        sa.ForeignKeyConstraint(["coach_id"], ["coach.id"]),
        sa.ForeignKeyConstraint(["alumna_id"], ["alumna.id"]),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_foto_de_comida_coach_id", "foto_de_comida", ["coach_id"])
    op.create_index("ix_foto_comida_alumna_subida", "foto_de_comida", ["alumna_id", "subida_en"])
    # El trabajo de purga recorre justo por aquí, cada media hora.
    op.create_index("ix_foto_comida_purga", "foto_de_comida", ["purgada_en", "subida_en"])


def downgrade() -> None:
    op.drop_table("foto_de_comida")
    op.drop_column("plan", "frecuencia_fotos")
