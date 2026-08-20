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
    Energia,
    Macros,
    NivelActividad,
    Prescripcion,
    ProyeccionGanancia,
    ProyeccionPerdida,
    RelacionGanancia,
    Sexo,
    clasificar_imc,
    deficit_promedio_semanal,
    proyectar_ganancia,
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
class Fila:
    """Una fila de tabla.

    `suya` es la fila que le toca a esta alumna. `fuera` es distinto: la fila sí es suya,
    pero su valor se salió del rango. Son dos avisos diferentes y se pintan diferente; si
    compartieran marca, «esta es tu fila» y «esto está mal» se leerían igual.
    """

    celdas: list[str]
    suya: bool = False
    fuera: bool = False


@dataclass(frozen=True, slots=True)
class Tabla:
    """Una tabla de consulta: actividad, refeeds, rangos, proyección de volumen."""

    titulo: str
    encabezados: list[str]
    filas: list[Fila] = field(default_factory=list)
    nota: str = ""
    #: Cuando lo que le toca a la alumna es una columna y no una fila, su índice.
    columna_suya: int | None = None


@dataclass(frozen=True, slots=True)
class TramoDeImc:
    """Un tramo de la escala con sus valores enteros, de `desde` a `hasta` inclusive."""

    nombre: str
    desde: int
    hasta: int
    suyo: bool
    #: El entero exacto donde cae, solo en el tramo suyo. Marcar el tramo entero diría que
    #: está en todos sus valores a la vez.
    valor: int | None = None


@dataclass(frozen=True, slots=True)
class Hoja:
    alumna: str
    bloques: list[Bloque]
    tablas: list[Tabla]
    escala_imc: list[TramoDeImc] = field(default_factory=list)


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


#: Extremos de la escala. Fuera de estos el tramo sigue valiendo, pero la tabla no dibuja
#: cada número: nadie consulta un IMC de 60 en una lista.
IMC_MIN = 16
IMC_MAX = 35


def _escala_de_imc(imc: Decimal) -> list[TramoDeImc]:
    """La escala en tramos, marcando el valor exacto donde cae.

    Sale del dominio y no de una copia, para que la tabla no pueda decir una cosa y el
    cálculo otra. El entero se recorta a los extremos de la tabla: un 42 no dibuja treinta
    filas más, se señala en el 35 y su tramo sigue siendo el correcto.
    """
    suyo = clasificar_imc(imc)
    entero = min(max(int(imc), IMC_MIN), IMC_MAX)

    tramos: list[TramoDeImc] = []
    desde = IMC_MIN
    for tope, etiqueta in (*ESCALA_IMC, (Decimal(IMC_MAX + 1), "Obesidad")):
        hasta = int(tope) - 1
        es_suyo = suyo == etiqueta
        tramos.append(
            TramoDeImc(
                nombre=etiqueta,
                desde=desde,
                hasta=hasta,
                suyo=es_suyo,
                valor=entero if es_suyo else None,
            )
        )
        desde = int(tope)
    return tramos


#: Cómo se lee cada nivel de actividad. Sale de aquí y no del nombre de la constante para
#: que en pantalla se lea escrito, no en mayúsculas con guiones bajos.
ROTULO_ACTIVIDAD: dict[NivelActividad, str] = {
    NivelActividad.MUY_POCO_ACTIVO: "Muy poco activo",
    NivelActividad.POCO_ACTIVO: "Poco activo",
    NivelActividad.ACTIVO: "Activo",
    NivelActividad.MUY_ACTIVO: "Muy activo",
    NivelActividad.INTENSO: "Intenso",
    NivelActividad.MUY_INTENSO: "Muy intenso",
    NivelActividad.ATLETA: "Atleta",
    NivelActividad.ATLETA_ELITE: "Atleta élite",
}

ROTULO_SEXO: dict[Sexo, str] = {Sexo.MASCULINO: "Masculino", Sexo.FEMENINO: "Femenino"}

ROTULO_BASE_PROTEINA: dict[BaseProteina, str] = {
    BaseProteina.PESO_TOTAL: "Gramos por kilo de peso total",
    BaseProteina.MASA_LIBRE_DE_GRASA: "Gramos por kilo de masa libre de grasa",
}

ROTULO_MACRO: dict[str, str] = {
    "carbohidrato": "Carbohidratos",
    "proteina": "Proteínas",
    "grasa": "Grasas",
}


