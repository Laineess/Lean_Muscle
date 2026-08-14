"""Esquema inicial.

Revision: 0001_inicial
Anterior: None
Fecha: 2026-08-13

Esta primera migración crea el esquema completo desde los modelos, en lugar de repetir a
mano las 25 tablas. Es la instantánea base; **a partir de aquí toda migración se genera con
`alembic revision --autogenerate` y se revisa a mano**, que es donde se ven de verdad los
cambios de columna.

El `downgrade` sí borra todo: solo tiene sentido para volver a cero en desarrollo.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.datos.base import Base

# Importar los modelos puebla Base.metadata. Sin esta línea el esquema sale vacío.
import app.datos.modelos  # noqa: F401

revision: str = "0001_inicial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
