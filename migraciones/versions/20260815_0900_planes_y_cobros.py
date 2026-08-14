"""Planes comerciales y cobros programados.

Revision: 0004_cobros
Anterior: 0003_marca
Fecha: 2026-08-15

Cambia la dinámica de cobro. Antes había un precio por ciclo en el perfil de la coach y un
`objetivo` fijo por alumna; ahora la coach crea planes con su propio costo e intensidad, y
cada alumna pertenece a uno.

Los cobros dejan de derivarse del ciclo: la coach marca las fechas en un calendario y cada
una dice qué se cobra y cuánto. **Un cobro vencido y sin pagar pausa el plan de la alumna**,
que pasa a ser la única palanca de cobro del sistema.

`alumna.objetivo` desaparece: quien quiera distinguir pérdida de ganancia crea dos planes
con esos nombres.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0004_cobros"
down_revision: str | None = "0003_marca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def _columnas(tabla: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(tabla)}


def upgrade() -> None:
    if "intensidad" not in _columnas("tarifa"):
        op.add_column(
            "tarifa",
            sa.Column("intensidad", sa.String(10), server_default="media", nullable=False),
        )
        op.create_check_constraint(
            "ck_tarifa_intensidad_valida", "tarifa", "intensidad in ('baja','media','alta')"
        )

    columnas_alumna = _columnas("alumna")
    if "tarifa_id" not in columnas_alumna:
        op.add_column("alumna", sa.Column("tarifa_id", sa.BigInteger(), nullable=True))
        op.create_foreign_key("fk_alumna_tarifa_id", "alumna", "tarifa", ["tarifa_id"], ["id"])
    if "objetivo" in columnas_alumna:
        op.drop_column("alumna", "objetivo")

    if not sa.inspect(op.get_bind()).has_table("cobro_programado"):
        op.create_table(
            "cobro_programado",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("ulid", mysql.CHAR(26), nullable=False),
            sa.Column(
                "creado_en",
                mysql.DATETIME(fsp=3),
                server_default=sa.func.now(3),
                nullable=False,
            ),
            sa.Column("coach_id", sa.BigInteger(), nullable=False),
            sa.Column("alumna_id", sa.BigInteger(), nullable=False),
            sa.Column("fecha", sa.Date(), nullable=False),
            sa.Column("motivo", sa.String(20), server_default="mensualidad", nullable=False),
            sa.Column("concepto", sa.String(180), nullable=True),
            sa.Column("monto", sa.Numeric(10, 2), nullable=False),
            sa.Column("estado", sa.String(20), server_default="pendiente", nullable=False),
            sa.Column("movimiento_id", sa.BigInteger(), nullable=True),
            sa.Column("pagado_en", sa.Date(), nullable=True),
            sa.Column("nota", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id", name="pk_cobro_programado"),
            sa.UniqueConstraint("ulid", name="uq_cobro_programado_ulid"),
            sa.ForeignKeyConstraint(
                ["alumna_id"], ["alumna.id"], name="fk_cobro_programado_alumna_id"
            ),
            sa.ForeignKeyConstraint(
                ["movimiento_id"],
                ["movimiento_financiero.id"],
                name="fk_cobro_programado_movimiento_id",
            ),
            sa.CheckConstraint(
                "motivo in ('inscripcion','mensualidad','cita','material','otro')",
                name="ck_cobro_programado_motivo_valido",
            ),
            sa.CheckConstraint(
                "estado in ('pendiente','pagado','cancelado')",
                name="ck_cobro_programado_estado_cobro_valido",
            ),
            sa.CheckConstraint("monto > 0", name="ck_cobro_programado_monto_positivo"),
            **ARGS,
        )
        op.create_index("ix_cobro_programado_coach_id", "cobro_programado", ["coach_id"])
        op.create_index("ix_cobro_alumna_fecha", "cobro_programado", ["alumna_id", "fecha"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("cobro_programado"):
        op.drop_table("cobro_programado")
    if "tarifa_id" in _columnas("alumna"):
        op.drop_constraint("fk_alumna_tarifa_id", "alumna", type_="foreignkey")
        op.drop_column("alumna", "tarifa_id")
    if "objetivo" not in _columnas("alumna"):
        op.add_column("alumna", sa.Column("objetivo", sa.String(30), nullable=True))
    if "intensidad" in _columnas("tarifa"):
        op.drop_column("tarifa", "intensidad")
