"""Registro abierto: liga por coach y solicitudes.

Revision: 0013_registro
Anterior: 0012_horario
Fecha: 2026-08-23

La solicitud no crea una alumna aparte: crea una fila de `alumna` con estado `solicitud`,
que es lo que la deja fuera de la cartera y del limite. Esta tabla guarda solo lo que vive
mientras dura el registro.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0013_registro"
down_revision: str | None = "0012_horario"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "coach",
        sa.Column("registro_abierto", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )

    op.create_table(
        "solicitud_registro",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(26), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "creado_en", mysql.DATETIME(fsp=3), nullable=False, server_default=sa.text("now(3)")
        ),
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="sin_verificar"),
        sa.Column("codigo_hash", sa.String(64), nullable=False),
        sa.Column("codigo_vence_en", mysql.DATETIME(fsp=3), nullable=False),
        sa.Column("intentos", mysql.TINYINT(), nullable=False, server_default="0"),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("recordatorio_enviado_en", mysql.DATETIME(fsp=3), nullable=True),
        sa.Column("decidida_en", mysql.DATETIME(fsp=3), nullable=True),
        sa.Column("motivo_descarte", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ulid"),
        # Una alumna no puede tener dos registros abiertos a la vez.
        sa.UniqueConstraint("alumna_id", name="uq_solicitud_alumna"),
        sa.ForeignKeyConstraint(["coach_id"], ["coach.id"]),
        sa.ForeignKeyConstraint(["alumna_id"], ["alumna.id"]),
        sa.CheckConstraint(
            "estado in ('sin_verificar','en_curso','esperando','aceptada','descartada')",
            name="estado_solicitud_valido",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_solicitud_registro_coach_id", "solicitud_registro", ["coach_id"])
    op.create_index("ix_solicitud_coach_estado", "solicitud_registro", ["coach_id", "estado"])


def downgrade() -> None:
    op.drop_table("solicitud_registro")
    op.drop_column("coach", "registro_abierto")
