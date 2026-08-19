"""Reglas del registro abierto: en qué punto va una solicitud y cuándo se borra sola.

Todo esto se calcula sin base de datos, así que se prueba sin base de datos.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.compartido.errores import ErrorDeDominio
from app.dominio.registro import (
    AVISO_ANTES_DE_BORRAR,
    GRACIA_TRAS_DESCARTAR,
    INTENTOS_DE_CODIGO,
    VIDA_DE_SOLICITUD,
    VIGENCIA_DEL_CODIGO,
    Estado,
    Paso,
    borra_el,
    codigo_utilizable,
    esta_vencida,
    exigir_abierto,
    exigir_codigo_utilizable,
    exigir_decidible,
    paso_actual,
    termino_su_parte,
    toca_recordar,
    vence_el,
)

AHORA = datetime(2026, 8, 19, 10, 0, tzinfo=UTC)


def _paso(estado: Estado = Estado.EN_CURSO, **cambios: bool) -> Paso:
    argumentos = {"cuestionario_completo": False, "tiene_cita": False, "comprobante_subido": False}
    argumentos.update(cambios)
    return paso_actual(estado=estado, **argumentos)  # type: ignore[arg-type]


class TestRecorrido:
    def test_sin_verificar_lo_primero_es_el_correo(self) -> None:
        assert _paso(Estado.SIN_VERIFICAR, cuestionario_completo=True) is Paso.CORREO

    def test_verificada_toca_el_cuestionario(self) -> None:
        assert _paso() is Paso.CUESTIONARIO

    def test_contestado_toca_la_cita(self) -> None:
        assert _paso(cuestionario_completo=True) is Paso.CITA

    def test_reservada_toca_el_comprobante(self) -> None:
        assert _paso(cuestionario_completo=True, tiene_cita=True) is Paso.COMPROBANTE

    def test_con_todo_subido_solo_queda_esperar(self) -> None:
        listo = _paso(cuestionario_completo=True, tiene_cita=True, comprobante_subido=True)
        assert listo is Paso.ESPERA
        assert termino_su_parte(listo)

    def test_el_comprobante_va_despues_de_la_cita(self) -> None:
        """Cobrarle antes de decirle a qué hora la atienden es cobrar por algo sin forma."""
        assert _paso(cuestionario_completo=True, comprobante_subido=True) is Paso.CITA

    @pytest.mark.parametrize("estado", [Estado.ACEPTADA, Estado.DESCARTADA])
    def test_una_solicitud_decidida_ya_no_tiene_pasos(self, estado: Estado) -> None:
        assert _paso(estado) is Paso.LISTA
        assert termino_su_parte(_paso(estado))


class TestCodigo:
    def test_recien_emitido_sirve(self) -> None:
        assert codigo_utilizable(AHORA + VIGENCIA_DEL_CODIGO, 0, AHORA)

    def test_caducado_no_sirve(self) -> None:
        assert not codigo_utilizable(AHORA - timedelta(seconds=1), 0, AHORA)

    def test_quemado_a_intentos_no_sirve(self) -> None:
        vence = AHORA + VIGENCIA_DEL_CODIGO
        assert not codigo_utilizable(vence, INTENTOS_DE_CODIGO, AHORA)
        assert codigo_utilizable(vence, INTENTOS_DE_CODIGO - 1, AHORA)

    def test_exigirlo_falla_con_su_codigo(self) -> None:
        with pytest.raises(ErrorDeDominio):
            exigir_codigo_utilizable(AHORA - timedelta(minutes=1), 0, AHORA)


class TestVencimiento:
    def test_recien_creada_no_se_borra(self) -> None:
        assert not esta_vencida(Estado.SIN_VERIFICAR, AHORA, AHORA)

    def test_a_los_siete_dias_se_borra(self) -> None:
        creada = AHORA - VIDA_DE_SOLICITUD
        assert esta_vencida(Estado.EN_CURSO, creada, AHORA)

    def test_la_que_ya_espera_a_la_coach_no_se_borra(self) -> None:
        # Ella hizo lo suyo: borrarla castigaría a la alumna por la demora de la coach.
        creada = AHORA - VIDA_DE_SOLICITUD * 3
        assert not esta_vencida(Estado.ESPERANDO, creada, AHORA)

    @pytest.mark.parametrize("estado", [Estado.ACEPTADA, Estado.DESCARTADA])
    def test_una_decidida_tampoco(self, estado: Estado) -> None:
        assert not esta_vencida(estado, AHORA - VIDA_DE_SOLICITUD * 5, AHORA)

    def test_el_plazo_se_cuenta_desde_que_se_creo(self) -> None:
        assert vence_el(AHORA) == AHORA + VIDA_DE_SOLICITUD


class TestDescartada:
    def test_sobrevive_una_semana_desde_que_se_decidio(self) -> None:
        # Y no desde que se registró: a quien descartan el sexto día no se le borra todo
        # al día siguiente.
        decidida = AHORA - timedelta(days=1)
        creada = AHORA - VIDA_DE_SOLICITUD * 2
        assert not esta_vencida(Estado.DESCARTADA, creada, AHORA, decidida)

    def test_a_los_siete_dias_de_descartarla_se_borra(self) -> None:
        decidida = AHORA - GRACIA_TRAS_DESCARTAR
        assert esta_vencida(Estado.DESCARTADA, AHORA, AHORA, decidida)

    def test_la_aceptada_no_se_borra_nunca_sola(self) -> None:
        assert borra_el(Estado.ACEPTADA, AHORA, AHORA) is None

    def test_una_descartada_sin_fecha_de_decision_no_se_borra(self) -> None:
        # Defensivo: sin esa fecha no hay plazo que contar, y borrar «por si acaso» sería
        # justo lo contrario de lo que se quiere.
        assert borra_el(Estado.DESCARTADA, AHORA, None) is None


class TestDecidir:
    @pytest.mark.parametrize("estado", [Estado.EN_CURSO, Estado.ESPERANDO])
    def test_se_decide_lo_que_sigue_abierto(self, estado: Estado) -> None:
        exigir_decidible(estado)

    @pytest.mark.parametrize("estado", [Estado.ACEPTADA, Estado.DESCARTADA])
    def test_no_se_decide_dos_veces(self, estado: Estado) -> None:
        with pytest.raises(ErrorDeDominio):
            exigir_decidible(estado)

    def test_sin_verificar_todavia_no_se_decide(self) -> None:
        # No probó ni que el correo es suyo: aceptarla sería crear una alumna con un buzón
        # que quizá no existe.
        with pytest.raises(ErrorDeDominio):
            exigir_decidible(Estado.SIN_VERIFICAR)


class TestRecordatorio:
    def test_avisa_dos_dias_antes(self) -> None:
        creada = AHORA - (VIDA_DE_SOLICITUD - AVISO_ANTES_DE_BORRAR)
        assert toca_recordar(Estado.EN_CURSO, creada, AHORA, ya_enviado=False)

    def test_antes_de_eso_no_molesta(self) -> None:
        creada = AHORA - timedelta(days=1)
        assert not toca_recordar(Estado.EN_CURSO, creada, AHORA, ya_enviado=False)

    def test_no_se_repite(self) -> None:
        creada = AHORA - VIDA_DE_SOLICITUD
        assert not toca_recordar(Estado.EN_CURSO, creada, AHORA, ya_enviado=True)

    def test_a_la_que_espera_no_se_le_recuerda_nada(self) -> None:
        creada = AHORA - VIDA_DE_SOLICITUD
        assert not toca_recordar(Estado.ESPERANDO, creada, AHORA, ya_enviado=False)


class TestInterruptor:
    def test_apagado_no_deja_registrar(self) -> None:
        with pytest.raises(ErrorDeDominio):
            exigir_abierto(False, 1)

    def test_sin_precio_de_inscripcion_tampoco(self) -> None:
        with pytest.raises(ErrorDeDominio):
            exigir_abierto(True, 0)

    def test_con_dos_precios_tampoco(self) -> None:
        # Nadie sabría cuál se le cobra, y cobrarle el que no era es peor que no dejarla.
        with pytest.raises(ErrorDeDominio):
            exigir_abierto(True, 2)

    def test_encendido_y_con_un_precio_pasa(self) -> None:
        exigir_abierto(True, 1)


#: Tablas que apuntan a `alumna` o a `usuario` y que una solicitante **no puede** tener,
#: cada una con el motivo por el que es imposible. Si una deja de serlo, hay que moverla
#: a la lista de borrado, no ampliar esta.
IMPOSIBLES = {
    "chequeo": "el chequeo solo se abre cuando la coach ya la aceptó",
    "ciclo": "el ciclo nace al aceptarla, con el plan que la coach confirme",
    "clave_temporal": "ella eligió su contraseña; nadie le emite claves",
    "foto_de_comida": "el plan todavía no existe, así que no hay fotos que pedirle",
    "mensaje": "la conversación se abre con la relación, y todavía no la hay",
    "movimiento_financiero": "su dinero no entra a finanzas hasta que se valida el pago",
    "pago": "el pago se registra al validarlo la coach",
    "parametros_ciclo": "cuelga del ciclo, que no existe",
    "pesaje": "cuelga del chequeo, que no existe",
    "plan": "lo publica la coach después de aceptarla",
    "anuncio": "apunta al usuario de la coach que lo escribió, no a ella",
    "cobro_coach": "apunta al superadmin que registró el cobro de la coach",
    "alumna": "es la fila que se borra al final",
    "solicitud_registro": "es la propia solicitud",
}


class TestBorradoCompleto:
    """Un registro abandonado se borra entero, y «entero» tiene que seguir siendo cierto
    cuando alguien agregue una tabla nueva que cuelgue de la alumna."""

    def test_toda_tabla_que_cuelga_de_ella_esta_contemplada(self) -> None:
        from app.datos.base import Base
        from app.servicios.registro import POR_ALUMNA, POR_USUARIO

        cubiertas = {t.__tablename__ for t in POR_ALUMNA} | {t.__tablename__ for t in POR_USUARIO}

        sueltas = []
        for tabla in Base.metadata.tables.values():
            apunta = any(
                fk.column.table.name in {"alumna", "usuario"}
                for c in tabla.columns
                for fk in c.foreign_keys
            )
            if not apunta or tabla.name in cubiertas or tabla.name in IMPOSIBLES:
                continue
            sueltas.append(tabla.name)

        assert not sueltas, (
            f"estas tablas cuelgan de la alumna o de su usuario y el borrado no las toca: "
            f"{sorted(sueltas)}. O se agregan a POR_ALUMNA/POR_USUARIO, o se declara aquí "
            "por qué una solicitante no puede tener filas ahí."
        )

    def test_no_sobran_imposibles(self) -> None:
        from app.datos.base import Base

        nombres = set(Base.metadata.tables)
        sobrantes = set(IMPOSIBLES) - nombres
        assert not sobrantes, f"declaradas y sin tabla: {sorted(sobrantes)}"
