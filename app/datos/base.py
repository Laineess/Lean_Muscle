"""Base declarativa y convenciones de MySQL, fijadas de una sola vez."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, MetaData, String, func
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from ulid import ULID

#: Nombres deterministas para indices y constraints. Sin esto, Alembic genera nombres
#: distintos en cada maquina y los downgrade dejan de aplicar.
CONVENCION_DE_NOMBRES = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}

ARGS_DE_TABLA: dict[str, Any] = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def nuevo_ulid() -> str:
    return str(ULID())


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCION_DE_NOMBRES)

    __abstract__ = True

    #: Llave interna. Nunca aparece en una URL.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    #: Identificador publico: es lo que va en las URLs, para que nadie enumere alumnas
    #: cambiando un numero en la barra de direcciones.
    ulid: Mapped[str] = mapped_column(CHAR(26), unique=True, default=nuevo_ulid, nullable=False)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(3), nullable=False
    )


class BaseMultiInquilino(Base):
    """Toda entidad que hereda de aqui queda filtrada por `coach_id` automaticamente.

    El filtro lo inyecta `app/datos/alcance.py` con los ganchos de SQLAlchemy 2.0.
    Es la reposicion manual del Row Level Security que MySQL no ofrece.
    """

    __abstract__ = True

    coach_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)


TEXTO_CORTO = String(120)
TEXTO_MEDIO = String(255)
