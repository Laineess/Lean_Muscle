"""Rangos antropometricos y varianza de peso. Sin base de datos: dominio puro."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.compartido.errores import Codigo, ErrorDeDominio
from app.dominio.medidas import (
    MAX_PESAJES_POR_CICLO,
    MEDIDAS_REQUERIDAS,
    NivelVarianza,
    TipoMedida,
    evaluar_varianza,
    faltantes,
    promedio_de_pesajes,
    validar_estatura,
    validar_medida,
    validar_peso,
)


def d(valor: str) -> Decimal:
    return Decimal(valor)


class TestPeso:
    def test_acepta_los_extremos_del_rango(self) -> None:
        assert validar_peso(d("30.0")) == d("30.0")
        assert validar_peso(d("250.0")) == d("250.0")

    @pytest.mark.parametrize("valor", ["0", "29.9", "250.1", "-70.0"])
    def test_rechaza_fuera_de_rango(self, valor: str) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            validar_peso(d(valor))
        assert exc.value.codigo is Codigo.PESO_FUERA_DE_RANGO

    def test_el_mensaje_lleva_el_rango_para_que_la_ui_no_lo_repita(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            validar_peso(d("12.0"))
        assert exc.value.detalle["minimo"] == "30.0"
        assert exc.value.detalle["maximo"] == "250.0"

    def test_redondea_a_un_decimal(self) -> None:
        assert validar_peso(d("68.44")) == d("68.4")
        assert validar_peso(d("68.45")) == d("68.5")


class TestMedidas:
    def test_cero_tiene_su_propio_codigo(self) -> None:
        # El diccionario de datos prohibe ceros explicitamente, y la alumna necesita saber
        # que el problema es "esta vacio", no "esta fuera de rango".
        with pytest.raises(ErrorDeDominio) as exc:
            validar_medida(TipoMedida.CINTURA, d("0"))
        assert exc.value.codigo is Codigo.MEDIDA_EN_CERO

    def test_cada_tipo_usa_su_propio_rango(self) -> None:
        # 25 cm es una cintura imposible pero un brazo normal.
        with pytest.raises(ErrorDeDominio):
            validar_medida(TipoMedida.CINTURA, d("25.0"))
        assert validar_medida(TipoMedida.BRAZO, d("25.0")) == d("25.0")

    def test_son_ocho_perimetros(self) -> None:
        # Ocho aqui + la estatura del perfil = las "9 medidas" del documento.
        assert len(MEDIDAS_REQUERIDAS) == 8

    def test_faltantes_lista_lo_que_falta(self) -> None:
        capturadas = {TipoMedida.CINTURA, TipoMedida.ABDOMEN}
        assert faltantes(capturadas) == MEDIDAS_REQUERIDAS - capturadas

    def test_estatura_se_guarda_como_entero(self) -> None:
        assert validar_estatura(d("165.4")) == 165
        with pytest.raises(ErrorDeDominio) as exc:
            validar_estatura(d("99"))
        assert exc.value.codigo is Codigo.ESTATURA_FUERA_DE_RANGO


class TestVarianza:
    def test_sin_referencia_previa_no_hay_varianza(self) -> None:
        v = evaluar_varianza(d("68.0"), None)
        assert v.nivel is NivelVarianza.NORMAL

    def test_dentro_del_tres_por_ciento_es_normal(self) -> None:
        assert evaluar_varianza(d("68.0"), d("70.0")).nivel is NivelVarianza.NORMAL

    def test_pasando_el_tres_por_ciento_confirma_la_alumna(self) -> None:
        assert evaluar_varianza(d("67.0"), d("70.0")).nivel is NivelVarianza.CONFIRMA_ALUMNA

    def test_pasando_el_diez_por_ciento_se_alerta_a_la_coach(self) -> None:
        assert evaluar_varianza(d("62.0"), d("70.0")).nivel is NivelVarianza.ALERTA_COACH

    def test_el_umbral_es_estricto_no_inclusivo(self) -> None:
        # Exactamente 3 % todavia es normal; el documento habla de quedar *fuera* del rango.
        assert evaluar_varianza(d("97.0"), d("100.0")).nivel is NivelVarianza.NORMAL
        assert evaluar_varianza(d("96.9"), d("100.0")).nivel is NivelVarianza.CONFIRMA_ALUMNA

    def test_subir_de_peso_dispara_igual_que_bajar(self) -> None:
        assert evaluar_varianza(d("78.0"), d("70.0")).nivel is NivelVarianza.ALERTA_COACH

    def test_el_porcentaje_sale_con_signo(self) -> None:
        assert evaluar_varianza(d("67.9"), d("70.0")).porcentaje == d("-3.0")


class TestPromedioDePesajes:
    def test_promedia_hasta_tres_fechas(self) -> None:
        assert promedio_de_pesajes([d("68.0"), d("67.4"), d("68.2")]) == d("67.9")

    def test_uno_solo_es_valido(self) -> None:
        assert promedio_de_pesajes([d("68.0")]) == d("68.0")

    def test_mas_de_tres_se_rechaza(self) -> None:
        pesos = [d("68.0")] * (MAX_PESAJES_POR_CICLO + 1)
        with pytest.raises(ErrorDeDominio) as exc:
            promedio_de_pesajes(pesos)
        assert exc.value.codigo is Codigo.PESAJES_DEL_CICLO_AGOTADOS

    def test_lista_vacia_es_error_de_programacion_no_de_negocio(self) -> None:
        with pytest.raises(ValueError):
            promedio_de_pesajes([])
