"""Los plazos de las fotos de comida.

Dos reglas: cada cuánto le toca a la alumna, y cuánto vive lo que manda. La segunda no la
elige nadie, y por eso es la que más pruebas tiene.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from app.dominio.fotos_de_comida import (
    DIAS,
    ROTULO,
    VIGENCIA,
    Frecuencia,
    estado,
    expira_en,
    periodo,
    vencida,
)


def _momento(dia: int, hora: int = 9) -> datetime:
    return datetime(2026, 8, dia, hora, tzinfo=UTC)


class TestVigencia:
    def test_son_treinta_y_seis_horas(self) -> None:
        """Fijo y corto a propósito: es lo que hace razonable pedir la foto."""
        assert VIGENCIA == timedelta(hours=36)

    def test_recien_subida_esta_viva(self) -> None:
        subida = _momento(10)
        assert not vencida(subida, subida + timedelta(hours=1))

    def test_a_las_treinta_y_cinco_horas_sigue_viva(self) -> None:
        subida = _momento(10)
        assert not vencida(subida, subida + timedelta(hours=35, minutes=59))

    def test_al_cumplirse_el_plazo_ya_no(self) -> None:
        """En el límite exacto se considera vencida: la promesa es «a las 36 horas», no
        «pasadas las 36 horas»."""
        subida = _momento(10)
        assert vencida(subida, subida + VIGENCIA)

    def test_expira_donde_dice(self) -> None:
        subida = _momento(10, 20)
        assert expira_en(subida) == datetime(2026, 8, 12, 8, tzinfo=UTC)


class TestFrecuencia:
    def test_ninguna_no_tiene_periodo(self) -> None:
        """Es el valor de fábrica: si la coach no pide fotos, no se pide nada."""
        assert Frecuencia.NINGUNA not in DIAS

    def test_todas_tienen_rotulo(self) -> None:
        for f in Frecuencia:
            assert ROTULO[f]

    @pytest.mark.parametrize(
        ("frecuencia", "dias"),
        [
            (Frecuencia.DIARIA, 1),
            (Frecuencia.SEMANAL, 7),
            (Frecuencia.QUINCENAL, 15),
            (Frecuencia.MENSUAL, 30),
        ],
    )
    def test_los_periodos_son_los_que_eligio(self, frecuencia: Frecuencia, dias: int) -> None:
        assert DIAS[frecuencia] == dias


class TestPeriodo:
    def test_se_cuenta_desde_que_se_publico_el_plan(self) -> None:
        """No desde el primero de mes: a quien dieron de alta un día 20 no le toca su
        primer «te toca» al día siguiente."""
        desde, hasta = periodo(Frecuencia.SEMANAL, date(2026, 8, 20), date(2026, 8, 22))
        assert desde == date(2026, 8, 20)
        assert hasta == date(2026, 8, 26)

    def test_avanza_al_periodo_siguiente(self) -> None:
        desde, hasta = periodo(Frecuencia.SEMANAL, date(2026, 8, 20), date(2026, 8, 28))
        assert desde == date(2026, 8, 27)
        assert hasta == date(2026, 9, 2)

    def test_antes_de_la_referencia_no_se_va_hacia_atras(self) -> None:
        """Puede pasar si se corrige la fecha de publicación: el periodo no debe salir
        negativo."""
        desde, _ = periodo(Frecuencia.SEMANAL, date(2026, 8, 20), date(2026, 8, 1))
        assert desde == date(2026, 8, 20)


class TestEstado:
    def test_sin_frecuencia_no_hay_nada_pendiente(self) -> None:
        assert estado(Frecuencia.NINGUNA, date(2026, 8, 1), date(2026, 8, 10), []) is None

    def test_sin_fotos_en_el_periodo_queda_pendiente(self) -> None:
        p = estado(Frecuencia.SEMANAL, date(2026, 8, 3), date(2026, 8, 5), [])
        assert p is not None and not p.cumplido

    def test_una_foto_dentro_del_periodo_lo_cumple(self) -> None:
        p = estado(Frecuencia.SEMANAL, date(2026, 8, 3), date(2026, 8, 5), [date(2026, 8, 4)])
        assert p is not None and p.cumplido

    def test_una_foto_del_periodo_anterior_no_cuenta(self) -> None:
        """Mandar una la semana pasada no exime de la de esta."""
        p = estado(Frecuencia.SEMANAL, date(2026, 8, 3), date(2026, 8, 12), [date(2026, 8, 4)])
        assert p is not None and not p.cumplido
