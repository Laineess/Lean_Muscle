"""La calculadora con la forma de la hoja de cálculo original.

La coach lleva años trabajando con «Calculadora del Fitness.xlsm» y sabe de memoria que el
multiplicador de actividad es C16 y que el déficit está en C17. Enseñarle los mismos bloques,
con la misma etiqueta y la celda de la que sale cada número, es lo que le permite comprobar
que la plataforma calcula lo que ella calculaba: no tiene que confiar, puede verificar.

Los valores los calcula `app/dominio/calculadora.py`, que es el único que sabe hacer cuentas.
Este módulo solo los coloca donde iban en la hoja.

Que sigan cuadrando lo vigila `pruebas/unidad/prueba_fidelidad_excel.py`, que lee el .xlsm y
compara celda por celda.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.dominio.calculadora import (
    ESCALA_IMC,
    KCAL_POR_KILO_GANADO,
    MULTIPLICADOR,
    PROPORCION_MUSCULO,
    RANGO_GKG,
    BaseProteina,
    Composicion,
    Macros,
    NivelActividad,
    Prescripcion,
    ProyeccionGanancia,
    ProyeccionPerdida,
    RelacionGanancia,
)


@dataclass(frozen=True, slots=True)
class Celda:
    """Un renglón de la hoja: su celda, su etiqueta, su valor y de dónde sale."""

    celda: str
    rotulo: str
    valor: str
    unidad: str = ""
    #: La fórmula original, tal como está en el archivo. Solo para leerla.
    formula: str = ""
    #: Verdadero si es un dato que se captura, no uno que se calcula.
    capturado: bool = False


@dataclass(frozen=True, slots=True)
class Bloque:
    titulo: str
    rango: str
    celdas: list[Celda] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Tabla:
    """Una de las tablas de consulta de la hoja: actividad, IMC, refeeds, rangos."""

    titulo: str
    rango: str
    encabezados: list[str]
    filas: list[list[str]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Hoja:
    alumna: str
    bloques: list[Bloque]
    tablas: list[Tabla]


def _n(valor: Decimal | float | int, decimales: int = 2) -> str:
    """Número con separador de miles, como lo enseña Excel."""
    return f"{Decimal(str(valor)):,.{decimales}f}".replace(",", " ")


def _pct(fraccion: Decimal, decimales: int = 1) -> str:
    return f"{fraccion * 100:.{decimales}f} %"


# ---------------------------------------------------------------------------
# Bloques
# ---------------------------------------------------------------------------


def _datos(
    comp: Composicion,
    edad: int,
    sexo: str,
    r: Prescripcion,
    ajuste: Decimal,
    actividad: NivelActividad,
) -> Bloque:
    return Bloque(
        titulo="Datos de la clienta",
        rango="B5:E23",
        celdas=[
            Celda("C6", "Edad", _n(edad, 0), "años", capturado=True),
            Celda("C7", "Peso", _n(comp.peso_kg), "kg", capturado=True),
            Celda("C8", "% grasa estimado", _pct(comp.porcentaje_grasa), capturado=True),
            Celda("C9", "Estatura", _n(Decimal(comp.estatura_cm) / 100), "mts", capturado=True),
            Celda("C10", "Género", sexo, capturado=True),
            Celda("C11", "IMC", _n(comp.imc), formula="=C7/B101"),
            Celda(
                "E11", "Clasificación", comp.clasificacion_imc, formula="=VLOOKUP(C11,E65:F84,2,1)"
            ),
            Celda(
                "C12",
                "Diferencia peso-estatura",
                _n(comp.diferencia_peso_estatura_kg),
                "kg",
                "=C7-B66",
            ),
            Celda(
                "C13", "Masa libre de grasa (MLG)", _n(comp.masa_libre_de_grasa_kg), "kg", "=C7-C14"
            ),
            Celda("C14", "Masa grasa (MG)", _n(comp.masa_grasa_kg), "kg", "=C7*C8"),
            Celda(
                "C16", "Multiplicador de actividad", _n(MULTIPLICADOR[actividad], 1), capturado=True
            ),
            Celda("C17", "% de ajuste calórico", _pct(ajuste), capturado=True),
            Celda(
                "C18", "Tasa metabólica basal", _n(r.tmb_kcal), "kcal", "=VLOOKUP(C10,A87:B88,2,0)"
            ),
            Celda(
                "C19",
                "Calorías de mantenimiento",
                _n(r.energia.mantenimiento_kcal),
                "kcal",
                "=C18*C16*1.1",
            ),
            Celda("C20", "Calorías ajustadas", _n(r.energia.ajustadas_kcal), "kcal", "=C19+D105"),
            Celda(
                "C21",
                "Calorías de ajuste diario",
                _n(r.energia.ajuste_diario_kcal),
                "kcal",
                "=C20-C19",
            ),
            Celda(
                "C22",
                "Calorías semanales según ajuste",
                _n(r.energia.semanales_kcal),
                "kcal",
                "=C20*7",
            ),
            Celda(
                "C23",
                "Calorías de ajuste semanal",
                _n(r.energia.ajuste_semanal_kcal),
                "kcal",
                "=C21*7",
            ),
        ],
    )


def _macros(m: Macros, gkg: dict[str, Decimal], base: BaseProteina) -> Bloque:
    referencia = "MLG" if base is BaseProteina.MASA_LIBRE_DE_GRASA else "peso total"
    return Bloque(
        titulo="Porcentaje de distribución de macros",
        rango="B25:E32",
        celdas=[
            Celda("B93", "Carbohidratos", _n(m.carbohidrato_g), "g", "=C20*B27/4"),
            Celda("C30", "Carbohidratos por kg de peso", _n(gkg["carbohidrato"]), "g/kg"),
            Celda("B94", "Proteína", _n(m.proteina_g), "g", "=C20*C27/4"),
            Celda("C31", f"Proteína por kg de {referencia}", _n(gkg["proteina"]), "g/kg"),
            Celda("B95", "Grasas", _n(m.grasa_g), "g", "=C20*E27/9"),
            Celda("C32", "Grasas por kg de peso", _n(gkg["grasa"]), "g/kg"),
        ],
    )


def _perdida(p: ProyeccionPerdida) -> Bloque:
    return Bloque(
        titulo="Proyección pérdida de grasa",
        rango="G5:J10",
        celdas=[
            Celda(
                "H6",
                "Kilos por bajar para llegar al objetivo",
                _n(p.kg_totales_por_bajar),
                "kg",
                "=H108+H106",
            ),
            Celda("H108", "De eso, grasa", _n(p.kg_grasa_por_bajar), "kg", "=C14-H109"),
            Celda(
                "H106",
                "De eso, masa libre de grasa",
                _n(p.kg_mlg_que_se_pierden),
                "kg",
                "=H108*20%",
            ),
            Celda(
                "H113", "Calorías totales del proceso", _n(p.kcal_totales, 0), "kcal", "=H112*1000"
            ),
            Celda(
                "H7",
                "Reducción semanal recomendada",
                f"{_n(p.recomendado_semanal_min_kg)} a {_n(p.recomendado_semanal_max_kg)}",
                "kg",
                "=C7*0.5% / =C7*1%",
            ),
            Celda(
                "H8",
                "Pérdida de peso semanal según déficit",
                _n(p.perdida_semanal_kg),
                "kg",
                "=H117",
            ),
            Celda("H9", "% de pérdida semanal", _pct(p.porcentaje_semanal, 2), formula="=H8/C7"),
            Celda(
                "H10", "Días para llegar al objetivo", _n(p.dias_estimados, 0), "días", "=H113/H115"
            ),
        ],
    )


def _ganancia(g: ProyeccionGanancia) -> Bloque:
    return Bloque(
        titulo="Proyección aumento de músculo",
        rango="G16:J23",
        celdas=[
            Celda("H17", "Aumento de peso semanal", _n(g.aumento_semanal_kg, 3), "kg", "=C23/8400"),
            Celda("H18", "De eso, músculo", _n(g.musculo_semanal_kg, 3), "kg", "=H17*33%"),
            Celda(
                "H19",
                "Porcentaje de aumento mensual",
                _pct(g.porcentaje_mensual, 2),
                formula="=H17*1/C7*4",
            ),
            Celda("H20", "Semanas de aumento", _n(g.semanas, 0), "semanas", capturado=True),
            Celda("H21", "Aumento total estimado", _n(g.aumento_total_kg), "kg", "=H17*H20"),
            Celda("H22", "De eso, músculo", _n(g.musculo_total_kg), "kg", "=H18*H20"),
            Celda("H23", "De eso, grasa", _n(g.grasa_total_kg), "kg", "=H21-H22"),
        ],
    )


def _refeeds(dia_bajo: Decimal, dias: int, promedio: Decimal | None) -> Bloque:
    return Bloque(
        titulo="Cálculo de refeeds",
        rango="G12:J14",
        celdas=[
            Celda("G14", "% de déficit del día bajo", _pct(dia_bajo), capturado=True),
            Celda("H14", "Días de refeed por semana", _n(dias, 0), "días", capturado=True),
            Celda(
                "J14",
                "Déficit promedio semanal",
                _pct(promedio) if promedio is not None else "—",
                formula="=VLOOKUP(H14,A74:B75,2,0)",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Tablas de consulta
# ---------------------------------------------------------------------------


def _filas_de_imc() -> list[list[str]]:
    """Tabla E65:F84 de la hoja. Se deriva de la escala del dominio para que no puedan
    quedar diciendo cosas distintas."""
    filas: list[list[str]] = []
    desde = Decimal(0)
    for tope, etiqueta in ESCALA_IMC:
        filas.append([f"menos de {tope}" if desde == 0 else f"{desde} a {tope}", etiqueta])
        desde = tope
    filas.append([f"{desde} o más", "Obesidad"])
    return filas


def _tablas() -> list[Tabla]:
    return [
        Tabla(
            titulo="Multiplicador de actividad",
            rango="G65:H72",
            encabezados=["Nivel", "Factor"],
            filas=[
                [n.value.replace("_", " ").capitalize(), str(MULTIPLICADOR[n])]
                for n in NivelActividad
            ],
        ),
        Tabla(
            titulo="Clasificación por IMC",
            rango="E65:F84",
            encabezados=["Desde", "Clasificación"],
            filas=_filas_de_imc(),
        ),
        Tabla(
            titulo="Rangos de referencia",
            rango="E30:E32",
            encabezados=["Macro", "g/kg"],
            filas=[
                [
                    "Carbohidratos",
                    f"{RANGO_GKG['carbohidrato'][0]} a {RANGO_GKG['carbohidrato'][1]}",
                ],
                ["Proteína", f"{RANGO_GKG['proteina'][0]} a {RANGO_GKG['proteina'][1]}"],
                ["Grasas", f"{RANGO_GKG['grasa'][0]} a {RANGO_GKG['grasa'][1]}"],
            ],
        ),
        Tabla(
            titulo="Ecuación de la tasa metabólica basal",
            rango="A87:B88",
            encabezados=["Género", "Fórmula"],
            filas=[
                ["Masculino", "13.587·MLG + 9.613·MG + 198 − 3.351·edad + 674"],
                ["Femenino", "13.587·MLG + 9.613·MG + 198·0 − 3.351·edad + 674"],
            ],
        ),
        Tabla(
            titulo="Relación de ganancia",
            rango="H18:I18",
            encabezados=["Relación", "Parte que es músculo"],
            filas=[[r.value, f"{PROPORCION_MUSCULO[r] * 100:.0f} %"] for r in RelacionGanancia],
        ),
        Tabla(
            titulo="Constantes",
            rango="C19 · H17",
            encabezados=["Concepto", "Valor"],
            filas=[
                ["Efecto térmico de los alimentos", "×1.1"],
                ["Kcal por kilo de peso ganado", str(KCAL_POR_KILO_GANADO)],
                ["Fracción de grasa pura en lo que se baja", "87 %"],
                ["Masa libre de grasa que se pierde", "20 %"],
            ],
        ),
    ]


def construir(
    *,
    alumna: str,
    edad: int,
    sexo: str,
    prescripcion: Prescripcion,
    actividad: NivelActividad,
    porcentaje_ajuste: Decimal,
    base_proteina: BaseProteina,
    dia_bajo: Decimal,
    dias_refeed: int,
    perdida: ProyeccionPerdida | None,
    ganancia: ProyeccionGanancia | None,
) -> Hoja:
    """Arma la hoja completa. Los bloques sin datos se omiten en lugar de salir vacíos."""
    bloques = [
        _datos(prescripcion.composicion, edad, sexo, prescripcion, porcentaje_ajuste, actividad),
        _macros(prescripcion.macros, prescripcion.gramos_por_kilo, base_proteina),
        _refeeds(dia_bajo, dias_refeed, prescripcion.deficit_promedio_semanal),
    ]
    if perdida is not None:
        bloques.append(_perdida(perdida))
    if ganancia is not None:
        bloques.append(_ganancia(ganancia))

    return Hoja(alumna=alumna, bloques=bloques, tablas=_tablas())


__all__ = ["Bloque", "Celda", "Hoja", "Tabla", "construir"]
