"""Vuelca el esquema **y los datos** a un .sql legible para leer en el editor.

Hermana de `volcar_esquema.py`, que solo trae el DDL. Esta tambien incluye un `INSERT` por
tabla con las filas actuales, para ver cada registro sin abrir un cliente MySQL.

Advertencia: con esto no se restaura nada —para reconstruir esta el alembic— y la fuente de
verdad son los modelos de `app/datos/modelos.py`. Se puede correr contra la copia local
(lena) o, en el VPS, contra la de produccion; el archivo sale igual de legible en ambos.
"""

import json
import re
import sys
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path

import sqlalchemy as sa

# Se corre a mano desde la raiz del repo, no como modulo instalado.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.datos.alcance import motor

DESTINO = "volcado_datos.sql"

CABECERA = """-- Volcado de MyProgressPlan (esquema + datos)
--
-- Generado desde la base con `herramientas/volcar_datos.py` para leer en el editor:
-- **no se usa para restaurar** (eso lo hace alembic) y los datos son una foto del momento.
-- Las contrasenas salen ya como hash, nunca en claro.
--
-- Generado: {cuando}
-- Motor:    {version}
-- Tablas:   {tablas}

SET FOREIGN_KEY_CHECKS = 0;

"""


def _literal(valor: object) -> str:
    """Un valor listo para ir entre parentesis de un INSERT de MySQL."""
    if valor is None:
        return "NULL"
    if isinstance(valor, (datetime, date, time)):
        return f"'{valor.isoformat(sep=' ')}'" if isinstance(valor, datetime) else f"'{valor.isoformat()}'"
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, (Decimal, int, float)):
        return str(valor)
    if isinstance(valor, (bytes, bytearray)):
        return f"X'{bytes(valor).hex()}'"
    if isinstance(valor, (dict, list)):
        return "'" + json.dumps(valor, ensure_ascii=False).replace("'", "''") + "'"
    # str y lo demas (bool ya se descarto arriba)
    texto = str(valor)
    return "'" + texto.replace("\\", "\\\\").replace("'", "''") + "'"


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
            # El contador de autoincremento va en marcha y cambia en cada alta: fuera.
            ddl = re.sub(r"\s*AUTO_INCREMENT=\d+", "", ddl)
            partes.append(f"-- {'-' * 74}\n-- {tabla}\n-- {'-' * 74}\n\n{ddl};\n")

            columnas = [
                r[0] for r in c.execute(sa.text(f"SHOW COLUMNS FROM `{tabla}`"))
            ]
            total = c.execute(sa.text(f"SELECT COUNT(*) FROM `{tabla}`")).scalar()
            if total > 0:
                filas = c.execute(
                    sa.text(f"SELECT * FROM `{tabla}` ORDER BY 1")
                ).fetchall()
                valores = [", ".join(_literal(v) for v in f) for f in filas]
                col = ", ".join(f"`{x}`" for x in columnas)
                partes.append(f"-- {total} registros\nINSERT INTO `{tabla}` ({col}) VALUES")
                partes.append(",\n".join(f"({v})" for v in valores) + ";\n")
            else:
                partes.append("-- sin registros\n")

        partes.append("\nSET FOREIGN_KEY_CHECKS = 1;\n")

    open(DESTINO, "w", encoding="utf-8", newline="\n").write("\n".join(partes))
    print(f"{DESTINO}: {len(nombres)} tablas")


if __name__ == "__main__":
    volcar()