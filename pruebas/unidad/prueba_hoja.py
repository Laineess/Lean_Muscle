"""Las tablas de consulta de la calculadora.

Lo que se comprueba aquí no es que la tabla salga, sino que **marque bien**: la coach la abre
para ubicar a su alumna de un vistazo, y una marca en la fila equivocada la manda a leer el
rango de otra persona.

Las escalas se comprueban contra el dominio y no contra una copia: si alguien mueve un corte
de IMC y la tabla no lo sigue, la pantalla y el cálculo se separan sin que nadie se entere.
"""

from __future__ import annotations

from decimal import Decimal
from itertools import pairwise

import pytest

from app.dominio.calculadora import (
    BaseProteina,
    NivelActividad,
    Prescripcion,
    RelacionGanancia,
    RepartoMacros,
    Sexo,
    calcular,
    clasificar_imc,
    proyectar_ganancia,
)
from app.servicios import hoja

PESO = Decimal("102.4")
GRASA = Decimal("0.30")
REPARTO = RepartoMacros(Decimal("0.50"), Decimal("0.28"), Decimal("0.22"))
SUPERAVIT = Decimal("0.10")


def _prescripcion(ajuste: Decimal, sexo: Sexo = Sexo.MASCULINO) -> Prescripcion:
    return calcular(
        peso_kg=PESO,
        porcentaje_grasa=GRASA,
        estatura_cm=178,
        edad=31,
        sexo=sexo,
        actividad=NivelActividad.ACTIVO,
        porcentaje_ajuste=ajuste,
        reparto=REPARTO,
    )


def _hoja(
    ajuste: Decimal = SUPERAVIT,
    sexo: Sexo = Sexo.MASCULINO,
    actividad: NivelActividad = NivelActividad.ACTIVO,
    base: BaseProteina = BaseProteina.MASA_LIBRE_DE_GRASA,
    dias_refeed: int = 1,
    relacion: RelacionGanancia = RelacionGanancia.DOS_A_UNO,
    peso: Decimal = PESO,
    grasa: Decimal = GRASA,
    estatura: int = 178,
) -> hoja.Hoja:
    p = calcular(
        peso_kg=peso,
        porcentaje_grasa=grasa,
        estatura_cm=estatura,
        edad=31,
        sexo=sexo,
        actividad=actividad,
        porcentaje_ajuste=ajuste,
        reparto=REPARTO,
        base_proteina=base,
        dias_refeed=dias_refeed,
    )
    return hoja.construir(
        alumna="Andrea",
        edad=31,
        sexo=sexo,
        prescripcion=p,
        actividad=actividad,
        porcentaje_ajuste=ajuste,
        base_proteina=base,
        dia_bajo=Decimal(26),
        dias_refeed=dias_refeed,
        perdida=None,
        ganancia=None,
        relacion_ganancia=relacion,
        semanas_ganancia=20,
    )


def _tabla(h: hoja.Hoja, titulo: str) -> hoja.Tabla:
    return next(t for t in h.tablas if t.titulo == titulo)


def _marcadas(t: hoja.Tabla) -> list[str]:
    return [f.celdas[0] for f in t.filas if f.suya]


def _todo_el_texto(h: hoja.Hoja) -> str:
    partes: list[str] = []
    for t in h.tablas:
        partes += [t.titulo, t.nota, *t.encabezados]
        partes += [c for f in t.filas for c in f.celdas]
    return " ".join(partes)


class TestEscalaDeImc:
    def test_los_tramos_cubren_la_escala_sin_huecos_ni_solapes(self) -> None:
        for antes, despues in pairwise(_hoja().escala_imc):
            assert despues.desde == antes.hasta + 1

    def test_va_de_dieciseis_a_treinta_y_cinco(self) -> None:
        tramos = _hoja().escala_imc
        assert tramos[0].desde == hoja.IMC_MIN
        assert tramos[-1].hasta == hoja.IMC_MAX

    def test_marca_un_tramo_y_solo_uno(self) -> None:
        assert sum(1 for t in _hoja().escala_imc if t.suyo) == 1

    def test_marca_el_mismo_tramo_que_clasifica_el_dominio(self) -> None:
        suyo = next(t.nombre for t in _hoja().escala_imc if t.suyo)
        assert suyo == clasificar_imc(_prescripcion(SUPERAVIT).composicion.imc)

    def test_su_imc_de_treinta_y_dos_cae_en_obesidad(self) -> None:
        assert [t.nombre for t in _hoja().escala_imc if t.suyo] == ["Obesidad"]

    def test_los_nombres_salen_del_dominio(self) -> None:
        # Si alguien renombra un tramo en la calculadora, la tabla lo sigue sola.
        nombres = [t.nombre for t in _hoja().escala_imc]
        assert nombres == ["Muy delgado", "Delgado", "Normal", "Sobre peso", "Obesidad"]


