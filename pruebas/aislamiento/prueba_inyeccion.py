"""Ninguna consulta se arma pegando texto.

La inyección de SQL no se evita revisando entradas una por una: se evita porque el valor
nunca llega a formar parte de la sentencia. Todo pasa por SQLAlchemy, que manda los valores
como parámetros, y el motor los trata como datos aunque contengan comillas o un `DROP`.

Esta prueba lee el árbol sintáctico y falla si alguien arma SQL concatenando o interpolando.
Se comprueba estáticamente, sin base de datos, para que corra en cada cambio.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
FUENTES = [RAIZ / "app"]

#: Funciones que reciben SQL en crudo. Pasarles algo que no sea una cadena literal es lo que
#: abre la puerta. `text` solo cuenta como llamada suelta —`from sqlalchemy import text`—:
#: como método, `.text(...)` casi siempre es otra cosa, por ejemplo el de Pillow.
CRUDAS_SUELTAS = {"text"}
CRUDAS_METODO = {"exec_driver_sql", "execute_sql"}

#: Archivos donde sí corresponde SQL literal, con su motivo.
EXENTOS = {
    # Fija la zona horaria de la conexión con una constante, sin ningún valor de fuera.
    "alcance.py": "SET time_zone con literal fijo",
    # Las migraciones son DDL escrito a mano; no reciben datos de nadie.
    "env.py": "migraciones",
}


def _archivos() -> list[Path]:
    return sorted(a for raiz in FUENTES for a in raiz.rglob("*.py"))


def _es_literal(nodo: ast.AST) -> bool:
    """Una cadena literal, o varias pegadas entre sí, no llevan nada de fuera."""
    if isinstance(nodo, ast.Constant):
        return isinstance(nodo.value, str)
    if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Add):
        return _es_literal(nodo.left) and _es_literal(nodo.right)
    return False


def _llamadas_crudas(archivo: Path) -> list[tuple[int, str]]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    hallazgos: list[tuple[int, str]] = []

    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        objetivo = nodo.func
        if isinstance(objetivo, ast.Attribute):
            interesa = objetivo.attr in CRUDAS_METODO
        elif isinstance(objetivo, ast.Name):
            interesa = objetivo.id in CRUDAS_SUELTAS or objetivo.id in CRUDAS_METODO
        else:
            interesa = False

        if not interesa or not nodo.args:
            continue
        if not _es_literal(nodo.args[0]):
            hallazgos.append((nodo.lineno, ast.dump(nodo.args[0])[:80]))

    return hallazgos


@pytest.mark.parametrize("archivo", _archivos(), ids=lambda a: a.name)
def test_ninguna_consulta_se_arma_pegando_texto(archivo: Path) -> None:
    if archivo.name in EXENTOS:
        return
    hallazgos = _llamadas_crudas(archivo)
    assert not hallazgos, (
        f"{archivo.relative_to(RAIZ)} arma SQL con un valor variable: {hallazgos}. "
        "Usa la sentencia del ORM o pásale parámetros con `text(...).bindparams(...)`."
    )


def test_las_contrasenas_nunca_se_guardan_en_claro() -> None:
    """Argon2 en el único sitio donde se escribe el hash."""
    fuente = (RAIZ / "app" / "servicios" / "seguridad.py").read_text(encoding="utf-8")
    assert "argon2" in fuente.lower()
    assert "hash_contrasena" in fuente


def test_la_semilla_no_corre_en_produccion() -> None:
    """Sembrar datos de demostración contra la base real crearía cuentas con contraseña
    conocida: es literalmente una puerta trasera."""
    fuente = (RAIZ / "app" / "semilla.py").read_text(encoding="utf-8")
    assert "es_produccion" in fuente, "la semilla no comprueba el entorno"
