"""Horario de atención de la coach y reglas de reserva.

Revision: 0012_horario
Anterior: 0011_arco
Fecha: 2026-08-22

De aquí salen los huecos que la alumna ve al reservar su consulta.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0012_horario"
down_revision: str | None = "0011_arco"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AJUSTES = [
    ("duracion_consulta_min", 60),
    ("margen_consulta_min", 15),
    ("antelacion_horas", 24),
    ("horizonte_semanas", 8),
]


def upgrade() -> None:
    for nombre, valor in AJUSTES:
        op.add_column(
            "coach",
            sa.Column(nombre, sa.Integer(), nullable=False, server_default=str(valor)),
        )

    op.create_table(
        "horario_atencion",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(26), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "creado_en", mysql.DATETIME(fsp=3), nullable=False, server_default=sa.text("now(3)")
        ),
        sa.Column("dia_semana", mysql.TINYINT(), nullable=False),
        sa.Column("desde", sa.Time(), nullable=False),
        sa.Column("hasta", sa.Time(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ulid"),
        sa.ForeignKeyConstraint(["coach_id"], ["coach.id"]),
        sa.CheckConstraint("dia_semana between 0 and 6", name="dia_semana_valido"),
        sa.CheckConstraint("hasta > desde", name="tramo_valido"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_horario_atencion_coach_id", "horario_atencion", ["coach_id"])
    op.create_index("ix_horario_coach_dia", "horario_atencion", ["coach_id", "dia_semana"])


def downgrade() -> None:
    op.drop_table("horario_atencion")
    for nombre, _ in AJUSTES:
        op.drop_column("coach", nombre)
