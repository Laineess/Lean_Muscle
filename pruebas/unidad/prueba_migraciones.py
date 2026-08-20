"""La cadena de migraciones tiene que poder replicarse.

La primera migración llamaba a `Base.metadata.create_all`, que refleja los modelos de **hoy**
y no el esquema del día que se escribió. Sobre una base vacía creaba de golpe tablas y
columnas que las migraciones siguientes volvían a crear, y `alembic upgrade head` reventaba
en la sexta. Nadie lo vio porque nunca se corrió desde cero: la base de desarrollo se armó
una vez y se fue parcheando.

Estas pruebas leen los archivos, no la base: lo que vigilan es que no vuelva a colarse un
`create_all` ni una revisión huérfana, y eso se ve en el texto.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

VERSIONES = Path(__file__).resolve().parents[2] / "migraciones" / "versions"
ARCHIVOS = sorted(VERSIONES.glob("*.py"))


def _revision(src: str, campo: str) -> str | None:
    m = re.search(rf"^{campo}: str \| None = (.+)$|^{campo}: str = (.+)$", src, re.M)
    if not m:
        return None
    crudo = (m.group(1) or m.group(2)).strip()
    return None if crudo == "None" else ast.literal_eval(crudo)


class TestNingunaMiraLosModelos:
    """Una migración describe el esquema de su día, congelado. Si lo deriva de los modelos,
    cambia sola cuando cambian ellos y deja de reproducir lo que decía."""

    #: Lo que convierte una migración en un espejo de los modelos en vez de un registro.
    PROHIBIDOS = frozenset({"create_all", "drop_all", "sorted_tables"})

    @pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda p: p.name)
    def test_no_usa_el_metadata_de_los_modelos(self, archivo: Path) -> None:
        # Se lee el árbol y no el texto: el propio comentario de la migración nombra
        # `create_all` para explicar por qué está prohibido, y buscar la cadena lo cazaría.
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        usados = {
            n.attr
            for n in ast.walk(arbol)
            if isinstance(n, ast.Attribute) and n.attr in self.PROHIBIDOS
        }
        assert not usados, f"{archivo.name} usa {sorted(usados)} sobre el metadata"


class TestLaCadenaEsUnaSola:
    def test_hay_migraciones(self) -> None:
        assert ARCHIVOS

    def test_una_sola_raiz(self) -> None:
        raices = [
            f.name
            for f in ARCHIVOS
            if _revision(f.read_text(encoding="utf-8"), "down_revision") is None
        ]
        assert len(raices) == 1, f"raíces: {raices}"

    def test_ninguna_apunta_a_una_revision_que_no_existe(self) -> None:
        revisiones = {_revision(f.read_text(encoding="utf-8"), "revision") for f in ARCHIVOS}
        for f in ARCHIVOS:
            anterior = _revision(f.read_text(encoding="utf-8"), "down_revision")
            if anterior is not None:
                assert anterior in revisiones, f"{f.name} cuelga de «{anterior}», que no existe"

    def test_ninguna_revision_repetida(self) -> None:
        revisiones = [_revision(f.read_text(encoding="utf-8"), "revision") for f in ARCHIVOS]
        assert len(revisiones) == len(set(revisiones))

    def test_la_cadena_llega_de_la_raiz_a_la_punta(self) -> None:
        """Sin bifurcaciones ni islas: se recorre entera desde la raíz."""
        porAnterior = {}
        for f in ARCHIVOS:
            src = f.read_text(encoding="utf-8")
            porAnterior.setdefault(_revision(src, "down_revision"), []).append(
                _revision(src, "revision")
            )
        visitadas = 0
        actual: str | None = None
        while actual in porAnterior:
            siguientes = porAnterior[actual]
            assert len(siguientes) == 1, f"«{actual}» tiene {len(siguientes)} continuaciones"
            actual = siguientes[0]
            visitadas += 1
        assert visitadas == len(ARCHIVOS)
