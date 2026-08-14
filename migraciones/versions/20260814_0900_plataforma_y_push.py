"""Suscripción y cobros de las coaches, y suscripciones push.

Revision: 0002_plataforma
Anterior: 0001_inicial
Fecha: 2026-08-14

Tres tablas nuevas:

- `suscripcion_coach` y `cobro_coach`: lo que cada coach le paga a la plataforma. **No llevan
  el filtro por inquilino**: son datos *sobre* el inquilino, no *del* inquilino, igual que la
  propia fila de `coach`. Si lo llevaran, el superadmin —que no es coach de nadie— no vería
  ninguna.
- `suscripcion_push`: un navegador suscrito a notificaciones. Esa sí es del inquilino.

Se escriben a mano en lugar de con `create_all` porque la base ya existe: `create_all` es
para la instantánea inicial, no para un cambio incremental.

**Cada tabla se crea solo si falta.** La migración inicial usa `Base.metadata.create_all()`,
que crea lo que digan los modelos *en el momento de correrla*: en una base creada desde cero
hoy, esa primera migración ya deja estas tres tablas puestas, y volver a crearlas reventaría.
En una base creada antes, no están. Las dos situaciones son reales y ninguna debe fallar.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0002_plataforma"
down_revision: str | None = "0001_inicial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def _columnas_base() -> list[sa.Column]:
    return [
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(26), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(3),
            nullable=False,
        ),
    ]


def _falta(tabla: str) -> bool:
    return not sa.inspect(op.get_bind()).has_table(tabla)


def upgrade() -> None:
    if _falta("suscripcion_coach"):
        _crear_suscripcion_coach()
    if _falta("cobro_coach"):
        _crear_cobro_coach()
    if _falta("suscripcion_push"):
        _crear_suscripcion_push()


def _crear_suscripcion_coach() -> None:
    op.create_table(
        "suscripcion_coach",
        *_columnas_base(),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("plan", sa.String(40), server_default="basico", nullable=False),
        sa.Column("precio", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("periodicidad", sa.String(10), server_default="mensual", nullable=False),
        sa.Column("estado", sa.String(20), server_default="cortesia", nullable=False),
        sa.Column("inicia_en", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_suscripcion_coach"),
        sa.UniqueConstraint("ulid", name="uq_suscripcion_coach_ulid"),
        sa.UniqueConstraint("coach_id", name="uq_suscripcion_coach"),
        sa.ForeignKeyConstraint(["coach_id"], ["coach.id"], name="fk_suscripcion_coach_coach_id"),
        sa.CheckConstraint(
            "estado in ('cortesia','al_corriente','por_vencer','vencida','cancelada')",
            name="ck_suscripcion_coach_estado_valido",
        ),
        sa.CheckConstraint(
            "periodicidad in ('mensual','anual')",
            name="ck_suscripcion_coach_periodicidad_valida",
        ),
        **ARGS,
    )


def _crear_cobro_coach() -> None:
    op.create_table(
        "cobro_coach",
        *_columnas_base(),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("metodo", sa.String(40), server_default="transferencia", nullable=False),
        sa.Column("periodo_inicia", sa.Date(), nullable=True),
        sa.Column("periodo_termina", sa.Date(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("registrado_por", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_cobro_coach"),
        sa.UniqueConstraint("ulid", name="uq_cobro_coach_ulid"),
        sa.ForeignKeyConstraint(["coach_id"], ["coach.id"], name="fk_cobro_coach_coach_id"),
        sa.ForeignKeyConstraint(
            ["registrado_por"], ["usuario.id"], name="fk_cobro_coach_registrado_por"
        ),
        **ARGS,
    )
    op.create_index("ix_cobro_coach_fecha", "cobro_coach", ["coach_id", "fecha"])


def _crear_suscripcion_push() -> None:
    op.create_table(
        "suscripcion_push",
        *_columnas_base(),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("endpoint", sa.String(500), nullable=False),
        # El endpoint es largo y MySQL no indexa 500 caracteres cómodamente: la unicidad va
        # sobre su hash.
        sa.Column("endpoint_hash", sa.String(64), nullable=False),
        sa.Column("p256dh", sa.String(255), nullable=False),
        sa.Column("auth", sa.String(255), nullable=False),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("ultimo_envio_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fallos", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_suscripcion_push"),
        sa.UniqueConstraint("ulid", name="uq_suscripcion_push_ulid"),
        sa.UniqueConstraint("endpoint_hash", name="uq_suscripcion_endpoint"),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name="fk_suscripcion_push_usuario_id"
        ),
        **ARGS,
    )
    op.create_index("ix_suscripcion_push_coach_id", "suscripcion_push", ["coach_id"])
    op.create_index("ix_suscripcion_usuario", "suscripcion_push", ["usuario_id"])


def downgrade() -> None:
    for tabla in ("suscripcion_push", "cobro_coach", "suscripcion_coach"):
        if sa.inspect(op.get_bind()).has_table(tabla):
            op.drop_table(tabla)
