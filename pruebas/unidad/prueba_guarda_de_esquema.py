"""El motor de la aplicación no tira tablas fuera del entorno de pruebas.

La suite borra el esquema en cada corrida, y basta importar el motor desde un script suelto
—sin el `conftest` que redirige a la base `_pruebas`— para que apunte a la de desarrollo.
Ahí `drop_all` se lleva el esquema entero, y el aviso llega cuando la aplicación responde
500 porque falta una tabla.

Se comprueba la expresión y no una conexión: lo que decide es qué sentencias reconoce como
destructivas, y eso se puede probar sin base.
"""

from __future__ import annotations

import pytest

from app.datos.alcance import _DDL_DESTRUCTIVO


class TestLoQueSeFrena:
    @pytest.mark.parametrize(
        "sentencia",
        [
            "DROP TABLE coach",
            "drop table if exists foto",
            "DROP  TABLE  `chequeo`",
            "\n  DROP TABLE alumna",
            "DROP DATABASE leanmuscle",
            "drop schema leanmuscle",
            "TRUNCATE TABLE bitacora",
            "truncate sesion",
        ],
    )
    def test_las_destructivas(self, sentencia: str) -> None:
        assert _DDL_DESTRUCTIVO.match(sentencia)


class TestLoQueSigueCorriendo:
    @pytest.mark.parametrize(
        "sentencia",
        [
            "SELECT * FROM coach",
            "INSERT INTO alumna (nombre) VALUES ('x')",
            "UPDATE chequeo SET estado = 'validado'",
            # La purga borra filas, no tablas: eso tiene que seguir funcionando.
            "DELETE FROM anuncio WHERE id = 1",
            "CREATE TABLE nueva (id INT)",
            "ALTER TABLE coach ADD COLUMN x INT",
            # Un texto que menciona la palabra sin ser la sentencia.
            "SELECT 'drop table' AS aviso",
            "INSERT INTO bitacora (detalle) VALUES ('truncate')",
        ],
    )
    def test_las_inofensivas(self, sentencia: str) -> None:
        assert not _DDL_DESTRUCTIVO.match(sentencia)

    def test_un_indice_no_es_una_tabla(self) -> None:
        # `DROP INDEX` es reversible y no se lleva datos.
        assert not _DDL_DESTRUCTIVO.match("DROP INDEX ix_foto_purga ON foto")
