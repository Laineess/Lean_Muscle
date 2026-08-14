"""El código y la hoja dan el mismo número, celda por celda.

Las fórmulas de `app/dominio/calculadora.py` salen de «Calculadora del Fitness.xlsm», que es
el archivo con el que la coach lleva años trabajando. Que coincidan no puede depender de que
alguien se acuerde: esta prueba lee la hoja, toma **sus** datos de entrada, corre el código
con ellos y compara los resultados contra los valores que el propio Excel calculó.

Si alguien toca una constante, aquí sale qué celda dejó de cuadrar y por cuánto.

La hoja se lee con `data_only=True`: openpyxl no evalúa fórmulas, devuelve el último
resultado que Excel guardó. Por eso el archivo tiene que abrirse y guardarse con Excel si se
cambian sus entradas, o los valores en caché quedarían viejos.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from app.dominio.calculadora import (
    KCAL_POR_KILO_GANADO,
    PROPORCION_MUSCULO,
    BaseProteina,
    Composicion,
    NivelActividad,
    RelacionGanancia,
    RepartoMacros,
    Sexo,
    calcular,
    deficit_promedio_semanal,
    energia,
    proyectar_ganancia,
    proyectar_perdida,
    tasa_metabolica_basal,
)

HOJA = Path(__file__).resolve().parents[2] / "Calculadora del Fitness.xlsm"
NOMBRE_HOJA = "Calculo bajar de peso "

#: Margen de comparación. La hoja calcula en coma flotante y el código en decimal: una
#: diferencia por debajo de esto es ruido de representación, no una fórmula distinta.
TOLERANCIA = Decimal("0.0000001")

#: Qué multiplicador de la hoja es cada nivel. Es la lista desplegable de C16 (tabla G65:H72).
POR_FACTOR = {
    Decimal("1.2"): NivelActividad.MUY_POCO_ACTIVO,
    Decimal("1.3"): NivelActividad.POCO_ACTIVO,
    Decimal("1.4"): NivelActividad.ACTIVO,
    Decimal("1.5"): NivelActividad.MUY_ACTIVO,
    Decimal("1.6"): NivelActividad.INTENSO,
    Decimal("1.7"): NivelActividad.MUY_INTENSO,
    Decimal("1.8"): NivelActividad.ATLETA,
    Decimal("1.9"): NivelActividad.ATLETA_ELITE,
}


@pytest.fixture(scope="module")
def hoja() -> Any:
    openpyxl = pytest.importorskip("openpyxl")
    if not HOJA.is_file():  # pragma: no cover - depende de la copia de trabajo
        pytest.skip(f"falta {HOJA.name}")
    return openpyxl.load_workbook(HOJA, data_only=True)[NOMBRE_HOJA]


def _d(hoja: Any, celda: str) -> Decimal:
    """El valor que Excel dejó guardado en esa celda."""
    valor = hoja[celda].value
    assert valor is not None, f"la celda {celda} está vacía en la hoja"
    return Decimal(str(valor))


def _cuadra(celda: str, hoja: Any, calculado: Decimal) -> None:
    esperado = _d(hoja, celda)
    diferencia = abs(esperado - calculado)
    referencia = max(abs(esperado), Decimal(1))
    assert diferencia / referencia <= TOLERANCIA, (
        f"celda {celda}: la hoja dice {esperado} y el código {calculado} (diferencia {diferencia})"
    )


@pytest.fixture(scope="module")
def entradas(hoja: Any) -> dict[str, Any]:
    """Los datos que la hoja tiene capturados. No se copian a mano: se leen de ella."""
    return {
        "edad": int(_d(hoja, "C6")),
        "peso_kg": _d(hoja, "C7"),
        "porcentaje_grasa": _d(hoja, "C8"),
        "estatura_cm": int(_d(hoja, "C9") * 100),
        "sexo": Sexo.MASCULINO if hoja["C10"].value == "Masculino" else Sexo.FEMENINO,
        "porcentaje_grasa_objetivo": _d(hoja, "C15"),
        "actividad": POR_FACTOR[_d(hoja, "C16")],
        "porcentaje_ajuste": _d(hoja, "C17"),
        "reparto": RepartoMacros(
            carbohidrato=_d(hoja, "B27"), proteina=_d(hoja, "C27"), grasa=_d(hoja, "E27")
        ),
    }


@pytest.fixture(scope="module")
def resultado(entradas: dict[str, Any]) -> Any:
    return calcular(
        peso_kg=entradas["peso_kg"],
        porcentaje_grasa=entradas["porcentaje_grasa"],
        estatura_cm=entradas["estatura_cm"],
        edad=entradas["edad"],
        sexo=entradas["sexo"],
        actividad=entradas["actividad"],
        porcentaje_ajuste=entradas["porcentaje_ajuste"],
        reparto=entradas["reparto"],
        base_proteina=BaseProteina.MASA_LIBRE_DE_GRASA,
    )


class TestComposicion:
    def test_cuadra_con_la_hoja(self, hoja: Any, resultado: Any) -> None:
        comp = resultado.composicion
        _cuadra("C11", hoja, comp.imc)
        _cuadra("C12", hoja, comp.diferencia_peso_estatura_kg)
        _cuadra("C13", hoja, comp.masa_libre_de_grasa_kg)
        _cuadra("C14", hoja, comp.masa_grasa_kg)
        _cuadra("B66", hoja, comp.peso_ideal_broca_kg)
        _cuadra("B101", hoja, (Decimal(comp.estatura_cm) / 100) ** 2)

    def test_la_clasificacion_de_imc_es_la_de_la_tabla(self, hoja: Any, resultado: Any) -> None:
        """Celda E11, que en la hoja es un VLOOKUP aproximado sobre E65:F84."""
        assert resultado.composicion.clasificacion_imc == hoja["E11"].value


class TestEnergia:
    def test_cuadra_con_la_hoja(self, hoja: Any, resultado: Any) -> None:
        _cuadra("C18", hoja, resultado.tmb_kcal)
        _cuadra("C19", hoja, resultado.energia.mantenimiento_kcal)
        _cuadra("C20", hoja, resultado.energia.ajustadas_kcal)
        _cuadra("C21", hoja, resultado.energia.ajuste_diario_kcal)
        _cuadra("C22", hoja, resultado.energia.ajustadas_kcal * 7)
        _cuadra("C23", hoja, resultado.energia.ajuste_semanal_kcal)


class TestMacros:
    def test_los_gramos_cuadran_con_la_hoja(self, hoja: Any, resultado: Any) -> None:
        _cuadra("B93", hoja, resultado.macros.carbohidrato_g)
        _cuadra("B94", hoja, resultado.macros.proteina_g)
        _cuadra("B95", hoja, resultado.macros.grasa_g)

    def test_los_gramos_por_kilo_cuadran(self, hoja: Any, resultado: Any) -> None:
        """C30 y C32 van contra peso total; C31, contra masa libre de grasa."""
        _cuadra("C30", hoja, resultado.gramos_por_kilo["carbohidrato"])
        _cuadra("C31", hoja, resultado.gramos_por_kilo["proteina"])
        _cuadra("C32", hoja, resultado.gramos_por_kilo["grasa"])


class TestRefeeds:
    def test_el_deficit_promedio_semanal_cuadra(self, hoja: Any) -> None:
        """Celda J14: el número que de verdad manda, no el del día bajo."""
        dia_bajo = _d(hoja, "G14") / 100
        dias = int(_d(hoja, "H14"))
        promedio = deficit_promedio_semanal(dia_bajo, dias, Decimal(0))
        _cuadra("J14", hoja, promedio * 100)


@pytest.fixture(scope="module")
def proyeccion(entradas: dict[str, Any], resultado: Any) -> Any:
    return proyectar_perdida(
        resultado.composicion, entradas["porcentaje_grasa_objetivo"], resultado.energia
    )


class TestProyeccionDePerdida:
    def test_cuadra_con_la_hoja(self, hoja: Any, proyeccion: Any) -> None:
        _cuadra("H108", hoja, proyeccion.kg_grasa_por_bajar)
        _cuadra("H106", hoja, proyeccion.kg_mlg_que_se_pierden)
        _cuadra("H110", hoja, proyeccion.kg_totales_por_bajar)
        _cuadra("H113", hoja, proyeccion.kcal_totales)
        _cuadra("H117", hoja, proyeccion.perdida_semanal_kg)
        _cuadra("H9", hoja, proyeccion.porcentaje_semanal)
        _cuadra("H10", hoja, proyeccion.dias_estimados)

    def test_el_ritmo_recomendado_es_el_de_la_hoja(self, hoja: Any, proyeccion: Any) -> None:
        """Celdas H7 e I7: entre 0.5 % y 1 % del peso por semana."""
        _cuadra("H7", hoja, proyeccion.recomendado_semanal_min_kg)
        _cuadra("I7", hoja, proyeccion.recomendado_semanal_max_kg)


class TestProyeccionDeGanancia:
    """La hoja calcula el bloque de ganancia con el mismo ajuste negativo que tiene arriba,
    así que sus celdas salen en negativo. El código no lo permite —`proyectar_ganancia` exige
    superávit—, de modo que la fidelidad se comprueba sobre la fórmula y el reparto se
    verifica aparte, con un escenario que sí tiene sentido."""

    def test_las_formulas_cuadran_con_la_hoja(self, hoja: Any, resultado: Any) -> None:
        comp: Composicion = resultado.composicion
        semanal = resultado.energia.ajuste_semanal_kcal / KCAL_POR_KILO_GANADO
        _cuadra("H17", hoja, semanal)
        _cuadra("H18", hoja, semanal * PROPORCION_MUSCULO[RelacionGanancia.DOS_A_UNO])
        _cuadra("I18", hoja, semanal * PROPORCION_MUSCULO[RelacionGanancia.UNO_A_UNO])
        _cuadra("H19", hoja, semanal / comp.peso_kg * 4)
        _cuadra("H21", hoja, semanal * int(_d(hoja, "H20")))

    def test_el_reparto_de_musculo_y_grasa_suma_el_total(
        self, hoja: Any, entradas: dict[str, Any]
    ) -> None:
        comp = Composicion(
            peso_kg=entradas["peso_kg"],
            porcentaje_grasa=entradas["porcentaje_grasa"],
            estatura_cm=entradas["estatura_cm"],
        )
        superavit = energia(
            tasa_metabolica_basal(comp, entradas["sexo"], entradas["edad"]),
            entradas["actividad"],
            Decimal("0.10"),
        )
        semanas = int(_d(hoja, "H20"))
        proyeccion = proyectar_ganancia(comp, superavit, semanas, RelacionGanancia.DOS_A_UNO)

        assert proyeccion.semanas == semanas
        assert proyeccion.musculo_total_kg + proyeccion.grasa_total_kg == (
            proyeccion.aumento_total_kg
        )
