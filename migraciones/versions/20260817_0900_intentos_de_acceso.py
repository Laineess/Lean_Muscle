"""Intentos de acceso, para frenar la fuerza bruta.

Revision: 0007_intentos
Anterior: 0006_presentacion
Fecha: 2026-08-17

El acceso no tenía límite: se podían probar contraseñas a la velocidad que aguantara el
servidor. Ahora cada intento deja fila y el login corta cuando un correo o una IP agotan los
suyos dentro de la ventana.

La tabla no lleva `coach_id`: al momento de intentar todavía no se sabe de quién es el
correo, y uno inventado no es de nadie.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0007_intentos"
down_revision: str | None = "0006_presentacion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intento_de_acceso",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(26), nullable=False),
        sa.Column(
            "creado_en", mysql.DATETIME(fsp=3), nullable=False, server_default=sa.text("now(3)")
        ),
        sa.Column("correo", sa.String(180), nullable=False),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("exitoso", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ulid"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    # Los dos índices son los que hacen que contar sea barato: el conteo corre en cada
    # intento de acceso, incluidos los de un ataque.
    op.create_index("ix_intento_correo_cuando", "intento_de_acceso", ["correo", "creado_en"])
    op.create_index("ix_intento_ip_cuando", "intento_de_acceso", ["ip", "creado_en"])


def downgrade() -> None:
    op.drop_table("intento_de_acceso")
