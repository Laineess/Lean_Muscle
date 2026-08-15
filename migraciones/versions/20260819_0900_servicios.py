"""Catálogo de precios sueltos de la coach.

Revision: 0009_servicios
Anterior: 0008_fotos_comida
Fecha: 2026-08-19

Los planes ya tenían su tabla porque son una suscripción: duración, intensidad y una alumna
que pertenece a uno. Lo que faltaba es el otro lado: una consulta suelta, material, una
inscripción. Cargos puntuales con su precio, que es lo que la coach quiere tener en un solo
sitio en vez de teclear el importe cada vez que programa un cobro.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0009_servicios"
down_revision: str | None = "0008_fotos_comida"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "servicio",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(26), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "creado_en", mysql.DATETIME(fsp=3), nullable=False, server_default=sa.text("now(3)")
        ),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("motivo", sa.String(20), nullable=False, server_default="cita"),
        sa.Column("precio", sa.Numeric(10, 2), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ulid"),
        sa.ForeignKeyConstraint(["coach_id"], ["coach.id"]),
        sa.CheckConstraint("precio > 0", name="precio_servicio_positivo"),
        sa.CheckConstraint(
            "motivo in ('inscripcion','mensualidad','cita','material','otro')",
            name="motivo_servicio_valido",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_servicio_coach_id", "servicio", ["coach_id"])
    op.create_index("ix_servicio_coach_motivo", "servicio", ["coach_id", "motivo"])


def downgrade() -> None:
    op.drop_table("servicio")
