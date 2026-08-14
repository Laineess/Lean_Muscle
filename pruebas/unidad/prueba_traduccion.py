"""Toda regla de negocio tiene texto para la usuaria, y ese texto vive en un solo lugar."""

from __future__ import annotations

import pytest

from app.compartido.errores import Codigo
from app.rutas.traduccion import RESPUESTAS, respuesta_para


@pytest.mark.parametrize("codigo", list(Codigo), ids=lambda c: c.value)
def test_cada_codigo_tiene_texto(codigo: Codigo) -> None:
    # Una regla nueva sin su mensaje se descubre aqui, no cuando la alumna ve un 500 pelado.
    estado, texto = respuesta_para(codigo)
    assert 400 <= estado <= 500
    assert len(texto) > 15


def test_no_hay_textos_huerfanos() -> None:
    sobrantes = set(RESPUESTAS) - set(Codigo)
    assert not sobrantes, f"textos sin código vigente: {sobrantes}"


def test_los_estados_siguen_la_convencion() -> None:
    # 422 dato invalido, 409 conflicto de estado, 401/403 acceso. Nada de 400 genérico.
    permitidos = {401, 403, 409, 422, 500}
    fuera = {c: RESPUESTAS[c][0] for c in RESPUESTAS if RESPUESTAS[c][0] not in permitidos}
    assert not fuera, f"estados fuera de convención: {fuera}"
