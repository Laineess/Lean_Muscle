"""Avisos que la coach manda a sus alumnas: título y cuerpo.

Revision: 0010_anuncios
Anterior: 0009_servicios
Fecha: 2026-08-20

La mensajería que ya existía es una conversación de dos. Esto va en una sola dirección y a
varias a la vez, así que necesita su tabla: sin ella no hay forma de saber a cuántas llegó
cada frase ni cuántas la leyeron.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0010_anuncios"
down_revision: str | None = "0009_servicios"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "anuncio",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(26), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "creado_en", mysql.DATETIME(fsp=3), nullable=False, server_default=sa.text("now(3)")
        ),
        sa.Column("titulo", sa.String(80), nullable=False),
        sa.Column("cuerpo", sa.String(300), nullable=False),
        sa.Column("enviado_por", sa.BigInteger(), nullable=False),
        sa.Column("enviado_en", mysql.DATETIME(fsp=3), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ulid"),
        sa.ForeignKeyConstraint(["coach_id"], ["coach.id"]),
        sa.ForeignKeyConstraint(["enviado_por"], ["usuario.id"]),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_anuncio_coach_id", "anuncio", ["coach_id"])
    op.create_index("ix_anuncio_coach_enviado", "anuncio", ["coach_id", "enviado_en"])

    op.add_column("notificacion", sa.Column("anuncio_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_notificacion_anuncio_id", "notificacion", "anuncio", ["anuncio_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_notificacion_anuncio_id", "notificacion", type_="foreignkey")
    op.drop_column("notificacion", "anuncio_id")
    op.drop_table("anuncio")
