"""Dos errores de transporte que un rol encontraría exactamente igual: el cuerpo que excede
el tope (413) y un fallo del servidor (500).

El 413 lo corta un *middleware* antes de que ninguna ruta lea el cuerpo, así que no hace
falta base de datos. El 500 es el manejador genérico: se prueba con una ruta trampa que
revienta, para ver que devuelve el mismo JSON que el resto y no el «Internal Server Error»
en texto plano que FastAPI manda por defecto.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.config import ajustes
from app.main import app

#: Un JSON con este cuerpo supera `LM_CUERPO_MAXIMO_BYTES` (16 MB por defecto).
_MAS_DEL_TOPE = "x" * (ajustes().cuerpo_maximo_bytes + 1)


def test_un_cuerpo_enorme_se_rechaza_antes_de_leerse() -> None:
    cliente = TestClient(app)
    respuesta = cliente.post(
        "/api/auth/login",
        content=_MAS_DEL_TOPE,
        headers={"Content-Type": "application/json"},
    )
    assert respuesta.status_code == 413
    assert "mensaje" in respuesta.json()


def test_un_error_del_servidor_vuelve_json_y_no_texto_plano() -> None:
    @app.get("/ruta-que-revienta")
    async def revienta(_: Request) -> JSONResponse:
        raise RuntimeError("pila oculta")

    try:
        cliente = TestClient(app, raise_server_exceptions=False)
        respuesta = cliente.get("/ruta-que-revienta")
    finally:
        app.router.routes = [
            r for r in app.router.routes if getattr(r, "path", None) != "/ruta-que-revienta"
        ]

    assert respuesta.status_code == 500
    cuerpo = respuesta.json()
    assert "mensaje" in cuerpo
    assert "pila oculta" not in str(cuerpo)