"""Maquina de estados del chequeo y sus guardas.

Estas pruebas son la red que sostiene la regla critica del negocio: sin chequeo completo y
del mismo dia no hay envio, y sin validacion de la coach no hay plan nuevo.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.compartido.errores import Codigo, ErrorDeDominio
from app.dominio.chequeo import (
    Angulo,
    EstadoChequeo,
    Instantanea,
    Transicion,
    debe_descartarse,
    guardas_de_envio,
    transicionar,
)
from app.dominio.medidas import TipoMedida

HOY = date(2026, 8, 13)
AYER = date(2026, 8, 12)

TODAS_LAS_MEDIDAS = frozenset(TipoMedida)
TODOS_LOS_ANGULOS = frozenset(Angulo)


def completa(**cambios: object) -> Instantanea:
    """Instantanea que pasa todas las guardas. Cada prueba rompe una sola cosa."""
    base: dict[str, object] = {
        "estado": EstadoChequeo.BORRADOR,
        "fecha": HOY,
        "ayuno_confirmado": True,
        "medidas_capturadas": TODAS_LAS_MEDIDAS,
        "angulos_capturados": TODOS_LOS_ANGULOS,
        "fecha_pesaje": HOY,
        "fechas_de_fotos": frozenset({HOY}),
        "peso_kg": Decimal("65.2"),
        "peso_anterior_kg": Decimal("66.3"),
    }
    base.update(cambios)
    return Instantanea(**base)  # type: ignore[arg-type]


def codigos(inst: Instantanea) -> set[Codigo]:
    return {e.codigo for e in guardas_de_envio(inst).errores}


class TestGuardasDeEnvio:
    def test_un_chequeo_completo_se_puede_enviar(self) -> None:
        assert guardas_de_envio(completa()).puede_enviar

    def test_reporta_todo_lo_que_falta_de_una_vez(self) -> None:
        # Devolver la lista completa evita que la alumna descubra un problema nuevo
        # en cada intento de envio.
        inst = completa(
            medidas_capturadas=frozenset({TipoMedida.CINTURA}),
            angulos_capturados=frozenset(),
            ayuno_confirmado=False,
        )
        assert codigos(inst) >= {
            Codigo.MEDIDAS_INCOMPLETAS,
            Codigo.FOTOS_INCOMPLETAS,
            Codigo.AYUNO_SIN_CONFIRMAR,
        }

    def test_faltando_una_medida_no_se_envia(self) -> None:
        inst = completa(medidas_capturadas=TODAS_LAS_MEDIDAS - {TipoMedida.PANTORRILLA})
        assert Codigo.MEDIDAS_INCOMPLETAS in codigos(inst)

    def test_el_error_nombra_las_medidas_que_faltan(self) -> None:
        inst = completa(medidas_capturadas=TODAS_LAS_MEDIDAS - {TipoMedida.MUSLO})
        resultado = guardas_de_envio(inst)
        assert resultado.campos_faltantes["medidas"] == ["muslo"]

    def test_faltando_un_angulo_no_se_envia(self) -> None:
        inst = completa(angulos_capturados=frozenset({Angulo.FRONTAL, Angulo.PERFIL}))
        assert Codigo.FOTOS_INCOMPLETAS in codigos(inst)
        assert guardas_de_envio(inst).campos_faltantes["fotos"] == ["espalda"]

    def test_peso_de_ayer_con_fotos_de_hoy_no_es_comparable(self) -> None:
        # Regla de sincronia: dia calendario, no ventana movil de 24 h.
        inst = completa(fecha_pesaje=AYER)
        assert Codigo.PESO_Y_FOTOS_EN_DIAS_DISTINTOS in codigos(inst)

    def test_fotos_de_dias_distintos_tampoco(self) -> None:
        inst = completa(fechas_de_fotos=frozenset({HOY, AYER}))
        assert Codigo.PESO_Y_FOTOS_EN_DIAS_DISTINTOS in codigos(inst)

    def test_cuestionario_incompleto_bloquea_el_chequeo(self) -> None:
        assert Codigo.CUESTIONARIO_INCOMPLETO in codigos(completa(cuestionario_completo=False))

    def test_protocolo_fotografico_rechazado_bloquea_el_chequeo(self) -> None:
        assert Codigo.PROTOCOLO_FOTO_RECHAZADO in codigos(completa(protocolo_foto_aceptado=False))


class TestVarianzaEnElEnvio:
    def test_varianza_moderada_exige_confirmacion(self) -> None:
        inst = completa(peso_kg=Decimal("62.0"), peso_anterior_kg=Decimal("66.3"))
        assert Codigo.VARIANZA_DE_PESO_SIN_CONFIRMAR in codigos(inst)

    def test_confirmada_deja_pasar(self) -> None:
        inst = completa(
            peso_kg=Decimal("62.0"),
            peso_anterior_kg=Decimal("66.3"),
            varianza_confirmada_por_alumna=True,
        )
        assert guardas_de_envio(inst).puede_enviar

    def test_mas_del_diez_por_ciento_hereda_alerta_para_la_coach(self) -> None:
        inst = completa(
            peso_kg=Decimal("58.9"),
            peso_anterior_kg=Decimal("65.8"),
            varianza_confirmada_por_alumna=True,
        )
        resultado = guardas_de_envio(inst)
        assert resultado.puede_enviar
        assert resultado.alerta_outlier

    def test_sin_chequeo_previo_no_hay_alerta(self) -> None:
        inst = completa(peso_anterior_kg=None)
        resultado = guardas_de_envio(inst)
        assert resultado.puede_enviar
        assert not resultado.alerta_outlier


class TestTransiciones:
    def test_recorrido_feliz(self) -> None:
        estado = transicionar(EstadoChequeo.BORRADOR, Transicion.ENVIAR)
        assert estado is EstadoChequeo.PENDIENTE_EVALUACION
        assert transicionar(estado, Transicion.VALIDAR) is EstadoChequeo.VALIDADO

    def test_no_se_valida_un_borrador(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            transicionar(EstadoChequeo.BORRADOR, Transicion.VALIDAR)
        assert exc.value.codigo is Codigo.TRANSICION_NO_PERMITIDA

    def test_un_chequeo_validado_no_se_reabre(self) -> None:
        with pytest.raises(ErrorDeDominio):
            transicionar(EstadoChequeo.VALIDADO, Transicion.RECHAZAR, motivo="x")

    def test_rechazar_exige_motivo(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            transicionar(EstadoChequeo.PENDIENTE_EVALUACION, Transicion.RECHAZAR, motivo="   ")
        assert exc.value.codigo is Codigo.MOTIVO_DE_RECHAZO_REQUERIDO

    def test_rechazado_vuelve_a_borrador_para_recapturar(self) -> None:
        assert (
            transicionar(EstadoChequeo.RECHAZADO_CALIDAD, Transicion.RECAPTURAR)
            is EstadoChequeo.BORRADOR
        )

    def test_sobrescribir_una_alerta_de_outlier_exige_justificacion(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            transicionar(
                EstadoChequeo.PENDIENTE_EVALUACION,
                Transicion.VALIDAR,
                alerta_outlier_abierta=True,
            )
        assert exc.value.codigo is Codigo.JUSTIFICACION_DE_OUTLIER_REQUERIDA

    def test_con_justificacion_la_coach_puede_validar_el_outlier(self) -> None:
        assert (
            transicionar(
                EstadoChequeo.PENDIENTE_EVALUACION,
                Transicion.VALIDAR,
                alerta_outlier_abierta=True,
                justificacion_outlier="Vino de una cirugia; las fotos confirman el cambio.",
            )
            is EstadoChequeo.VALIDADO
        )


class TestExpiracionDelBorrador:
    def test_un_borrador_incompleto_de_ayer_se_descarta(self) -> None:
        inst = completa(fecha=AYER, angulos_capturados=frozenset(), fechas_de_fotos=frozenset())
        assert debe_descartarse(inst, HOY)

    def test_un_borrador_completo_de_ayer_no_se_descarta(self) -> None:
        # Ya cumplia todas las guardas; lo que falta es que alguien pulse enviar.
        inst = completa(fecha=AYER, fecha_pesaje=AYER, fechas_de_fotos=frozenset({AYER}))
        assert not debe_descartarse(inst, HOY)

    def test_un_borrador_de_hoy_todavia_tiene_su_dia(self) -> None:
        inst = completa(angulos_capturados=frozenset(), fechas_de_fotos=frozenset())
        assert not debe_descartarse(inst, HOY)

    def test_lo_ya_enviado_no_se_descarta(self) -> None:
        inst = completa(estado=EstadoChequeo.PENDIENTE_EVALUACION, fecha=AYER)
        assert not debe_descartarse(inst, HOY)
