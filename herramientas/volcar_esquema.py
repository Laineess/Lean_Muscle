"""Vuelca el esquema a un .sql legible, sin una sola fila de datos.

Es para leer la base en el editor, no para restaurarla: quien la reconstruye es alembic. Por
eso no lleva datos —las fotos y los pesos de las alumnas no salen del servidor— ni AUTO_INCREMENT
en curso, que cambia en cada corrida y ensucia el diff.
"""

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy as sa

# Se corre a mano desde la raiz del repo, no como modulo instalado.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.datos.alcance import motor

DESTINO = "esquema.sql"

CABECERA = """-- Esquema de MyProgressPlan
--
-- Generado desde la base con `herramientas/volcar_esquema.py`. Es una foto para leer en el
-- editor: **no contiene datos** y no se usa para restaurar nada. La fuente de verdad del
-- esquema son los modelos de `app/datos/modelos.py` y la migracion de `migraciones/`.
--
-- Para abrirlo con resaltado y navegacion en VS Code basta la extension de SQL; para
-- consultar la base de verdad, una de cliente MySQL apuntando a la URL de tu config.env.
--
-- Generado: {cuando}
-- Motor:    {version}
-- Tablas:   {tablas}

SET FOREIGN_KEY_CHECKS = 0;

"""


def volcar() -> None:
    maquina = motor()
    with maquina.connect() as c:
        version = c.execute(sa.text("SELECT VERSION()")).scalar()
        nombres = sorted(
            r[0]
            for r in c.execute(
                sa.text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'"
                )
            )
        )

        partes = [
            CABECERA.format(
                cuando=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
                version=version,
                tablas=len(nombres),
            )
        ]
        for tabla in nombres:
            fila = c.execute(sa.text(f"SHOW CREATE TABLE `{tabla}`")).one()
            ddl = fila[1]
            # El contador de autoincremento va en marcha y cambia en cada alta: fuera, o el
            # archivo sale distinto cada vez que alguien se registra.
            ddl = re.sub(r"\s*AUTO_INCREMENT=\d+", "", ddl)
            partes.append(f"-- {'-' * 74}\n-- {tabla}\n-- {'-' * 74}\n\n{ddl};\n")

        partes.append("\nSET FOREIGN_KEY_CHECKS = 1;\n")

    open(DESTINO, "w", encoding="utf-8", newline="\n").write("\n".join(partes))
    print(f"{DESTINO}: {len(nombres)} tablas")


if __name__ == "__main__":
    volcar()