class TestMarcadoDeLasTablas:
    def test_la_actividad_marca_el_nivel_del_plan(self) -> None:
        t = _tabla(_hoja(actividad=NivelActividad.MUY_INTENSO), "Multiplicador de actividad")
        assert _marcadas(t) == ["Muy intenso"]

    def test_estan_los_ocho_niveles_y_todos_con_nombre(self) -> None:
        t = _tabla(_hoja(), "Multiplicador de actividad")
        assert len(t.filas) == len(NivelActividad)
        assert all(f.celdas[0] and not f.celdas[0][0].isdigit() for f in t.filas)

    def test_la_base_de_proteina_marca_la_que_usa(self) -> None:
        t = _tabla(_hoja(base=BaseProteina.PESO_TOTAL), "Base del cálculo de proteína")
        assert _marcadas(t) == ["Gramos por kilo de peso total"]

    def test_los_refeeds_marcan_los_dias_del_plan(self) -> None:
        assert _marcadas(_tabla(_hoja(dias_refeed=2), "Refeeds")) == ["Dos días"]
        assert _marcadas(_tabla(_hoja(dias_refeed=0), "Refeeds")) == ["Ninguno"]

    def test_la_tmb_marca_su_genero(self) -> None:
        titulo = "Ecuación de la tasa metabólica basal"
        assert _marcadas(_tabla(_hoja(sexo=Sexo.FEMENINO), titulo)) == ["Femenino"]
        assert _marcadas(_tabla(_hoja(sexo=Sexo.MASCULINO), titulo)) == ["Masculino"]

    def test_el_rango_no_marca_filas_como_suyas(self) -> None:
        # Las tres son suyas. Aquí el aviso es otro: cuál se salió.
        assert _marcadas(_tabla(_hoja(), "Rango de referencia")) == []

    def test_el_rango_senala_el_macro_que_se_sale(self) -> None:
        t = _tabla(_hoja(), "Rango de referencia")
        # Con superávit la proteína se dispara por encima de 3.0 g/kg.
        assert "Proteínas" in [f.celdas[0] for f in t.filas if f.fuera]

    def test_dentro_de_rango_no_senala_nada(self) -> None:
        t = _tabla(_hoja(ajuste=Decimal("-0.28")), "Rango de referencia")
        assert [f.celdas[0] for f in t.filas if f.fuera] == []


class TestTablaDeVolumen:
    TITULO = "Proyección de aumento de músculo"

    def test_trae_las_siete_filas_de_la_proyeccion(self) -> None:
        assert len(_tabla(_hoja(), self.TITULO).filas) == 7

    def test_las_dos_relaciones_van_en_paralelo(self) -> None:
        assert _tabla(_hoja(), self.TITULO).encabezados == [
            "Concepto",
            "Relación 2:1",
            "Relación 1:1",
        ]

    def test_el_porcentaje_mensual_esta_presente(self) -> None:
        rotulos = [f.celdas[0] for f in _tabla(_hoja(), self.TITULO).filas]
        assert "Porcentaje de aumento mensual" in rotulos

    def test_las_filas_que_no_dependen_de_la_relacion_dejan_vacia_la_segunda(self) -> None:
        comunes = {"Aumento de peso semanal", "Porcentaje de aumento mensual"}
        for f in _tabla(_hoja(), self.TITULO).filas:
            if f.celdas[0] in comunes:
                assert f.celdas[2] == ""

    def test_en_deficit_la_tabla_sigue_estando(self) -> None:
        # Es de consulta: la que desaparece cuando la alumna baja nunca se consulta.
        h = _hoja(ajuste=Decimal("-0.28"))
        assert any(t.titulo == self.TITULO for t in h.tablas)

    def test_en_deficit_los_numeros_salen_en_negativo(self) -> None:
        t = _tabla(_hoja(ajuste=Decimal("-0.28")), self.TITULO)
        semanal = next(f for f in t.filas if f.celdas[0] == "Aumento de peso semanal")
        assert semanal.celdas[1].startswith("-")

    def test_marca_la_columna_de_la_relacion_del_plan(self) -> None:
        dos = _tabla(_hoja(relacion=RelacionGanancia.DOS_A_UNO), self.TITULO)
        uno = _tabla(_hoja(relacion=RelacionGanancia.UNO_A_UNO), self.TITULO)
        assert dos.encabezados[dos.columna_suya or 0] == "Relación 2:1"
        assert uno.encabezados[uno.columna_suya or 0] == "Relación 1:1"

    def test_ninguna_fila_se_marca_como_suya(self) -> None:
        # Lo que le toca es una columna, no una fila: marcar ambas diría dos cosas.
        assert _marcadas(_tabla(_hoja(), self.TITULO)) == []

    def test_con_relacion_uno_a_uno_musculo_y_grasa_se_igualan(self) -> None:
        p = _prescripcion(SUPERAVIT)
        g = proyectar_ganancia(p.composicion, p.energia, 20, RelacionGanancia.UNO_A_UNO)
        # La igualdad es del reparto, no de los decimales: uno sale de multiplicar y el otro
        # de restar, y a la vigésima cifra eso ya no coincide al dígito.
        assert abs(g.musculo_total_kg - g.grasa_total_kg) < Decimal("1e-20")


