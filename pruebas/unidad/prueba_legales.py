"""Los documentos legales se leen del repositorio y dicen qué les falta.

Un aviso de privacidad con huecos no cumple la LFPDPPP. Que el servicio los devuelva en
lugar de esconderlos es lo que permite a la pantalla decirlo.
"""

from __future__ import annotations

import pytest

from app.servicios import legales


class TestLectura:
    @pytest.mark.parametrize("clave", sorted(legales.DOCUMENTOS))
    def test_cada_documento_existe_y_trae_su_version(self, clave: str) -> None:
        d = legales.leer(clave)
        assert d.contenido.strip()
        assert d.version != "—", "no se encontró la línea de versión"
        assert d.actualizado != "—"

    def test_el_documento_desconocido_falla(self) -> None:
        with pytest.raises(KeyError):
            legales.leer("inventado")


class TestMarcadores:
    def test_la_marca_de_la_coach_se_sustituye(self) -> None:
        """Dejar `[NOMBRE_COMERCIAL_COACH]` a la vista de la alumna sería absurdo: el sistema
        sabe cómo se llama."""
        d = legales.leer("privacidad", coach="LeanMuscle")
        assert "[NOMBRE_COMERCIAL_COACH]" not in d.contenido
        assert "LeanMuscle" in d.contenido
        assert "NOMBRE_COMERCIAL_COACH" not in d.marcadores

    def test_lo_que_el_sistema_no_sabe_sigue_a_la_vista(self) -> None:
        """RFC y domicilio fiscal no los sabe nadie todavía. Ocultarlos haría creer que el
        documento está terminado."""
        d = legales.leer("privacidad", coach="LeanMuscle")
        assert d.marcadores, "los huecos pendientes deberían reportarse"
        assert not d.listo_para_publicar

    def test_los_marcadores_no_incluyen_enlaces_de_markdown(self) -> None:
        """`[texto](url)` no es un hueco. El patrón exige mayúsculas justo por eso."""
        for clave in legales.DOCUMENTOS:
            for marcador in legales.leer(clave).marcadores:
                assert marcador.isupper()
                assert " " not in marcador
