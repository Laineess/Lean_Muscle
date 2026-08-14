"""Entorno de Alembic.

Las migraciones corren **sin alcance de inquilino**: tocan todas las tablas de todas las
coaches, que es exactamente para lo que existe la excepcion. Por eso importan el motor
directo y no `sesion_con_alcance`.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Importar los modelos puebla Base.metadata; sin esta linea el autogenerate ve un esquema vacio.
import app.datos.modelos  # noqa: F401
from app.config import ajustes
from app.datos.base import Base

config = context.config
config.set_main_option("sqlalchemy.url", ajustes().bd_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def correr_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def correr_online() -> None:
    conectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with conectable.connect() as conexion:
        context.configure(
            connection=conexion,
            target_metadata=target_metadata,
            # compare_type detecta cambios de DECIMAL(5,1) a DECIMAL(6,2); sin esto,
            # una migracion de precision pasa desapercibida.
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    correr_offline()
else:
    correr_online()
