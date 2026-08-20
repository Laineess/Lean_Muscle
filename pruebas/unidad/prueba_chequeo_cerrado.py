"""Un chequeo resuelto deja de admitir cambios.

No todo cambio es una transición, y ahí estaba el agujero: estimar el porcentaje de grasa o
borrar una foto no mueven el estado, así que pasaban por encima de la máquina sin tocarla.
El de la grasa es el que muerde — de ese número sale el plan, y reescribirlo después de
validar deja el plan publicado calculado sobre un valor que ya no está en el expediente.
"""

from __future__ import annotations

import pytest

from app.compartido.errores import Codigo, ErrorDeDominio
from app.dominio.chequeo import (
    ABIERTO_A_LA_ALUMNA,
    ABIERTO_A_LA_COACH,
    EstadoChequeo,
    exigir_abierto,
)

#: Cerrado para todos. `rechazado_calidad` no está aquí: para la coach está resuelto, pero
#: para la alumna se reabre — es justo el estado en el que vuelve a capturar.
CERRADOS = (EstadoChequeo.VALIDADO, EstadoChequeo.DESCARTADO)

#: Los que ya no admiten ni una decisión más de la coach.
RESUELTOS_PARA_LA_COACH = (*CERRADOS, EstadoChequeo.RECHAZADO_CALIDAD)


class TestLoQueLaCoachTodaviaPuedeTocar:
    def test_mientras_espera_resolucion_puede(self) -> None:
        exigir_abierto(EstadoChequeo.PENDIENTE_EVALUACION, ABIERTO_A_LA_COACH)

    @pytest.mark.parametrize("estado", RESUELTOS_PARA_LA_COACH)
    def test_resuelto_ya_no(self, estado: EstadoChequeo) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            exigir_abierto(estado, ABIERTO_A_LA_COACH)
        assert exc.value.codigo is Codigo.CHEQUEO_YA_RESUELTO

    def test_un_borrador_tampoco_es_suyo(self) -> None:
        # Todavía lo está capturando la alumna: no hay nada que estimar.
        with pytest.raises(ErrorDeDominio):
            exigir_abierto(EstadoChequeo.BORRADOR, ABIERTO_A_LA_COACH)

    def test_el_error_dice_en_que_estado_esta(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            exigir_abierto(EstadoChequeo.VALIDADO, ABIERTO_A_LA_COACH)
        assert exc.value.detalle["estado"] == "validado"
        assert "pendiente_evaluacion" in exc.value.detalle["abiertos"]


class TestLoQueLaAlumnaTodaviaPuedeTocar:
    @pytest.mark.parametrize("estado", [EstadoChequeo.BORRADOR, EstadoChequeo.RECHAZADO_CALIDAD])
    def test_mientras_es_suyo_puede(self, estado: EstadoChequeo) -> None:
        exigir_abierto(estado, ABIERTO_A_LA_ALUMNA)

    def test_enviado_ya_no_lo_toca(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            exigir_abierto(EstadoChequeo.PENDIENTE_EVALUACION, ABIERTO_A_LA_ALUMNA)
        assert exc.value.codigo is Codigo.CHEQUEO_YA_RESUELTO

    def test_validado_menos_todavia(self) -> None:
        # Borrar una foto aquí se lleva la prueba contra la que se validó.
        with pytest.raises(ErrorDeDominio):
            exigir_abierto(EstadoChequeo.VALIDADO, ABIERTO_A_LA_ALUMNA)


class TestLosDosConjuntosNoSeSolapan:
    def test_ninguna_puede_a_la_vez(self) -> None:
        # Si un estado estuviera en los dos, las dos escribirían sobre el mismo expediente.
        assert not (ABIERTO_A_LA_COACH & ABIERTO_A_LA_ALUMNA)

    def test_ningun_estado_cerrado_esta_abierto_a_nadie(self) -> None:
        for estado in CERRADOS:
            assert estado not in ABIERTO_A_LA_COACH
            assert estado not in ABIERTO_A_LA_ALUMNA

    def test_un_rechazo_le_devuelve_el_chequeo_a_la_alumna(self) -> None:
        # Cerrado para la coach, abierto para ella: es el estado en el que vuelve a capturar.
        assert EstadoChequeo.RECHAZADO_CALIDAD not in ABIERTO_A_LA_COACH
        assert EstadoChequeo.RECHAZADO_CALIDAD in ABIERTO_A_LA_ALUMNA
