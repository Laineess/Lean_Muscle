"""Presentación de la coach y cuestionario inicial con preguntas suyas.

Revision: 0006_presentacion
Anterior: 0005_comprobante
Fecha: 2026-08-16

Se le pedían lesiones, medicación y peso a alguien que todavía no sabía con quién estaba
hablando. La presentación va antes del cuestionario para que ese formulario deje de ser un
trámite con un desconocido.

La ficha va como JSON porque cada coach nombra sus propios campos: fijar «certificaciones» y
«años de experiencia» en columnas sería decidir por ella.

El cuestionario tiene dos mitades. El núcleo clínico sigue en `historial_clinico`, con sus
columnas, porque el plan y los avisos lo consultan por nombre y la ley lo exige. Encima, las
preguntas que cada coach agrega, que sí son libres.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0006_presentacion"
down_revision: str | None = "0005_comprobante"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "presentacion_coach",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(26), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "creado_en", mysql.DATETIME(fsp=3), nullable=False, server_default=sa.text("now(3)")
        ),
        sa.Column("foto_key", sa.String(255), nullable=True),
        sa.Column("titulo", sa.String(160), nullable=False, server_default=""),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("ficha", mysql.JSON(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ulid"),
        sa.UniqueConstraint("coach_id", name="uq_presentacion_coach"),
        sa.ForeignKeyConstraint(["coach_id"], ["coach.id"]),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_presentacion_coach_coach_id", "presentacion_coach", ["coach_id"])

    op.create_table(
        "pregunta_cuestionario",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(26), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "creado_en", mysql.DATETIME(fsp=3), nullable=False, server_default=sa.text("now(3)")
        ),
        sa.Column("texto", sa.String(300), nullable=False),
        sa.Column("ayuda", sa.String(300), nullable=True),
        sa.Column("tipo", sa.String(20), nullable=False, server_default="texto"),
        sa.Column("opciones", mysql.JSON(), nullable=False),
        sa.Column("obligatoria", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ulid"),
        sa.ForeignKeyConstraint(["coach_id"], ["coach.id"]),
        sa.CheckConstraint(
            "tipo in ('texto','texto_largo','numero','opcion','si_no')",
            name="tipo_pregunta_valido",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_pregunta_coach_orden", "pregunta_cuestionario", ["coach_id", "orden"])

    op.create_table(
        "respuesta_cuestionario",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(26), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "creado_en", mysql.DATETIME(fsp=3), nullable=False, server_default=sa.text("now(3)")
        ),
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("pregunta_id", sa.BigInteger(), nullable=False),
        sa.Column("valor", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ulid"),
        sa.UniqueConstraint("alumna_id", "pregunta_id", name="uq_respuesta_alumna_pregunta"),
        sa.ForeignKeyConstraint(["coach_id"], ["coach.id"]),
        sa.ForeignKeyConstraint(["alumna_id"], ["alumna.id"]),
        sa.ForeignKeyConstraint(["pregunta_id"], ["pregunta_cuestionario.id"]),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("ix_respuesta_cuestionario_coach_id", "respuesta_cuestionario", ["coach_id"])


def downgrade() -> None:
    op.drop_table("respuesta_cuestionario")
    op.drop_table("pregunta_cuestionario")
    op.drop_table("presentacion_coach")