def _tabla_de_actividad(actual: NivelActividad) -> Tabla:
    return Tabla(
        titulo="Multiplicador de actividad",
        encabezados=["Nivel de actividad", "Factor"],
        filas=[
            Fila([ROTULO_ACTIVIDAD[n], _n(MULTIPLICADOR[n], 1)], suya=n is actual)
            for n in NivelActividad
        ],
    )


def _tabla_de_rangos(gkg: dict[str, Decimal]) -> Tabla:
    """El rango de cada macro con lo que le tocó a ella al lado."""
    return Tabla(
        titulo="Rango de referencia",
        encabezados=["Macronutriente", "Gramos por kilo", "Ella"],
        filas=[
            Fila(
                [ROTULO_MACRO[m], f"{RANGO_GKG[m][0]} a {RANGO_GKG[m][1]}", _n(gkg[m])],
                # Las tres filas son suyas: lo que cambia es si su número cae dentro.
                fuera=not (RANGO_GKG[m][0] <= gkg[m] <= RANGO_GKG[m][1]),
            )
            for m in ("carbohidrato", "proteina", "grasa")
        ],
        nota="Señaladas, las que se salen del rango.",
    )


def _tabla_de_base_de_proteina(
    base: BaseProteina, gkg: dict[str, Decimal], por_peso: Decimal
) -> Tabla:
    return Tabla(
        titulo="Base del cálculo de proteína",
        encabezados=["Base", "Gramos por kilo"],
        filas=[
            Fila(
                [ROTULO_BASE_PROTEINA[BaseProteina.PESO_TOTAL], _n(por_peso, 4)],
                suya=base is BaseProteina.PESO_TOTAL,
            ),
            Fila(
                [ROTULO_BASE_PROTEINA[BaseProteina.MASA_LIBRE_DE_GRASA], _n(gkg["proteina"], 4)],
                suya=base is BaseProteina.MASA_LIBRE_DE_GRASA,
            ),
        ],
    )


def _tabla_de_refeeds(dia_bajo: Decimal, dias: int) -> Tabla:
    """Qué déficit promedio deja la semana según cuántos días de refeed lleve."""
    return Tabla(
        titulo="Refeeds",
        encabezados=["Días de refeed", "Porcentaje promedio"],
        filas=[
            Fila([rotulo, _pct(deficit_promedio_semanal(dia_bajo, n) / 100, 4)], suya=n == dias)
            for n, rotulo in ((0, "Ninguno"), (1, "Un día"), (2, "Dos días"))
        ],
        nota=f"Con el día bajo al {_pct(dia_bajo / 100, 0)}.",
    )


def _tabla_de_tmb(sexo: Sexo) -> Tabla:
    """Se compara contra el enumerado y no contra el rótulo: el texto es de presentación y
    cualquier día pasa a decir «Mujer», que también empieza por eme."""
    return Tabla(
        titulo="Ecuación de la tasa metabólica basal",
        encabezados=["Género", "Fórmula"],
        filas=[
            Fila(
                ["Masculino", "13.587·MLG + 9.613·MG + 198 − 3.351·edad + 674"],
                suya=sexo is Sexo.MASCULINO,
            ),
            Fila(
                ["Femenino", "13.587·MLG + 9.613·MG + 198·0 − 3.351·edad + 674"],
                suya=sexo is Sexo.FEMENINO,
            ),
        ],
        nota="En femenino el 198 se multiplica por cero: son 198 kcal exactos de diferencia.",
    )


