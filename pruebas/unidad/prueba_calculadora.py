"""La calculadora reproduce, celda por celda, `Calculadora del Fitness.xlsm`.

Estas pruebas no comprueban que el código "funcione": comprueban que **da los mismos
números que la hoja de la clienta**. Si alguna falla, el plan de sus alumnas cambió.

Caso de referencia: el que viene capturado en el archivo original.
    Edad 31 · Peso 102.4 kg · 30 % de grasa · 1.78 m · Masculino
    Actividad 1.4 · Ajuste −28 % · Macros 50/28/22 · Objetivo 15 % de grasa
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.compartido.errores import Codigo, ErrorDeDominio
from app.dominio.calculadora import (
    BaseProteina,
    Composicion,
    Energia,
    NivelActividad,
    RelacionGanancia,
    RepartoMacros,
    Sexo,
    calcular,
    clasificar_imc,
    deficit_promedio_semanal,
    deficit_recomendado,
    energia,
    gramos_por_kilo,
    macros,
    proyectar_ganancia,
    proyectar_perdida,
    tasa_metabolica_basal,
)

PESO = Decimal("102.4")
GRASA = Decimal("0.30")
ESTATURA = 178
EDAD = 31
OBJETIVO = Decimal("0.15")
AJUSTE = Decimal("-0.28")
REPARTO = RepartoMacros(Decimal("0.50"), Decimal("0.28"), Decimal("0.22"))

COMP = Composicion(peso_kg=PESO, porcentaje_grasa=GRASA, estatura_cm=ESTATURA)


def cerca(valor: Decimal, esperado: str, tolerancia: str = "0.001") -> bool:
    return abs(valor - Decimal(esperado)) <= Decimal(tolerancia)


class TestComposicion:
    def test_masa_grasa(self) -> None:
        assert COMP.masa_grasa_kg == Decimal("30.720")  # C14

    def test_masa_libre_de_grasa(self) -> None:
        assert COMP.masa_libre_de_grasa_kg == Decimal("71.680")  # C13

    def test_imc(self) -> None:
        assert cerca(COMP.imc, "32.319151622")  # C11

    def test_clasificacion_de_imc(self) -> None:
        assert COMP.clasificacion_imc == "Obesidad"  # E11

    def test_diferencia_peso_estatura(self) -> None:
        # C12: peso menos el índice de Broca (estatura en cm − 100).
        assert COMP.diferencia_peso_estatura_kg == Decimal("24.4")

    @pytest.mark.parametrize(
        ("imc", "etiqueta"),
        [
            ("16", "Muy delgado"),
            ("17.9", "Muy delgado"),
            ("18", "Delgado"),
            ("20.9", "Delgado"),
            ("21", "Normal"),
            ("25.9", "Normal"),
            ("26", "Sobre peso"),
            ("29.9", "Sobre peso"),
            ("30", "Obesidad"),
            ("42", "Obesidad"),
        ],
    )
    def test_la_escala_de_imc_respeta_los_cortes_de_la_hoja(self, imc: str, etiqueta: str) -> None:
        assert clasificar_imc(Decimal(imc)) == etiqueta


class TestTasaMetabolicaBasal:
    def test_hombre(self) -> None:
        assert cerca(tasa_metabolica_basal(COMP, Sexo.MASCULINO, EDAD), "2037.34652")  # B87

    def test_mujer(self) -> None:
        assert cerca(tasa_metabolica_basal(COMP, Sexo.FEMENINO, EDAD), "1839.34652")  # B88

    def test_la_diferencia_entre_sexos_son_exactamente_198_kcal(self) -> None:
        # En la hoja la fórmula femenina es idéntica salvo que multiplica el 198 por cero.
        hombre = tasa_metabolica_basal(COMP, Sexo.MASCULINO, EDAD)
        mujer = tasa_metabolica_basal(COMP, Sexo.FEMENINO, EDAD)
        assert hombre - mujer == Decimal("198")


class TestEnergia:
    def setup_method(self) -> None:
        self.tmb = tasa_metabolica_basal(COMP, Sexo.MASCULINO, EDAD)
        self.e = energia(self.tmb, NivelActividad.ACTIVO, AJUSTE)

    def test_mantenimiento(self) -> None:
        assert cerca(self.e.mantenimiento_kcal, "3137.5136408")  # C19

    def test_calorias_ajustadas(self) -> None:
        assert cerca(self.e.ajustadas_kcal, "2259.009821376")  # C20

    def test_ajuste_diario(self) -> None:
        assert cerca(self.e.ajuste_diario_kcal, "-878.503819424")  # C21

    def test_calorias_semanales(self) -> None:
        assert cerca(self.e.semanales_kcal, "15813.068749632", "0.01")  # C22

    def test_ajuste_semanal(self) -> None:
        assert cerca(self.e.ajuste_semanal_kcal, "-6149.526735968", "0.01")  # C23

    def test_un_ajuste_negativo_es_deficit(self) -> None:
        assert self.e.es_deficit


class TestMacros:
    def setup_method(self) -> None:
        tmb = tasa_metabolica_basal(COMP, Sexo.MASCULINO, EDAD)
        self.e = energia(tmb, NivelActividad.ACTIVO, AJUSTE)
        self.m = macros(self.e.ajustadas_kcal, REPARTO)

    def test_carbohidratos(self) -> None:
        assert cerca(self.m.carbohidrato_g, "282.376227672")  # B93

    def test_proteina(self) -> None:
        assert cerca(self.m.proteina_g, "158.130687496")  # B94

    def test_grasa(self) -> None:
        assert cerca(self.m.grasa_g, "55.220240078")  # B95

    def test_los_gramos_reconstruyen_las_calorias_exactas(self) -> None:
        # Por construcción cuadra al 100 %: no hay tolerancia que negociar.
        assert cerca(self.m.kcal(), str(self.e.ajustadas_kcal), "0.000001")

    def test_proteina_por_kilo_de_masa_libre_de_grasa(self) -> None:
        gkg = gramos_por_kilo(self.m, COMP, BaseProteina.MASA_LIBRE_DE_GRASA)
        assert cerca(gkg["proteina"], "2.2060642787")  # C80

    def test_proteina_por_kilo_de_peso_total(self) -> None:
        gkg = gramos_por_kilo(self.m, COMP, BaseProteina.PESO_TOTAL)
        assert cerca(gkg["proteina"], "1.5442449951")  # C79

    def test_carbohidrato_y_grasa_por_kilo(self) -> None:
        gkg = gramos_por_kilo(self.m, COMP, BaseProteina.MASA_LIBRE_DE_GRASA)
        assert cerca(gkg["carbohidrato"], "2.7575803484")  # C30
        assert cerca(gkg["grasa"], "0.5392601570")  # C32

    def test_un_reparto_que_no_suma_cien_se_rechaza(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            RepartoMacros(Decimal("0.50"), Decimal("0.30"), Decimal("0.22"))
        assert exc.value.codigo is Codigo.REPARTO_DE_MACROS_NO_SUMA_UNO


class TestRefeeds:
    def test_un_dia_de_refeed(self) -> None:
        # B74: (26×6 + 0×1) / 7 = 22.2857 %
        assert cerca(deficit_promedio_semanal(Decimal(26), 1), "22.2857142857")

    def test_dos_dias_de_refeed(self) -> None:
        # B75: (26×5 + 0×2) / 7 = 18.5714 %
        assert cerca(deficit_promedio_semanal(Decimal(26), 2), "18.5714285714")

    def test_sin_refeeds_el_promedio_es_el_dia_bajo(self) -> None:
        assert deficit_promedio_semanal(Decimal(26), 0) == Decimal(26)

    def test_el_dia_de_refeed_puede_llevar_deficit_propio(self) -> None:
        # La hoja lo deja en 0 (mantenimiento), pero la coach puede subirlo.
        assert cerca(deficit_promedio_semanal(Decimal(26), 1, Decimal(10)), "23.7142857143")

    def test_mas_de_dos_dias_se_rechaza(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            deficit_promedio_semanal(Decimal(26), 3)
        assert exc.value.codigo is Codigo.DIAS_DE_REFEED_FUERA_DE_RANGO


class TestDeficitRecomendado:
    """La hoja traía «Déficit recomendado» rota en #REF!. De la fórmula original sobrevivió
    `× 0.75 × 0.87 × 9 / 7`, que es solo la parte de la grasa."""

    def setup_method(self) -> None:
        self.d = deficit_recomendado(COMP)

    def test_un_kilo_de_peso_bajado_trae_6172_kcal(self) -> None:
        # (0.75×0.87×9 + 0.25×0.30×4) por mil gramos.
        assert self.d.kcal_por_kilo == Decimal("6172.5")

    def test_la_banda_corresponde_al_ritmo_de_la_hoja(self) -> None:
        # 0.5 % de 102.4 kg son 0.512 kg por semana; 1 %, 1.024 kg.
        assert cerca(self.d.minimo_kcal, "451.4742857143")
        assert cerca(self.d.maximo_kcal, "902.9485714286")

    def test_el_fragmento_que_sobrevivio_es_la_mitad_de_grasa(self) -> None:
        """512 g por semana × 0.75 × 0.87 × 9 / 7, tal cual quedó escrito en la hoja."""
        grasa = Decimal(512) * Decimal("0.75") * Decimal("0.87") * Decimal(9) / Decimal(7)
        proteina = Decimal(512) * Decimal("0.25") * Decimal("0.30") * Decimal(4) / Decimal(7)
        assert cerca(grasa, "429.5314285714")
        assert cerca(grasa + proteina, "451.4742857143")

    def test_su_deficit_del_28_por_ciento_cae_dentro(self) -> None:
        tmb = tasa_metabolica_basal(COMP, Sexo.MASCULINO, EDAD)
        e = energia(tmb, NivelActividad.ACTIVO, AJUSTE)
        assert self.d.contiene(-e.ajuste_diario_kcal)

    def test_un_deficit_agresivo_queda_fuera(self) -> None:
        assert not self.d.contiene(Decimal(1500))

    def test_la_prescripcion_lo_trae(self) -> None:
        r = calcular(
            peso_kg=PESO,
            porcentaje_grasa=GRASA,
            estatura_cm=ESTATURA,
            edad=EDAD,
            sexo=Sexo.MASCULINO,
            actividad=NivelActividad.ACTIVO,
            porcentaje_ajuste=AJUSTE,
            reparto=RepartoMacros(Decimal("0.50"), Decimal("0.28"), Decimal("0.22")),
        )
        assert r.deficit_recomendado.kcal_por_kilo == Decimal("6172.5")


class TestProyeccionDePerdida:
    def setup_method(self) -> None:
        tmb = tasa_metabolica_basal(COMP, Sexo.MASCULINO, EDAD)
        self.e = energia(tmb, NivelActividad.ACTIVO, AJUSTE)
        self.p = proyectar_perdida(COMP, OBJETIVO, self.e)

    def test_kilos_de_grasa_por_bajar(self) -> None:
        assert cerca(self.p.kg_grasa_por_bajar, "15.36")  # H108

    def test_masa_libre_de_grasa_que_se_pierde(self) -> None:
        assert cerca(self.p.kg_mlg_que_se_pierden, "3.072")  # H106

    def test_kilos_totales_por_bajar(self) -> None:
        # H6: no todo lo que se pierde es grasa, por eso el total supera los 15.36 kg.
        assert cerca(self.p.kg_totales_por_bajar, "18.432")

    def test_calorias_totales_a_quemar(self) -> None:
        assert cerca(self.p.kcal_totales, "123955.2", "0.1")  # H113

    def test_perdida_semanal_esperada(self) -> None:
        assert cerca(self.p.perdida_semanal_kg, "0.9144277674")  # H8

    def test_porcentaje_semanal(self) -> None:
        assert cerca(self.p.porcentaje_semanal, "0.0089299587")  # H9

    def test_dias_estimados(self) -> None:
        assert cerca(self.p.dias_estimados, "141.0980775033", "0.01")  # H10

    def test_rango_semanal_recomendado(self) -> None:
        # H7/I7: entre 0.5 % y 1.0 % del peso corporal.
        assert self.p.recomendado_semanal_min_kg == Decimal("0.512")
        assert self.p.recomendado_semanal_max_kg == Decimal("1.024")

    def test_este_ritmo_esta_dentro_de_lo_recomendado(self) -> None:
        assert self.p.dentro_de_lo_recomendado

    def test_un_deficit_agresivo_sale_del_rango_recomendado(self) -> None:
        tmb = tasa_metabolica_basal(COMP, Sexo.MASCULINO, EDAD)
        agresiva = energia(tmb, NivelActividad.ACTIVO, Decimal("-0.50"))
        assert not proyectar_perdida(COMP, OBJETIVO, agresiva).dentro_de_lo_recomendado

    def test_sin_deficit_no_hay_proyeccion_de_perdida(self) -> None:
        tmb = tasa_metabolica_basal(COMP, Sexo.MASCULINO, EDAD)
        superavit = energia(tmb, NivelActividad.ACTIVO, Decimal("0.10"))
        with pytest.raises(ErrorDeDominio) as exc:
            proyectar_perdida(COMP, OBJETIVO, superavit)
        assert exc.value.codigo is Codigo.PROYECCION_SIN_DEFICIT

    def test_un_objetivo_mayor_al_actual_no_tiene_sentido(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            proyectar_perdida(COMP, Decimal("0.35"), self.e)
        assert exc.value.codigo is Codigo.OBJETIVO_DE_GRASA_NO_ES_MENOR


class TestLaTablaDeGananciaCuadraConLaHoja:
    """G16:J23, la tabla «Proyección aumento de músculo».

    La hoja la calcula con el ajuste en déficit, así que le salen negativas —es una tabla
    de volumen alimentada con un superávit que ese caso no tiene—. Aquí se usa el mismo
    ajuste semanal con el signo cambiado, que es la fase que sí proyecta, y se comprueba
    contra las magnitudes que la hoja trae en caché.
    """

    #: C23 de la hoja, en positivo.
    AJUSTE_SEMANAL = Decimal("6149.526735968")

    def setup_method(self) -> None:
        # Solo el ajuste semanal manda en esta tabla; el resto no entra en ninguna fórmula.
        e = Energia(
            mantenimiento_kcal=Decimal(0),
            ajustadas_kcal=Decimal(0),
            ajuste_diario_kcal=self.AJUSTE_SEMANAL / Decimal(7),
            ajuste_semanal_kcal=self.AJUSTE_SEMANAL,
            semanales_kcal=Decimal(0),
        )
        self.dos = proyectar_ganancia(COMP, e, 20, RelacionGanancia.DOS_A_UNO)
        self.uno = proyectar_ganancia(COMP, e, 20, RelacionGanancia.UNO_A_UNO)

    def test_h17_aumento_de_peso_semanal(self) -> None:
        assert cerca(self.dos.aumento_semanal_kg, "0.7320865161866666")

    def test_h18_musculo_semanal_dos_a_uno(self) -> None:
        assert cerca(self.dos.musculo_semanal_kg, "0.2415885503416")

    def test_i18_musculo_semanal_uno_a_uno(self) -> None:
        assert cerca(self.uno.musculo_semanal_kg, "0.3660432580933333")

    def test_h19_porcentaje_de_aumento_mensual(self) -> None:
        # La fila que faltaba en pantalla: aumento semanal entre el peso, por cuatro semanas.
        assert cerca(self.dos.porcentaje_mensual, "0.028597129538541665")

    def test_h21_aumento_de_peso_total(self) -> None:
        assert cerca(self.dos.aumento_total_kg, "14.641730323733332")

    def test_h22_musculo_total_dos_a_uno(self) -> None:
        assert cerca(self.dos.musculo_total_kg, "4.831771006832001")

    def test_i22_musculo_total_uno_a_uno(self) -> None:
        assert cerca(self.uno.musculo_total_kg, "7.320865161866666")

    def test_h23_grasa_total_dos_a_uno(self) -> None:
        assert cerca(self.dos.grasa_total_kg, "9.809959316901331")

    def test_i23_grasa_total_uno_a_uno(self) -> None:
        # Con relación 1:1 la mitad de lo que sube es grasa, así que iguala al músculo.
        assert cerca(self.uno.grasa_total_kg, "7.320865161866666")

    def test_las_dos_relaciones_reparten_el_mismo_peso_total(self) -> None:
        assert self.dos.aumento_total_kg == self.uno.aumento_total_kg


class TestProyeccionDeGanancia:
    def setup_method(self) -> None:
        tmb = tasa_metabolica_basal(COMP, Sexo.MASCULINO, EDAD)
        self.e = energia(tmb, NivelActividad.ACTIVO, Decimal("0.10"))
        self.g = proyectar_ganancia(COMP, self.e, semanas=20)

    def test_aumento_semanal(self) -> None:
        # H17: superávit semanal entre 8400 kcal por kilo.
        esperado = self.e.ajuste_semanal_kcal / Decimal("8400")
        assert self.g.aumento_semanal_kg == esperado

    def test_relacion_dos_a_uno_asigna_un_tercio_a_musculo(self) -> None:
        assert self.g.musculo_semanal_kg == self.g.aumento_semanal_kg * Decimal("0.33")

    def test_relacion_uno_a_uno_asigna_la_mitad(self) -> None:
        g = proyectar_ganancia(COMP, self.e, 20, RelacionGanancia.UNO_A_UNO)
        assert g.musculo_semanal_kg == g.aumento_semanal_kg * Decimal("0.50")

    def test_el_resto_del_peso_ganado_es_grasa(self) -> None:
        assert self.g.grasa_total_kg == self.g.aumento_total_kg - self.g.musculo_total_kg

    def test_en_deficit_no_hay_proyeccion_de_ganancia(self) -> None:
        tmb = tasa_metabolica_basal(COMP, Sexo.MASCULINO, EDAD)
        deficit = energia(tmb, NivelActividad.ACTIVO, AJUSTE)
        with pytest.raises(ErrorDeDominio) as exc:
            proyectar_ganancia(COMP, deficit, 20)
        assert exc.value.codigo is Codigo.PROYECCION_SIN_SUPERAVIT


class TestFachada:
    def test_el_recorrido_completo_da_los_numeros_de_la_hoja(self) -> None:
        p = calcular(
            peso_kg=PESO,
            porcentaje_grasa=GRASA,
            estatura_cm=ESTATURA,
            edad=EDAD,
            sexo=Sexo.MASCULINO,
            actividad=NivelActividad.ACTIVO,
            porcentaje_ajuste=AJUSTE,
            reparto=REPARTO,
            base_proteina=BaseProteina.MASA_LIBRE_DE_GRASA,
            dias_refeed=1,
        )
        assert cerca(p.tmb_kcal, "2037.34652")
        assert cerca(p.energia.ajustadas_kcal, "2259.009821376")
        assert cerca(p.macros.carbohidrato_g, "282.376227672")
        assert cerca(p.macros.proteina_g, "158.130687496")
        assert cerca(p.macros.grasa_g, "55.220240078")
        assert p.deficit_promedio_semanal is not None
        assert cerca(p.deficit_promedio_semanal, "0.24", "0.01")

    def test_avisa_cuando_un_macro_sale_del_rango_de_referencia(self) -> None:
        # 90 % de carbohidratos: dispara el aviso de carbos y el de grasa, sin bloquear.
        p = calcular(
            peso_kg=PESO,
            porcentaje_grasa=GRASA,
            estatura_cm=ESTATURA,
            edad=EDAD,
            sexo=Sexo.MASCULINO,
            actividad=NivelActividad.ACTIVO,
            porcentaje_ajuste=AJUSTE,
            reparto=RepartoMacros(Decimal("0.90"), Decimal("0.05"), Decimal("0.05")),
        )
        assert "proteina" in p.avisos_de_rango
        assert "grasa" in p.avisos_de_rango

    def test_un_porcentaje_de_grasa_imposible_se_rechaza(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            calcular(
                peso_kg=PESO,
                porcentaje_grasa=Decimal("1.5"),
                estatura_cm=ESTATURA,
                edad=EDAD,
                sexo=Sexo.MASCULINO,
                actividad=NivelActividad.ACTIVO,
                porcentaje_ajuste=AJUSTE,
                reparto=REPARTO,
            )
        assert exc.value.codigo is Codigo.PORCENTAJE_DE_GRASA_INVALIDO

    def test_los_ocho_niveles_de_actividad_de_la_hoja_estan_completos(self) -> None:
        from app.dominio.calculadora import MULTIPLICADOR

        assert sorted(MULTIPLICADOR.values()) == [
            Decimal(v) for v in ("1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8", "1.9")
        ]
