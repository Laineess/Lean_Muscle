"""Qué se avisa, por qué canal y cuándo.

Dos cosas se prueban aquí más que ninguna: que un aviso no se repita —un trabajo programado
que corre dos veces no debe mandar dos correos— y que el correo se reserve para lo que de
verdad no puede perderse.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from app.dominio.avisos import (
    CANALES,
    Aviso,
    Canal,
    canales_de,
    lleva_adjunto,
    toca_avisar_inactividad,
    toca_avisar_purga,
    toca_avisar_vencido,
    toca_recordar_cita,
    toca_recordar_pago,
)
from app.servicios.avisos import llave_de_canal

AHORA = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)
HOY = date(2026, 8, 13)


class TestCanales:
    def test_todos_los_avisos_tienen_canal(self) -> None:
        # Un aviso sin canal no se envía por ningún lado y nadie se entera.
        faltantes = [a for a in Aviso if a not in CANALES]
        assert not faltantes, f"sin canal: {faltantes}"

    def test_ningun_aviso_se_queda_sin_ruta(self) -> None:
        vacios = [a for a in Aviso if not canales_de(a)]
        assert not vacios, f"con canal vacío: {vacios}"

    @pytest.mark.parametrize(
        "aviso",
        [Aviso.BIENVENIDA, Aviso.CLAVE_TEMPORAL, Aviso.CONTRASENA_CAMBIADA],
        ids=lambda a: a.value,
    )
    def test_lo_de_acceso_va_por_correo(self, aviso: Aviso) -> None:
        # Si no llega, la alumna se queda fuera y no hay push que la rescate.
        assert Canal.CORREO in canales_de(aviso)

    @pytest.mark.parametrize(
        "aviso",
        [Aviso.PAGO_VALIDADO, Aviso.PAGO_RECHAZADO, Aviso.PAGO_VENCIDO],
        ids=lambda a: a.value,
    )
    def test_lo_de_dinero_va_por_correo(self, aviso: Aviso) -> None:
        assert Canal.CORREO in canales_de(aviso)

    @pytest.mark.parametrize(
        "aviso",
        [
            Aviso.RECORDATORIO_CHEQUEO,
            Aviso.CHEQUEO_RECIBIDO,
            Aviso.CHEQUEO_VALIDADO,
            Aviso.PLAN_PUBLICADO,
            Aviso.INACTIVIDAD,
        ],
        ids=lambda a: a.value,
    )
    def test_el_dia_a_dia_del_metodo_no_llena_el_correo(self, aviso: Aviso) -> None:
        # Mandar por correo cada movimiento sería la forma más rápida de que aprenda a
        # ignorarnos, y entonces el correo que sí importa también se pierde.
        assert canales_de(aviso) == frozenset({Canal.PUSH})

    def test_solo_el_pago_validado_lleva_adjunto(self) -> None:
        con_adjunto = [a for a in Aviso if lleva_adjunto(a)]
        assert con_adjunto == [Aviso.PAGO_VALIDADO]


class TestRecordatorioDeCita:
    def test_se_avisa_el_dia_antes(self) -> None:
        p = toca_recordar_cita(AHORA + timedelta(hours=20), AHORA, False, "c1")
        assert p is not None and p.aviso is Aviso.CITA_RECORDATORIO

    def test_no_se_avisa_con_tres_dias_de_anticipacion(self) -> None:
        assert toca_recordar_cita(AHORA + timedelta(days=3), AHORA, False, "c1") is None

    def test_no_se_avisa_de_una_cita_que_ya_paso(self) -> None:
        # Sin piso en la ventana, cada corrida del trabajo recordaría citas viejas.
        assert toca_recordar_cita(AHORA - timedelta(hours=2), AHORA, False, "c1") is None

    def test_no_se_avisa_dos_veces(self) -> None:
        assert toca_recordar_cita(AHORA + timedelta(hours=20), AHORA, True, "c1") is None

    def test_la_llave_identifica_la_cita(self) -> None:
        p = toca_recordar_cita(AHORA + timedelta(hours=20), AHORA, False, "c1")
        assert p is not None and p.llave == "cita:c1:recordatorio"


class TestRecordatorioDePago:
    def test_se_avisa_tres_dias_antes_de_que_termine_el_ciclo(self) -> None:
        p = toca_recordar_pago(HOY + timedelta(days=2), HOY, pagado=False, ciclo_id="x")
        assert p is not None and p.aviso is Aviso.PAGO_PROXIMO

    def test_no_se_le_cobra_a_quien_ya_pago(self) -> None:
        # Es la forma más rápida de que deje de leer los correos.
        assert toca_recordar_pago(HOY + timedelta(days=2), HOY, pagado=True, ciclo_id="x") is None

    def test_no_se_avisa_con_una_semana_de_anticipacion(self) -> None:
        assert toca_recordar_pago(HOY + timedelta(days=7), HOY, pagado=False, ciclo_id="x") is None

    def test_el_ciclo_vencido_dispara_otro_aviso(self) -> None:
        p = toca_avisar_vencido(HOY - timedelta(days=1), HOY, pagado=False, ciclo_id="x")
        assert p is not None and p.aviso is Aviso.PAGO_VENCIDO

    def test_un_ciclo_vigente_no_esta_vencido(self) -> None:
        assert toca_avisar_vencido(HOY + timedelta(days=5), HOY, pagado=False, ciclo_id="x") is None

    def test_un_ciclo_pagado_nunca_se_marca_vencido(self) -> None:
        assert toca_avisar_vencido(HOY - timedelta(days=5), HOY, pagado=True, ciclo_id="x") is None


class TestAvisoDePurga:
    def test_se_avisa_quince_dias_antes_de_borrar_las_fotos(self) -> None:
        # Lo exige el Aviso de Privacidad §8: lo que se lleva es suyo.
        tomada = HOY - timedelta(days=110)  # con 4 meses, se borra en 10 días
        p = toca_avisar_purga(tomada, HOY, retencion_meses=4, foto_id="f1")
        assert p is not None and p.aviso is Aviso.PURGA_PROXIMA

    def test_una_foto_reciente_no_dispara_aviso(self) -> None:
        assert toca_avisar_purga(HOY - timedelta(days=10), HOY, 4, "f1") is None

    def test_una_foto_que_ya_paso_el_plazo_no_reavisa(self) -> None:
        assert toca_avisar_purga(HOY - timedelta(days=200), HOY, 4, "f1") is None


class TestInactividad:
    def test_tres_dias_sin_entrar_disparan_el_aviso(self) -> None:
        p = toca_avisar_inactividad(HOY - timedelta(days=3), HOY, False, "a1")
        assert p is not None and p.aviso is Aviso.INACTIVIDAD

    def test_dos_dias_todavia_no(self) -> None:
        assert toca_avisar_inactividad(HOY - timedelta(days=2), HOY, False, "a1") is None

    def test_quien_nunca_entro_cuenta_como_inactiva(self) -> None:
        assert toca_avisar_inactividad(None, HOY, False, "a1") is not None

    def test_no_se_avisa_dos_veces_el_mismo_dia(self) -> None:
        assert toca_avisar_inactividad(HOY - timedelta(days=5), HOY, True, "a1") is None

    def test_la_llave_lleva_la_fecha_para_poder_reavisar_despues(self) -> None:
        # Si vuelve a inactivarse el mes que entra, la llave es distinta y se avisa otra vez.
        p = toca_avisar_inactividad(HOY - timedelta(days=5), HOY, False, "a1")
        assert p is not None and p.llave.endswith(HOY.isoformat())


class TestLlaveDeCanal:
    """`aviso_enviado` tiene UNIQUE (coach_id, llave).

    Un aviso que sale por correo y por push necesita dos llaves distintas o la segunda fila
    revienta la transacción entera. Era el caso de `PAGO_VENCIDO` y `PURGA_PROXIMA`, y hacía
    fallar la corrida diaria completa de recordatorios.
    """

    def test_cada_canal_tiene_su_propia_llave(self) -> None:
        llave = "ciclo:c1:vencido"
        correo = llave_de_canal(llave, Canal.CORREO)
        push = llave_de_canal(llave, Canal.PUSH)
        assert correo != push
        assert correo.startswith(llave) and push.startswith(llave)

    def test_los_avisos_de_dos_canales_no_colisionan(self) -> None:
        for aviso, canales in CANALES.items():
            llaves = {llave_de_canal(f"x:{aviso.value}", c) for c in canales}
            assert len(llaves) == len(canales), f"{aviso} colisiona consigo mismo"

    def test_una_llave_larguisima_sigue_cabiendo_en_la_columna(self) -> None:
        # VARCHAR(160): si no cupiera, MySQL truncaría en silencio y dos disparos distintos
        # acabarían con la misma llave, que es peor que fallar.
        assert len(llave_de_canal("a" * 400, Canal.PUSH)) <= 160
