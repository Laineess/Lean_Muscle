"""Qué horas se le ofrecen a una alumna para reservar.

Es un cálculo puro: horario de la coach, lo que ya tiene ocupado y dos plazos.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.compartido.errores import ErrorDeDominio
from app.dominio.agenda import EstadoCita, Franja
from app.dominio.huecos import Bloque, Reglas, libres, reservable, revisar_horario, ventana

CDMX = "America/Mexico_City"

#: Lunes 17 de agosto de 2026, 9:00 en CDMX.
LUNES = datetime(2026, 8, 17, 9, 0, tzinfo=ZoneInfo(CDMX))

#: Un horario normal: mañana y tarde de lunes a viernes, con hueco para comer.
JORNADA = [Bloque(dia=d, desde=time(9), hasta=time(14)) for d in range(5)] + [
    Bloque(dia=d, desde=time(16), hasta=time(19)) for d in range(5)
]


def _ahora(dias_antes: int = 2) -> datetime:
    return LUNES - timedelta(days=dias_antes)


class TestHorario:
    def test_un_tramo_al_reves_no_se_acepta(self) -> None:
        with pytest.raises(ErrorDeDominio):
            Bloque(dia=0, desde=time(14), hasta=time(9))

    def test_un_dia_que_no_existe_tampoco(self) -> None:
        with pytest.raises(ErrorDeDominio):
            Bloque(dia=7, desde=time(9), hasta=time(10))

    def test_sin_horario_no_hay_nada_que_ofrecer(self) -> None:
        assert libres([], [], Reglas(), CDMX, _ahora()) == []


class TestTroceado:
    def test_las_consultas_empiezan_cada_duracion_mas_margen(self) -> None:
        reglas = Reglas(duracion_min=60, margen_min=15)
        huecos = libres([Bloque(0, time(9), time(14))], [], reglas, CDMX, _ahora())
        primeros = [h.inicia_en.astimezone(ZoneInfo(CDMX)).strftime("%H:%M") for h in huecos[:4]]
        assert primeros == ["09:00", "10:15", "11:30", "12:45"]

    def test_no_se_ofrece_una_consulta_que_no_cabe(self) -> None:
        """A las 13:45 ya no caben 60 minutos antes de las 14."""
        reglas = Reglas(duracion_min=60, margen_min=15)
        huecos = libres([Bloque(0, time(9), time(14))], [], reglas, CDMX, _ahora())
        ultimo = huecos[-1].termina_en.astimezone(ZoneInfo(CDMX))
        assert ultimo.hour <= 14

    def test_sin_margen_las_consultas_van_pegadas(self) -> None:
        # Una sola semana de horizonte deja un solo lunes que contar.
        reglas = Reglas(duracion_min=60, margen_min=0, horizonte_semanas=1)
        huecos = libres([Bloque(0, time(9), time(12))], [], reglas, CDMX, _ahora())
        assert len(huecos) == 3

    def test_la_comida_no_se_ofrece(self) -> None:
        horas = {
            h.inicia_en.astimezone(ZoneInfo(CDMX)).hour
            for h in libres(JORNADA, [], Reglas(), CDMX, _ahora())
        }
        assert 14 not in horas and 15 not in horas


class TestLoOcupado:
    def test_una_cita_agendada_tapa_su_hueco(self) -> None:
        reglas = Reglas(duracion_min=60, margen_min=15)
        tomada = Franja(id=1, inicia_en=LUNES, termina_en=LUNES + timedelta(hours=1))
        huecos = libres([Bloque(0, time(9), time(14))], [tomada], reglas, CDMX, _ahora())
        assert all(h.inicia_en != tomada.inicia_en for h in huecos)

    def test_un_bloque_de_trabajo_estorba_igual(self) -> None:
        """El tiempo de la coach es uno solo: da igual si es consulta o trabajo suyo."""
        reglas = Reglas(duracion_min=60, margen_min=15, horizonte_semanas=1)
        bloqueo = Franja(id=2, inicia_en=LUNES, termina_en=LUNES + timedelta(hours=5))
        assert libres([Bloque(0, time(9), time(14))], [bloqueo], reglas, CDMX, _ahora()) == []

    def test_una_cita_cancelada_libera_su_hueco(self) -> None:
        reglas = Reglas(duracion_min=60, margen_min=15)
        cancelada = Franja(
            id=3,
            inicia_en=LUNES,
            termina_en=LUNES + timedelta(hours=1),
            estado=EstadoCita.CANCELADA,
        )
        huecos = libres([Bloque(0, time(9), time(14))], [cancelada], reglas, CDMX, _ahora())
        assert any(h.inicia_en == cancelada.inicia_en for h in huecos)


class TestPlazos:
    def test_no_se_puede_reservar_sobre_la_hora(self) -> None:
        reglas = Reglas(antelacion_horas=24)
        # Faltando una hora para el lunes, el lunes ya no se ofrece.
        huecos = libres(JORNADA, [], reglas, CDMX, LUNES - timedelta(hours=1))
        assert all(h.inicia_en.astimezone(ZoneInfo(CDMX)).date() > LUNES.date() for h in huecos)

    def test_no_se_ofrece_mas_alla_del_horizonte(self) -> None:
        reglas = Reglas(horizonte_semanas=2)
        _, hasta = ventana(reglas, _ahora())
        assert all(h.termina_en <= hasta for h in libres(JORNADA, [], reglas, CDMX, _ahora()))

    def test_la_ventana_arranca_tras_la_antelacion(self) -> None:
        ahora = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
        desde, _ = ventana(Reglas(antelacion_horas=24), ahora)
        assert desde == ahora + timedelta(hours=24)


class TestReservar:
    def test_un_hueco_de_la_lista_se_puede_tomar(self) -> None:
        huecos = libres(JORNADA, [], Reglas(), CDMX, _ahora())
        tomado = reservable(huecos[0].inicia_en, JORNADA, [], Reglas(), CDMX, _ahora())
        assert tomado.inicia_en == huecos[0].inicia_en

    def test_una_hora_fuera_del_horario_se_rechaza(self) -> None:
        medianoche = LUNES.replace(hour=3)
        with pytest.raises(ErrorDeDominio):
            reservable(medianoche, JORNADA, [], Reglas(), CDMX, _ahora())

    def test_el_hueco_que_alguien_acaba_de_tomar_se_rechaza(self) -> None:
        """Entre ver la pantalla y tocar el botón, otra alumna pudo ganarlo."""
        huecos = libres(JORNADA, [], Reglas(), CDMX, _ahora())
        elegido = huecos[0]
        ya_tomado = [Franja(id=9, inicia_en=elegido.inicia_en, termina_en=elegido.termina_en)]
        with pytest.raises(ErrorDeDominio):
            reservable(elegido.inicia_en, JORNADA, ya_tomado, Reglas(), CDMX, _ahora())


class TestZonaHoraria:
    def test_la_jornada_es_local_aunque_todo_se_guarde_en_utc(self) -> None:
        """Las 9 de la coach son las 9 de la coach, en verano y en invierno."""
        enero = datetime(2026, 1, 12, 9, 0, tzinfo=ZoneInfo(CDMX))
        for referencia in (enero, LUNES):
            huecos = libres(
                [Bloque(referencia.weekday(), time(9), time(11))],
                [],
                Reglas(duracion_min=60, margen_min=0),
                CDMX,
                referencia - timedelta(days=2),
            )
            assert huecos[0].inicia_en.astimezone(ZoneInfo(CDMX)).hour == 9

    def test_una_alumna_en_otra_zona_ve_el_mismo_instante(self) -> None:
        hueco = libres(JORNADA, [], Reglas(), CDMX, _ahora())[0]
        en_tijuana = hueco.inicia_en.astimezone(ZoneInfo("America/Tijuana"))
        en_cdmx = hueco.inicia_en.astimezone(ZoneInfo(CDMX))
        assert en_tijuana.hour != en_cdmx.hour
        assert en_tijuana.utcoffset() != en_cdmx.utcoffset()


class TestReglas:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"duracion_min": 5},
            {"duracion_min": 500},
            {"margen_min": -1},
            {"margen_min": 300},
            {"horizonte_semanas": 0},
            {"horizonte_semanas": 99},
        ],
    )
    def test_lo_absurdo_no_se_configura(self, kwargs: dict) -> None:
        with pytest.raises(ErrorDeDominio):
            Reglas(**kwargs)


class TestTramosEncimados:
    def test_dos_tramos_que_se_pisan_no_pasan(self) -> None:
        con_pisada = [
            Bloque(dia=0, desde=time(9), hasta=time(14)),
            Bloque(dia=0, desde=time(13), hasta=time(18)),
        ]
        with pytest.raises(ErrorDeDominio):
            revisar_horario(con_pisada)

    def test_pegados_no_es_encimados(self) -> None:
        # Terminar a las 14:00 y arrancar a las 14:00 es una jornada partida, no un error.
        revisar_horario(
            [
                Bloque(dia=0, desde=time(9), hasta=time(14)),
                Bloque(dia=0, desde=time(14), hasta=time(18)),
            ]
        )

    def test_la_misma_hora_en_dias_distintos_convive(self) -> None:
        revisar_horario(
            [
                Bloque(dia=0, desde=time(9), hasta=time(14)),
                Bloque(dia=1, desde=time(9), hasta=time(14)),
            ]
        )

    def test_uno_dentro_de_otro_tampoco_pasa(self) -> None:
        with pytest.raises(ErrorDeDominio):
            revisar_horario(
                [
                    Bloque(dia=3, desde=time(8), hasta=time(20)),
                    Bloque(dia=3, desde=time(10), hasta=time(12)),
                ]
            )

    def test_sin_tramos_no_se_queja(self) -> None:
        revisar_horario([])
