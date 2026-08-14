"""Reglas de la agenda.

El error caro de esta pantalla es agendar dos alumnas a la misma hora, así que la mayoría
de estas pruebas son sobre solape.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.compartido.errores import Codigo, ErrorDeDominio
from app.dominio.agenda import (
    DURACION_MAXIMA,
    DURACION_MINIMA,
    EstadoCita,
    Franja,
    agendar,
    buscar_choque,
    exigir_hueco_libre,
    toca_recordatorio,
    transicionar,
)

AHORA = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)


def franja(
    inicio_h: float,
    fin_h: float,
    *,
    id: int | None = None,
    estado: EstadoCita = EstadoCita.AGENDADA,
) -> Franja:
    base = datetime(2026, 8, 20, 0, 0, tzinfo=UTC)
    return Franja(
        id=id,
        inicia_en=base + timedelta(hours=inicio_h),
        termina_en=base + timedelta(hours=fin_h),
        estado=estado,
    )


class TestSolape:
    def test_dos_citas_a_la_misma_hora_chocan(self) -> None:
        assert franja(10, 11).choca_con(franja(10, 11))

    def test_una_cita_que_empieza_dentro_de_otra_choca(self) -> None:
        assert franja(10, 12).choca_con(franja(11, 13))

    def test_una_cita_contenida_en_otra_choca(self) -> None:
        assert franja(10, 14).choca_con(franja(11, 12))

    def test_citas_seguidas_no_chocan(self) -> None:
        # Intervalo medio abierto: sin esto sería imposible agendar consultas seguidas.
        assert not franja(10, 11).choca_con(franja(11, 12))

    def test_citas_separadas_no_chocan(self) -> None:
        assert not franja(9, 10).choca_con(franja(14, 15))

    def test_una_cita_cancelada_libera_su_hueco(self) -> None:
        cancelada = franja(10, 11, estado=EstadoCita.CANCELADA)
        assert not franja(10, 11).choca_con(cancelada)

    def test_un_bloqueo_de_trabajo_tambien_ocupa(self) -> None:
        # El tiempo de la coach es uno solo: da igual si el hueco es consulta o bloqueo.
        agenda = [franja(16, 18, id=1)]
        with pytest.raises(ErrorDeDominio) as exc:
            exigir_hueco_libre(franja(17, 17.5), agenda)
        assert exc.value.codigo is Codigo.CITA_SE_SOLAPA


class TestBuscarChoque:
    def test_encuentra_la_cita_que_estorba(self) -> None:
        agenda = [franja(9, 10, id=1), franja(11, 12, id=2), franja(15, 16, id=3)]
        choque = buscar_choque(franja(11.5, 13), agenda)
        assert choque is not None and choque.id == 2

    def test_una_agenda_libre_no_devuelve_nada(self) -> None:
        assert buscar_choque(franja(13, 14), [franja(9, 10, id=1)]) is None

    def test_editar_una_cita_no_choca_consigo_misma(self) -> None:
        agenda = [franja(9, 10, id=7)]
        # Se mueve media hora, sigue solapando su horario anterior: debe permitirse.
        assert buscar_choque(franja(9.5, 10.5, id=7), agenda) is None


class TestValidacion:
    def test_el_fin_debe_ser_posterior_al_inicio(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            agendar(franja(12, 11), [], ahora=AHORA)
        assert exc.value.codigo is Codigo.CITA_RANGO_INVALIDO

    def test_una_cita_de_cero_minutos_se_rechaza(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            agendar(franja(10, 10), [], ahora=AHORA)
        assert exc.value.codigo is Codigo.CITA_RANGO_INVALIDO

    def test_una_cita_demasiado_corta_se_rechaza(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            agendar(franja(10, 10 + 5 / 60), [], ahora=AHORA)
        assert exc.value.codigo is Codigo.CITA_DURACION_INVALIDA

    def test_una_cita_de_dias_se_rechaza(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            agendar(franja(0, 20), [], ahora=AHORA)
        assert exc.value.codigo is Codigo.CITA_DURACION_INVALIDA

    def test_los_limites_de_duracion_se_aceptan(self) -> None:
        minima = DURACION_MINIMA.total_seconds() / 3600
        maxima = DURACION_MAXIMA.total_seconds() / 3600
        agendar(franja(10, 10 + minima), [], ahora=AHORA)
        agendar(franja(9, 9 + maxima), [], ahora=AHORA)

    def test_no_se_agenda_en_el_pasado(self) -> None:
        pasada = Franja(
            None, datetime(2026, 8, 1, 10, tzinfo=UTC), datetime(2026, 8, 1, 11, tzinfo=UTC)
        )
        with pytest.raises(ErrorDeDominio) as exc:
            agendar(pasada, [], ahora=AHORA)
        assert exc.value.codigo is Codigo.CITA_EN_EL_PASADO

    def test_registrar_una_consulta_ya_ocurrida_si_se_permite(self) -> None:
        pasada = Franja(
            None, datetime(2026, 8, 1, 10, tzinfo=UTC), datetime(2026, 8, 1, 11, tzinfo=UTC)
        )
        agendar(pasada, [], ahora=AHORA, permitir_pasado=True)


class TestEstados:
    def test_recorrido_normal(self) -> None:
        estado = transicionar(EstadoCita.AGENDADA, EstadoCita.CONFIRMADA)
        assert transicionar(estado, EstadoCita.REALIZADA) is EstadoCita.REALIZADA

    def test_cancelar_exige_motivo(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            transicionar(EstadoCita.AGENDADA, EstadoCita.CANCELADA, motivo="  ")
        assert exc.value.codigo is Codigo.MOTIVO_DE_CANCELACION_REQUERIDO

    def test_con_motivo_se_cancela(self) -> None:
        assert (
            transicionar(EstadoCita.AGENDADA, EstadoCita.CANCELADA, motivo="La alumna se enfermó")
            is EstadoCita.CANCELADA
        )

    def test_una_cita_cancelada_no_se_revive(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            transicionar(EstadoCita.CANCELADA, EstadoCita.AGENDADA)
        assert exc.value.codigo is Codigo.TRANSICION_NO_PERMITIDA

    def test_una_cita_realizada_no_se_cancela(self) -> None:
        with pytest.raises(ErrorDeDominio):
            transicionar(EstadoCita.REALIZADA, EstadoCita.CANCELADA, motivo="x")


class TestRecordatorio:
    def test_se_avisa_cuando_falta_menos_de_un_dia(self) -> None:
        cita = Franja(None, AHORA + timedelta(hours=20), AHORA + timedelta(hours=21))
        assert toca_recordatorio(cita, AHORA, ya_enviado=False)

    def test_no_se_avisa_con_dos_dias_de_anticipacion(self) -> None:
        cita = Franja(None, AHORA + timedelta(days=2), AHORA + timedelta(days=2, hours=1))
        assert not toca_recordatorio(cita, AHORA, ya_enviado=False)

    def test_no_se_avisa_dos_veces(self) -> None:
        cita = Franja(None, AHORA + timedelta(hours=20), AHORA + timedelta(hours=21))
        assert not toca_recordatorio(cita, AHORA, ya_enviado=True)

    def test_una_cita_cancelada_no_genera_recordatorio(self) -> None:
        cita = Franja(
            None, AHORA + timedelta(hours=20), AHORA + timedelta(hours=21), EstadoCita.CANCELADA
        )
        assert not toca_recordatorio(cita, AHORA, ya_enviado=False)
