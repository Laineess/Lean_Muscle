"""Toda lectura y escritura de datos sensibles deja rastro.

Es obligación del Anexo Legal §6, no una convención del equipo. Y una convención que solo
vive en un comentario se olvida: esta prueba lee el árbol sintáctico de las rutas y falla si
alguien agrega un endpoint que toca datos sensibles sin registrarlo.

Se comprueba estáticamente y no con una base de datos a propósito: así corre en cada cambio,
sin MySQL, y bloquea el olvido antes de que llegue a producción.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
RUTAS = RAIZ / "app" / "rutas"

#: Modelos cuya lectura o escritura obliga a registrar.
SENSIBLES = {"Foto", "HistorialClinico", "Chequeo", "Medida", "Pesaje", "Consentimiento"}

#: Funciones del servicio que cumplen la obligación.
REGISTRADORES = {"registrar", "registrar_acceso"}


def _funciones_de(archivo: Path) -> list[ast.FunctionDef]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    return [n for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef)]


def _es_endpoint(funcion: ast.FunctionDef) -> bool:
    """Un endpoint es una función decorada con @ruteador.<método>(...)."""
    for d in funcion.decorator_list:
        objetivo = d.func if isinstance(d, ast.Call) else d
        if isinstance(objetivo, ast.Attribute) and isinstance(objetivo.value, ast.Name):
            if objetivo.value.id == "ruteador":
                return True
    return False


def _nombres_usados(funcion: ast.FunctionDef) -> set[str]:
    nombres: set[str] = set()
    for nodo in ast.walk(funcion):
        if isinstance(nodo, ast.Name):
            nombres.add(nodo.id)
        elif isinstance(nodo, ast.Attribute):
            nombres.add(nodo.attr)
        elif isinstance(nodo, ast.alias):
            nombres.add(nodo.asname or nodo.name.split(".")[-1])
    return nombres


def _registra(funcion: ast.FunctionDef) -> bool:
    return bool(_nombres_usados(funcion) & REGISTRADORES)


def _toca_sensible(funcion: ast.FunctionDef) -> set[str]:
    return _nombres_usados(funcion) & SENSIBLES


#: Endpoints exentos, cada uno con su razón. Agregar aquí obliga a justificarlo.
EXENTOS: dict[str, str] = {
    # La alumna leyendo lo suyo no es un acceso de tercero: `acceso_sensible` responde
    # «¿quién más vio mi expediente?», y ella no es «alguien más».
    "inicio": "la alumna lee sus propios datos",
    "plan": "la alumna lee su propio plan",
    "mi_cuestionario": "la alumna lee lo que ella misma contestó",
    # Solo devuelve agregados y estados; no expone contenido clínico ni fotografías.
    "panel": "solo agregados de la cartera",
    "alumnas": "solo agregados de la cartera",
    # Escribe el plan, que no es dato de salud: es la prescripción que la coach redacta.
    "guardar_plan": "el plan no es dato de salud del titular",
    # La alumna capturando lo suyo. El rastro se toma al **enviar** (`enviar_chequeo`), que
    # es cuando el dato entra al expediente. Anotar cada guardado de borrador metería una
    # fila por tecleo en una tabla de cinco años de retención: sería ruido, no auditoría.
    "abrir_chequeo": "abrir un borrador propio no mueve dato sensible; el rastro va al enviar",
    "guardar_chequeo": "borrador propio; el rastro va al enviar",
    # Cuenta chequeos para decirle a la coach cuánto se va a borrar. No abre ninguno: no
    # hay peso, ni medida, ni foto, ni feedback en la respuesta.
    "revisar_baja": "solo cuenta cuántos chequeos se van a borrar",
}


def endpoints_sensibles() -> list[tuple[str, str, ast.FunctionDef]]:
    casos: list[tuple[str, str, ast.FunctionDef]] = []
    for archivo in sorted(RUTAS.rglob("api*.py")):
        for funcion in _funciones_de(archivo):
            if not _es_endpoint(funcion):
                continue
            if funcion.name in EXENTOS:
                continue
            if _toca_sensible(funcion):
                casos.append((archivo.name, funcion.name, funcion))
    return casos


def test_hay_endpoints_que_tocan_datos_sensibles() -> None:
    """Guarda contra un refactor que deje la prueba sin casos y parezca que todo pasa."""
    assert endpoints_sensibles(), "el detector no encontró ningún endpoint sensible"


@pytest.mark.parametrize(
    ("archivo", "nombre", "funcion"),
    endpoints_sensibles(),
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_cada_endpoint_sensible_registra(
    archivo: str, nombre: str, funcion: ast.FunctionDef
) -> None:
    modelos = sorted(_toca_sensible(funcion))
    assert _registra(funcion), (
        f"{archivo}::{nombre} toca {modelos} y no llama a bitacora.registrar ni a "
        "registrar_acceso. Si de verdad no corresponde, decláralo en EXENTOS con su motivo."
    )


def test_los_exentos_siguen_existiendo() -> None:
    """Una exención que ya no corresponde a ningún endpoint es ruido que esconde el olvido
    siguiente."""
    existentes = {
        f.name
        for archivo in RUTAS.rglob("api*.py")
        for f in _funciones_de(archivo)
        if _es_endpoint(f)
    }
    huerfanos = set(EXENTOS) - existentes
    assert not huerfanos, f"exenciones sin endpoint: {sorted(huerfanos)}"


def test_las_descargas_de_pdf_registran_el_acceso() -> None:
    """Una descarga es justo el momento en que el dato sale de la plataforma."""
    documentos = RUTAS / "api_documentos.py"
    for funcion in _funciones_de(documentos):
        if funcion.name in {"plan_nutricion", "rutina"}:
            assert _registra(funcion), f"{funcion.name} no registra el acceso"


def test_el_servicio_de_bitacora_no_guarda_valores_sensibles() -> None:
    """`detalle` guarda qué cambió, no el dato.

    Copiar el peso o el historial aquí duplicaría el dato sensible en una tabla de cinco
    años de retención que sobrevive a la cancelación: lo contrario de minimizar datos.
    """
    fuente = (RAIZ / "app" / "servicios" / "bitacora.py").read_text(encoding="utf-8")
    assert "campos_cambiados" in fuente
    assert "no el dato en sí" in fuente
