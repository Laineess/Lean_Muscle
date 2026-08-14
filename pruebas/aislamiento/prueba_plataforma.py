"""El superadmin no puede ver datos de alumnas. Comprobado leyendo el codigo.

`app/datos/repos/plataforma.py` es la unica capa que cruza inquilinos por diseno, asi que es
la que con mas facilidad se convierte en una puerta trasera. Esta prueba lee su arbol
sintactico y falla si de una tabla con datos de alumnas sale algo que no sea un agregado o
una columna declarada aqui abajo.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
FUENTE = RAIZ / "app" / "datos" / "repos" / "plataforma.py"

#: Tablas cuyo contenido pertenece a la alumna, no a la plataforma.
CON_DATOS_DE_ALUMNAS = {
    "Alumna",
    "Chequeo",
    "Medida",
    "Pesaje",
    "Foto",
    "HistorialClinico",
    "Consentimiento",
    "Mensaje",
    "Pago",
    "Plan",
    "Cita",
    "Notificacion",
    "AccesoSensible",
    "Bitacora",
}

#: Funciones de SQL que devuelven un número, no una fila.
AGREGADOS = {"count", "sum", "max", "min", "avg", "if_", "date_format"}

#: Columnas que sí pueden salir de esas tablas, cada una con su razón.
#:
#: Agregar una aquí obliga a justificarla, que es el punto: el trabajo de convencerse de que
#: una columna nueva no identifica a nadie es exactamente el que hay que hacer.
COLUMNAS_PERMITIDAS: dict[str, str] = {
    "id": "solo aparece dentro de count(); nunca se proyecta",
    "coach_id": "es el inquilino, no la persona: sirve para agrupar",
    "estado": "borrador/validado, activa/baja. No dice nada de nadie",
    "fecha": "solo dentro de comparaciones para contar por mes",
    "bytes": "peso en disco de una imagen, para cobrar almacenamiento",
    "purgada_en": "si la foto ya se borró. Es metadato de retención",
    "tomada_en": "cuándo toca purgarla. Metadato de retención",
    "creado_en": "sello de tiempo de la bitácora",
    "actor_tipo": "coach o alumna, sin decir cuál",
    "accion": "qué se hizo, no a quién",
    "entidad": "sobre qué tabla, no sobre qué fila",
}


def _arbol() -> ast.Module:
    return ast.parse(FUENTE.read_text(encoding="utf-8"), filename=str(FUENTE))


def _es_agregado(nodo: ast.AST) -> bool:
    """`func.count(...)`, `func.sum(...)` y compañía."""
    if not isinstance(nodo, ast.Call):
        return False
    objetivo = nodo.func
    return isinstance(objetivo, ast.Attribute) and objetivo.attr in AGREGADOS


def _referencias_sueltas(nodo: ast.AST) -> list[str]:
    """Usos de una tabla sensible que **no** están envueltos en un agregado.

    Devuelve la descripción de cada uso problemático: `Alumna` a secas, o `Alumna.nombre`.
    """
    problemas: list[str] = []

    def recorrer(actual: ast.AST, dentro_de_agregado: bool) -> None:
        if _es_agregado(actual):
            for hijo in ast.iter_child_nodes(actual):
                recorrer(hijo, True)
            return

        if isinstance(actual, ast.Attribute):
            base = actual.value
            if isinstance(base, ast.Name) and base.id in CON_DATOS_DE_ALUMNAS:
                if not dentro_de_agregado and actual.attr not in COLUMNAS_PERMITIDAS:
                    problemas.append(f"{base.id}.{actual.attr}")
                return

        if isinstance(actual, ast.Name) and actual.id in CON_DATOS_DE_ALUMNAS:
            # `select(Alumna)` a secas: trae la fila entera.
            problemas.append(actual.id)
            return

        for hijo in ast.iter_child_nodes(actual):
            recorrer(hijo, dentro_de_agregado)

    recorrer(nodo, False)
    return problemas


def _selects() -> list[ast.Call]:
    return [
        n
        for n in ast.walk(_arbol())
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "select"
    ]


def test_hay_consultas_que_revisar() -> None:
    """Guarda contra un refactor que deje la prueba sin casos y parezca que todo pasa."""
    assert _selects(), "no encontré ninguna consulta en plataforma.py"


@pytest.mark.parametrize(
    "consulta",
    _selects(),
    ids=lambda c: f"linea-{c.lineno}",
)
def test_ninguna_consulta_devuelve_datos_de_alumnas(consulta: ast.Call) -> None:
    """De las tablas de alumnas solo salen agregados y columnas declaradas."""
    problemas: list[str] = []
    for argumento in consulta.args:
        problemas.extend(_referencias_sueltas(argumento))

    assert not problemas, (
        f"plataforma.py línea {consulta.lineno}: la consulta expone {sorted(set(problemas))}. "
        "El panel del superadmin no puede ver datos de alumnas. Si de verdad es un dato "
        "agregado, envuélvelo en func.count/sum; si es una columna que no identifica a nadie, "
        "decláralo en COLUMNAS_PERMITIDAS con su razón."
    )


def test_las_columnas_permitidas_llevan_su_razon() -> None:
    """Una excepción sin motivo escrito es una excepción que nadie recuerda por qué existe."""
    sin_razon = [c for c, razon in COLUMNAS_PERMITIDAS.items() if len(razon.strip()) < 15]
    assert not sin_razon, f"sin justificar: {sin_razon}"


def test_las_funciones_publicas_no_devuelven_modelos_de_alumnas() -> None:
    """La otra mitad: aunque la consulta esté bien, el tipo de retorno lo delataría.

    Si una función declarara `-> list[Alumna]`, algo se está devolviendo entero aunque el
    `select` parezca inocente.
    """
    prohibidos = CON_DATOS_DE_ALUMNAS - {"Bitacora"}  # Bitácora sale proyectada a columnas
    for funcion in ast.walk(_arbol()):
        if not isinstance(funcion, ast.FunctionDef) or funcion.name.startswith("_"):
            continue
        if funcion.returns is None:
            continue
        nombres = {n.id for n in ast.walk(funcion.returns) if isinstance(n, ast.Name)}
        fuga = nombres & prohibidos
        assert not fuga, f"{funcion.name} devuelve {sorted(fuga)}"
