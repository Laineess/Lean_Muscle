"""Todo aviso que sale por correo tiene su texto, y ese texto se puede rellenar.

Un aviso sin plantilla no falla al arrancar: falla cuando el trabajo programado intenta
mandarlo, de madrugada, y la alumna no recibe nada. Por eso se comprueba aquí.
"""

from __future__ import annotations

import re

import pytest

from app.dominio.avisos import Aviso, Canal, canales_de
from app.servicios.plantillas_correo import PLANTILLAS, redactar

#: Contexto con todas las variables que usan las plantillas. Si una plantilla nueva pide una
#: variable que no está aquí, la prueba falla y obliga a declararla.
CONTEXTO = {
    "nombre": "Andrea",
    "coach": "Mariana Cervantes",
    "clave": "7K4M-92QX",
    "momento": "13 de agosto de 2026 a las 09:14",
    "fecha": "17 de agosto de 2026",
    "hora_inicio": "09:00",
    "hora_fin": "09:45",
    "modalidad": "Videollamada",
    "detalle": "Revisar técnica de sentadilla.",
    "motivo": "Se empalmó una urgencia.",
    "monto": "$1,200.00",
    "vence": "14 de septiembre de 2026",
    "ciclo": 5,
    "mes": "abril",
}

POR_CORREO = [a for a in Aviso if Canal.CORREO in canales_de(a)]


def test_hay_avisos_por_correo() -> None:
    # Guarda contra un refactor que vacíe el mapa de canales y deje la prueba sin casos.
    assert POR_CORREO


@pytest.mark.parametrize("aviso", POR_CORREO, ids=lambda a: a.value)
def test_cada_aviso_por_correo_tiene_plantilla(aviso: Aviso) -> None:
    assert aviso in PLANTILLAS, f"{aviso.value} sale por correo pero no tiene texto"


@pytest.mark.parametrize("aviso", POR_CORREO, ids=lambda a: a.value)
def test_cada_plantilla_se_rellena_sin_huecos(aviso: Aviso) -> None:
    asunto, texto, html = redactar(aviso, CONTEXTO)

    # Una llave sin sustituir es un hueco visible en el correo de la alumna.
    assert "{" not in asunto and "}" not in asunto
    assert "{" not in texto and "}" not in texto

    assert len(asunto) > 8
    assert len(texto) > 40
    assert html.startswith("<div")


@pytest.mark.parametrize("aviso", POR_CORREO, ids=lambda a: a.value)
def test_el_html_lleva_la_alternativa_de_texto_completa(aviso: Aviso) -> None:
    """Los filtros de spam castigan un correo HTML sin equivalente en texto plano."""
    _, texto, html = redactar(aviso, CONTEXTO)
    primera_frase = texto.split("\n")[0]
    assert primera_frase in html


def test_no_hay_plantillas_huerfanas() -> None:
    sobrantes = set(PLANTILLAS) - set(Aviso)
    assert not sobrantes, f"plantillas sin aviso vigente: {sobrantes}"


def test_todos_los_enlaces_apuntan_al_dominio_del_servicio() -> None:
    """Un enlace a otro dominio en un correo de salud es exactamente lo que enseña a la
    alumna a confiar en correos falsos."""
    for aviso in POR_CORREO:
        _, _, html = redactar(aviso, CONTEXTO)
        for enlace in re.findall(r'href="([^"]+)"', html):
            assert enlace.startswith("https://myfittplan.com"), f"{aviso.value}: {enlace}"


def test_el_aviso_de_contrasena_explica_el_riesgo() -> None:
    """No es un correo de cortesía: es la señal de que alguien pudo entrar a su cuenta."""
    _, texto, _ = redactar(Aviso.CONTRASENA_CAMBIADA, CONTEXTO)
    assert "no fuiste tú" in texto.lower()


def test_el_aviso_de_purga_advierte_que_no_se_recupera() -> None:
    _, texto, _ = redactar(Aviso.PURGA_PROXIMA, CONTEXTO)
    assert "no se pueden recuperar" in texto.lower()
