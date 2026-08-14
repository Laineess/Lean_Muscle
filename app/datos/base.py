"""Base declarativa y convenciones de MySQL, fijadas de una sola vez."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, MetaData, String, TypeDecorator, func
from sqlalchemy.dialects import mysql
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.engine.interfaces import Dialect
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


class MarcaDeTiempo(TypeDecorator[datetime]):
    """DATETIME(3) que siempre entra y sale en UTC, con `tzinfo`.

    MySQL no guarda offset: sin esto, lo leído vuelve *naive* y compararlo con `ahora_utc()`
    lanza «can't compare offset-naive and offset-aware datetimes».

    La precisión es 3 porque hay orden que depende de ella —el hilo de mensajes, la bitácora,
    la cola de avisos—, y porque una columna sin fracción rechaza un `DEFAULT now(3)`.
    """

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "mysql":
            return dialect.type_descriptor(mysql.DATETIME(fsp=3))
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


MARCA_DE_TIEMPO = MarcaDeTiempo()


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCION_DE_NOMBRES)

    __abstract__ = True

    #: Llave interna. Nunca aparece en una URL.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    #: Identificador publico: es lo que va en las URLs, para que nadie enumere alumnas
    #: cambiando un numero en la barra de direcciones.
    ulid: Mapped[str] = mapped_column(CHAR(26), unique=True, default=nuevo_ulid, nullable=False)

    creado_en: Mapped[datetime] = mapped_column(
        MARCA_DE_TIEMPO, server_default=func.now(3), nullable=False
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
