"""Todo lo que entra por la API lleva tope, o MySQL corta y la respuesta es un 500.

Se lee del OpenAPI, así que cubre lo que haya. No necesita base de datos.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.main import app

#: Sin tope a propósito: contraseñas, que se guardan cifradas, y JSON libre.
PERDONADOS = {
    ("Credenciales", "contrasena"),
    ("CambioDeContrasena", "actual"),
    ("CambioDeContrasena", "nueva"),
    ("PlanGuardado", "contenido"),
}


def _esquemas_de_entrada() -> dict[str, dict[str, Any]]:
    """Cada cuerpo que acepta la API, por su nombre."""
    esp = app.openapi()
    comp = esp["components"]["schemas"]
    pendientes = []
    for ops in esp["paths"].values():
        for op in ops.values():
            if not isinstance(op, dict):
                continue
            cont = (op.get("requestBody") or {}).get("content", {})
            ref = cont.get("application/json", {}).get("schema", {}).get("$ref")
            if ref:
                pendientes.append(ref.split("/")[-1])

    vistos: dict[str, dict[str, Any]] = {}
    while pendientes:
        nombre = pendientes.pop()
        if nombre in vistos or nombre not in comp:
            continue
        vistos[nombre] = comp[nombre]
        for prop in comp[nombre].get("properties", {}).values():
            for anidado in _refs(prop):
                pendientes.append(anidado)
    return vistos


def _refs(prop: dict[str, Any]) -> list[str]:
    salida = []
    if "$ref" in prop:
        salida.append(prop["$ref"].split("/")[-1])
    for clave in ("anyOf", "oneOf", "allOf"):
        for opcion in prop.get(clave, []):
            salida.extend(_refs(opcion))
    if "items" in prop:
        salida.extend(_refs(prop["items"]))
    return salida


def _ramas(prop: dict[str, Any]) -> list[dict[str, Any]]:
    """Las alternativas de un campo opcional: `str | None` son dos ramas."""
    for clave in ("anyOf", "oneOf"):
        if clave in prop:
            return [r for r in prop[clave] if r.get("type") != "null"]
    return [prop]


def _sin_tope(prop: dict[str, Any]) -> str | None:
    for rama in _ramas(prop):
        tipo = rama.get("type")
        if tipo == "string" and rama.get("format") is None:
            if "maxLength" not in rama and "pattern" not in rama and "enum" not in rama:
                return "cadena sin `max_length`"
        if tipo in ("integer", "number"):
            techos = {"maximum", "exclusiveMaximum", "enum"}
            if not techos & set(rama):
                return f"{tipo} sin techo"
        if tipo == "array" and "maxItems" not in rama:
            return "lista sin `max_length`"
    return None


CASOS = sorted(
    (nombre, campo, prop)
    for nombre, esquema in _esquemas_de_entrada().items()
    for campo, prop in esquema.get("properties", {}).items()
)


@pytest.mark.parametrize(
    ("esquema", "campo", "prop"), CASOS, ids=lambda v: v if isinstance(v, str) else ""
)
def test_todo_lo_que_entra_lleva_tope(esquema: str, campo: str, prop: dict[str, Any]) -> None:
    if (esquema, campo) in PERDONADOS:
        return
    motivo = _sin_tope(prop)
    assert motivo is None, (
        f"{esquema}.{campo}: {motivo}. Sin tope el valor llega crudo a MySQL y la API "
        f"contesta 500 en vez de un 422 que diga cuál es el campo."
    )


def test_hay_esquemas_que_revisar() -> None:
    """Si el barrido dejara de encontrar cuerpos, la prueba pasaría sin comprobar nada."""
    assert len(CASOS) > 100