class TestRotulos:
    @pytest.mark.parametrize("abreviatura", ["gr x kg", "MLG (", "Kcal por", "g/kg"])
    def test_no_quedan_abreviaturas(self, abreviatura: str) -> None:
        assert abreviatura not in _todo_el_texto(_hoja())

    @pytest.mark.parametrize("rastro", ["E65", "H17", "G65", "B88", "Excel", "celda"])
    def test_ninguna_tabla_nombra_el_archivo_de_origen(self, rastro: str) -> None:
        # La coach ya no abre esa hoja: mandarla ahí desde la pantalla no la ayuda.
        assert rastro not in _todo_el_texto(_hoja())


class TestElImcMarcaElValorExacto:
    """Marcar el tramo entero diría que está en sus seis valores a la vez."""

    def _tramo_suyo(self, peso: Decimal, estatura: int) -> hoja.TramoDeImc:
        h = _hoja(peso=peso, estatura=estatura)
        return next(t for t in h.escala_imc if t.suyo)

    def test_solo_el_tramo_suyo_lleva_valor(self) -> None:
        h = _hoja()
        assert [t.valor for t in h.escala_imc if not t.suyo] == [None] * 4

    @pytest.mark.parametrize(
        ("peso", "estatura", "esperado", "tramo"),
        [
            (Decimal("102.4"), 178, 32, "Obesidad"),
            (Decimal("58.0"), 162, 22, "Normal"),
            (Decimal("49.5"), 168, 17, "Muy delgado"),
            (Decimal("75.0"), 175, 24, "Normal"),
            (Decimal("85.0"), 175, 27, "Sobre peso"),
        ],
    )
    def test_cae_en_el_entero_de_su_indice(
        self, peso: Decimal, estatura: int, esperado: int, tramo: str
    ) -> None:
        suyo = self._tramo_suyo(peso, estatura)
        assert suyo.valor == esperado
        assert suyo.nombre == tramo
        assert suyo.desde <= esperado <= suyo.hasta

    def test_por_debajo_del_piso_se_recorta_sin_perder_el_tramo(self) -> None:
        # IMC 15.2: la tabla empieza en 16, así que se señala ahí.
        suyo = self._tramo_suyo(Decimal("44.0"), 170)
        assert suyo.valor == hoja.IMC_MIN
        assert suyo.nombre == "Muy delgado"

    def test_por_encima_del_techo_se_recorta_sin_perder_el_tramo(self) -> None:
        suyo = self._tramo_suyo(Decimal("140.0"), 165)
        assert suyo.valor == hoja.IMC_MAX
        assert suyo.nombre == "Obesidad"

    def test_el_valor_siempre_cae_dentro_de_su_propio_tramo(self) -> None:
        for peso in (Decimal("45"), Decimal("60"), Decimal("75"), Decimal("95"), Decimal("130")):
            suyo = self._tramo_suyo(peso, 170)
            assert suyo.valor is not None
            assert suyo.desde <= suyo.valor <= suyo.hasta