def _tabla_de_volumen(
    comp: Composicion,
    energia_calculada: Energia,
    semanas: int,
    relacion: RelacionGanancia,
) -> Tabla:
    """Las dos relaciones en paralelo. Son dos apuestas sobre cuánto de lo que sube es
    músculo, y se deciden comparándolas, no alternando entre ellas.

    Se arma también en déficit, y entonces sale en negativo: es lo que hace la hoja, y una
    tabla de consulta que desaparece justo cuando la alumna está bajando no se consulta
    nunca. La nota dice lo que significan esos números para que no se lean como promesa.
    """
    ajuste = dict(exigir_superavit=False)
    dos = proyectar_ganancia(comp, energia_calculada, semanas, RelacionGanancia.DOS_A_UNO, **ajuste)
    uno = proyectar_ganancia(comp, energia_calculada, semanas, RelacionGanancia.UNO_A_UNO, **ajuste)
    ambas = f"{_n(dos.aumento_semanal_kg, 2)} kg"
    return Tabla(
        titulo="Proyección de aumento de músculo",
        encabezados=["Concepto", "Relación 2:1", "Relación 1:1"],
        filas=[
            Fila(["Aumento de peso semanal", ambas, ""]),
            Fila(
                [
                    "Aumento de músculo semanal",
                    f"{_n(dos.musculo_semanal_kg, 2)} kg",
                    f"{_n(uno.musculo_semanal_kg, 2)} kg",
                ]
            ),
            Fila(["Porcentaje de aumento mensual", _pct(dos.porcentaje_mensual), ""]),
            Fila(["Semanas de aumento de peso", _n(semanas, 0), ""]),
            Fila(["Aumento de peso total", f"{_n(dos.aumento_total_kg)} kg", ""]),
            Fila(
                [
                    "Aumento de músculo total",
                    f"{_n(dos.musculo_total_kg)} kg",
                    f"{_n(uno.musculo_total_kg)} kg",
                ]
            ),
            Fila(
                [
                    "Aumento de grasa total",
                    f"{_n(dos.grasa_total_kg)} kg",
                    f"{_n(uno.grasa_total_kg)} kg",
                ]
            ),
        ],
        nota=(
            "Las filas de un solo valor no dependen de la relación."
            if not energia_calculada.es_deficit
            else "Su ajuste es déficit: en negativo, lo que perdería a este ritmo."
        ),
        columna_suya=1 if relacion is RelacionGanancia.DOS_A_UNO else 2,
    )


def _tabla_de_constantes() -> Tabla:
    return Tabla(
        titulo="Constantes",
        encabezados=["Concepto", "Valor"],
        filas=[
            Fila(["Efecto térmico de los alimentos", "×1.1"]),
            Fila(["Kilocalorías por kilo de peso ganado", _n(KCAL_POR_KILO_GANADO, 0)]),
            Fila(["Grasa pura en lo que se baja", "87 %"]),
            Fila(["Masa libre de grasa que se pierde", "20 %"]),
            Fila(
                [
                    "Parte que es músculo, relación 2:1",
                    _pct(PROPORCION_MUSCULO[RelacionGanancia.DOS_A_UNO], 0),
                ]
            ),
            Fila(
                [
                    "Parte que es músculo, relación 1:1",
                    _pct(PROPORCION_MUSCULO[RelacionGanancia.UNO_A_UNO], 0),
                ]
            ),
        ],
    )


def construir(
    *,
    alumna: str,
    edad: int,
    sexo: Sexo,
    prescripcion: Prescripcion,
    actividad: NivelActividad,
    porcentaje_ajuste: Decimal,
    base_proteina: BaseProteina,
    dia_bajo: Decimal,
    dias_refeed: int,
    perdida: ProyeccionPerdida | None,
    ganancia: ProyeccionGanancia | None,
    relacion_ganancia: RelacionGanancia = RelacionGanancia.DOS_A_UNO,
    semanas_ganancia: int = 20,
) -> Hoja:
    """Arma la hoja completa. Los bloques sin datos se omiten en lugar de salir vacíos."""
    bloques = [
        _datos(
            prescripcion.composicion,
            edad,
            ROTULO_SEXO[sexo],
            prescripcion,
            porcentaje_ajuste,
            actividad,
        ),
        _macros(prescripcion.macros, prescripcion.gramos_por_kilo, base_proteina),
        _refeeds(dia_bajo, dias_refeed, prescripcion.deficit_promedio_semanal),
    ]
    if perdida is not None:
        bloques.append(_perdida(perdida))
    if ganancia is not None:
        bloques.append(_ganancia(ganancia))

    comp = prescripcion.composicion
    gkg = prescripcion.gramos_por_kilo
    tablas = [
        _tabla_de_actividad(actividad),
        _tabla_de_rangos(gkg),
        _tabla_de_base_de_proteina(
            base_proteina, gkg, prescripcion.macros.proteina_g / comp.peso_kg
        ),
        _tabla_de_refeeds(dia_bajo, dias_refeed),
        _tabla_de_tmb(sexo),
    ]
    # Va siempre, también en déficit: es una tabla de consulta, y la que desaparece justo
    # cuando la alumna está bajando es la que nunca se llega a consultar.
    tablas.append(
        _tabla_de_volumen(
            comp,
            prescripcion.energia,
            ganancia.semanas if ganancia is not None else semanas_ganancia,
            relacion_ganancia,
        )
    )
    tablas.append(_tabla_de_constantes())

    return Hoja(
        alumna=alumna,
        bloques=bloques,
        tablas=tablas,
        escala_imc=_escala_de_imc(comp.imc),
    )


__all__ = ["Bloque", "Celda", "Hoja", "Tabla", "construir"]
