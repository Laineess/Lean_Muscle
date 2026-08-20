"""Calculadora metabólica: el método de la coach, traducido de `Calculadora del Fitness.xlsm`.

Las fórmulas y sus coeficientes se preservan exactos —cambiar un número aquí cambia el plan
de todas sus alumnas— y cada constante dice de qué dato sale. Módulo puro.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.compartido.errores import Codigo, ErrorDeDominio

CERO = Decimal(0)
UNO = Decimal(1)


def _r(valor: Decimal, decimales: int = 1) -> Decimal:
    return valor.quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Entradas
# ---------------------------------------------------------------------------


class Sexo(StrEnum):
    MASCULINO = "masculino"
    FEMENINO = "femenino"


class NivelActividad(StrEnum):
    """Nivel de actividad que elige la coach. El valor es su multiplicador."""

    MUY_POCO_ACTIVO = "muy_poco_activo"
    POCO_ACTIVO = "poco_activo"
    ACTIVO = "activo"
    MUY_ACTIVO = "muy_activo"
    INTENSO = "intenso"
    MUY_INTENSO = "muy_intenso"
    ATLETA = "atleta"
    ATLETA_ELITE = "atleta_elite"


#: Multiplicador con el que se pasa de tasa basal a mantenimiento. La hoja nombra los cuatro
#: primeros; del 1.6 al 1.9 solo trae el número, así que aquí se les puso nombre.
MULTIPLICADOR: dict[NivelActividad, Decimal] = {
    NivelActividad.MUY_POCO_ACTIVO: Decimal("1.2"),
    NivelActividad.POCO_ACTIVO: Decimal("1.3"),
    NivelActividad.ACTIVO: Decimal("1.4"),
    NivelActividad.MUY_ACTIVO: Decimal("1.5"),
    NivelActividad.INTENSO: Decimal("1.6"),
    NivelActividad.MUY_INTENSO: Decimal("1.7"),
    NivelActividad.ATLETA: Decimal("1.8"),
    NivelActividad.ATLETA_ELITE: Decimal("1.9"),
}


class BaseProteina(StrEnum):
    """Contra qué peso se expresa la proteína en g/kg."""

    PESO_TOTAL = "peso_total"
    MASA_LIBRE_DE_GRASA = "masa_libre_de_grasa"


class RelacionGanancia(StrEnum):
    """Cuánto del peso ganado se espera que sea músculo."""

    DOS_A_UNO = "2:1"
    UNO_A_UNO = "1:1"


PROPORCION_MUSCULO: dict[RelacionGanancia, Decimal] = {
    RelacionGanancia.DOS_A_UNO: Decimal("0.33"),
    RelacionGanancia.UNO_A_UNO: Decimal("0.50"),
}


# ---------------------------------------------------------------------------
# Constantes de la hoja
# ---------------------------------------------------------------------------

#: Ecuación de tasa metabólica basal:
#: TMB = 13.587·MLG + 9.613·MG + 198·(1 si hombre) − 3.351·edad + 674
COEF_MLG = Decimal("13.587")
COEF_MG = Decimal("9.613")
COEF_SEXO_MASCULINO = Decimal("198")
COEF_EDAD = Decimal("3.351")
COEF_BASE = Decimal("674")

#: Mantenimiento = TMB × actividad × 1.1. El 1.1 es el efecto térmico de los alimentos, que
#: la hoja aplica plano en lugar de calcularlo por macro.
FACTOR_TERMICO = Decimal("1.1")

#: Atwater: 4 kcal/g en proteína y carbohidrato, 9 en grasa.
KCAL_POR_GRAMO: dict[str, Decimal] = {
    "carbohidrato": Decimal(4),
    "proteina": Decimal(4),
    "grasa": Decimal(9),
}

GRAMOS_POR_KILO = Decimal(1000)

#: Composición del peso que se pierde.
FRACCION_GRASA_PURA = Decimal("0.87")  # de cada kg de grasa perdida, 87 % es grasa pura
FRACCION_MLG_PERDIDA = Decimal("0.20")  # por cada kg de grasa se pierde 0.2 kg de MLG
FRACCION_PROTEINA_EN_MLG = Decimal("0.30")

#: Cómo se reparte el peso que se baja, en la «regla del cuarto»: tres cuartas partes salen de
#: la grasa y una cuarta parte, de la masa magra.
FRACCION_GRASA_EN_LO_PERDIDO = Decimal("0.75")
FRACCION_MLG_EN_LO_PERDIDO = Decimal("0.25")

#: Kcal de superávit por kilo de peso ganado.
KCAL_POR_KILO_GANADO = Decimal("8400")

#: Reducción semanal recomendada, entre 0.5 % y 1.0 % del peso.
REDUCCION_SEMANAL_MIN = Decimal("0.005")
REDUCCION_SEMANAL_MAX = Decimal("0.010")

#: Rangos de referencia en g/kg. Fuera de esto la pantalla avisa.
RANGO_GKG: dict[str, tuple[Decimal, Decimal]] = {
    "carbohidrato": (Decimal("2.0"), Decimal("5.0")),
    "proteina": (Decimal("1.8"), Decimal("3.0")),
    "grasa": (Decimal("0.5"), Decimal("1.5")),
}

#: Clasificación de IMC. La hoja la tabula de 16 a 35; abajo de 16 no devuelve nada y aquí,
#: «Muy delgado».
ESCALA_IMC: tuple[tuple[Decimal, str], ...] = (
    (Decimal(18), "Muy delgado"),
    (Decimal(21), "Delgado"),
    (Decimal(26), "Normal"),
    (Decimal(30), "Sobre peso"),
)


def clasificar_imc(imc: Decimal) -> str:
    for tope, etiqueta in ESCALA_IMC:
        if imc < tope:
            return etiqueta
    return "Obesidad"


# ---------------------------------------------------------------------------
# Composición corporal
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Composicion:
    """Lo que se deriva del peso y del porcentaje de grasa."""

    peso_kg: Decimal
    porcentaje_grasa: Decimal
    """Fracción, no porcentaje: 0.30 = 30 %."""

    estatura_cm: int

    @property
    def masa_grasa_kg(self) -> Decimal:
        """Peso por porcentaje de grasa."""
        return self.peso_kg * self.porcentaje_grasa

    @property
    def masa_libre_de_grasa_kg(self) -> Decimal:
        """Peso menos masa grasa."""
        return self.peso_kg - self.masa_grasa_kg

    @property
    def imc(self) -> Decimal:
        """Peso entre estatura en metros al cuadrado."""
        metros = Decimal(self.estatura_cm) / Decimal(100)
        return self.peso_kg / (metros * metros)

    @property
    def clasificacion_imc(self) -> str:
        return clasificar_imc(self.imc)

    @property
    def peso_ideal_broca_kg(self) -> Decimal:
        """Fórmula de Broca: estatura en cm menos 100."""
        return Decimal(self.estatura_cm) - Decimal(100)

    @property
    def diferencia_peso_estatura_kg(self) -> Decimal:
        """Peso actual menos peso ideal de Broca."""
        return self.peso_kg - self.peso_ideal_broca_kg


def tasa_metabolica_basal(comp: Composicion, sexo: Sexo, edad: int) -> Decimal:
    """La única diferencia por sexo es el término de 198 kcal, que la fórmula femenina
    multiplica por cero."""
    termino_sexo = COEF_SEXO_MASCULINO if sexo is Sexo.MASCULINO else CERO
    return (
        COEF_MLG * comp.masa_libre_de_grasa_kg
        + COEF_MG * comp.masa_grasa_kg
        + termino_sexo
        - COEF_EDAD * Decimal(edad)
        + COEF_BASE
    )


# ---------------------------------------------------------------------------
# Energía y macros
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RepartoMacros:
    """Fracciones de las calorías que va a cada macro. Deben sumar exactamente 1."""

    carbohidrato: Decimal
    proteina: Decimal
    grasa: Decimal

    def __post_init__(self) -> None:
        total = self.carbohidrato + self.proteina + self.grasa
        if total != UNO:
            raise ErrorDeDominio(
                Codigo.REPARTO_DE_MACROS_NO_SUMA_UNO,
                total=str(_r(total * Decimal(100), 2)),
            )


@dataclass(frozen=True, slots=True)
class Energia:
    mantenimiento_kcal: Decimal
    ajustadas_kcal: Decimal
    ajuste_diario_kcal: Decimal
    ajuste_semanal_kcal: Decimal
    semanales_kcal: Decimal

    @property
    def es_deficit(self) -> bool:
        return self.ajuste_diario_kcal < 0


def energia(tmb: Decimal, actividad: NivelActividad, porcentaje_ajuste: Decimal) -> Energia:
    """De mantenimiento a calorías ajustadas. `porcentaje_ajuste` va con signo: −0.28 es un
    déficit del 28 %."""
    mantenimiento = tmb * MULTIPLICADOR[actividad] * FACTOR_TERMICO
    ajustadas = mantenimiento + mantenimiento * porcentaje_ajuste
    diario = ajustadas - mantenimiento
    return Energia(
        mantenimiento_kcal=mantenimiento,
        ajustadas_kcal=ajustadas,
        ajuste_diario_kcal=diario,
        ajuste_semanal_kcal=diario * 7,
        semanales_kcal=ajustadas * 7,
    )


@dataclass(frozen=True, slots=True)
class Macros:
    carbohidrato_g: Decimal
    proteina_g: Decimal
    grasa_g: Decimal

    def kcal(self) -> Decimal:
        return (
            self.carbohidrato_g * KCAL_POR_GRAMO["carbohidrato"]
            + self.proteina_g * KCAL_POR_GRAMO["proteina"]
            + self.grasa_g * KCAL_POR_GRAMO["grasa"]
        )

    def redondeados(self) -> Macros:
        return Macros(_r(self.carbohidrato_g, 0), _r(self.proteina_g, 0), _r(self.grasa_g, 0))


def macros(kcal_ajustadas: Decimal, reparto: RepartoMacros) -> Macros:
    """Calorías ajustadas por el porcentaje de cada macro, entre sus kcal por gramo."""
    return Macros(
        carbohidrato_g=kcal_ajustadas * reparto.carbohidrato / KCAL_POR_GRAMO["carbohidrato"],
        proteina_g=kcal_ajustadas * reparto.proteina / KCAL_POR_GRAMO["proteina"],
        grasa_g=kcal_ajustadas * reparto.grasa / KCAL_POR_GRAMO["grasa"],
    )


def gramos_por_kilo(
    macros_calculados: Macros, comp: Composicion, base_proteina: BaseProteina
) -> dict[str, Decimal]:
    """Carbohidrato y grasa van contra el peso total; la proteína, contra lo que elija la
    coach."""
    referencia_proteina = (
        comp.peso_kg if base_proteina is BaseProteina.PESO_TOTAL else comp.masa_libre_de_grasa_kg
    )
    return {
        "carbohidrato": macros_calculados.carbohidrato_g / comp.peso_kg,
        "proteina": macros_calculados.proteina_g / referencia_proteina,
        "grasa": macros_calculados.grasa_g / comp.peso_kg,
    }


def fuera_de_rango(gkg: dict[str, Decimal]) -> dict[str, tuple[Decimal, Decimal]]:
    """Qué macros salen de los rangos de referencia de la hoja. Avisa, no bloquea."""
    salidos: dict[str, tuple[Decimal, Decimal]] = {}
    for macro, valor in gkg.items():
        minimo, maximo = RANGO_GKG[macro]
        if not (minimo <= valor <= maximo):
            salidos[macro] = (minimo, maximo)
    return salidos


# ---------------------------------------------------------------------------
# Refeeds
# ---------------------------------------------------------------------------

#: El día de refeed va a mantenimiento. Es el valor por defecto de la hoja y la coach puede
#: cambiarlo.
DEFICIT_DIA_REFEED_POR_DEFECTO = CERO

MAX_DIAS_REFEED = 2


def deficit_promedio_semanal(
    porcentaje_dia_bajo: Decimal,
    dias_refeed: int,
    porcentaje_dia_refeed: Decimal = DEFICIT_DIA_REFEED_POR_DEFECTO,
) -> Decimal:
    """Es el número que manda sobre el resultado, no el del día bajo: con un refeed y 26 %
    los otros seis días, el promedio queda en 22.29 %.

    La hoja suma el déficit del día de refeed una sola vez aunque sean dos días; aquí se
    suma por cada día. Con el refeed a mantenimiento, que es lo normal, da lo mismo.
    """
    if not 0 <= dias_refeed <= MAX_DIAS_REFEED:
        raise ErrorDeDominio(
            Codigo.DIAS_DE_REFEED_FUERA_DE_RANGO, dias=dias_refeed, maximo=MAX_DIAS_REFEED
        )
    dias_bajos = 7 - dias_refeed
    total = porcentaje_dia_bajo * Decimal(dias_bajos) + porcentaje_dia_refeed * Decimal(dias_refeed)
    return total / Decimal(7)


# ---------------------------------------------------------------------------
# Déficit recomendado
# ---------------------------------------------------------------------------


def energia_por_kilo_perdido() -> Decimal:
    """Kcal que hay en un kilo de peso bajado, unas 6 172.

    De cada kilo, 750 g salen de la grasa —y el tejido graso es 87 % lípido, a 9 kcal/g— y
    250 g de masa magra, que es 30 % proteína a 4 kcal/g. Los 0.87 × 9 000 son de dónde sale
    la cifra clásica de ~7 700 kcal por kilo de grasa.
    """
    grasa = FRACCION_GRASA_EN_LO_PERDIDO * FRACCION_GRASA_PURA * KCAL_POR_GRAMO["grasa"]
    proteina = FRACCION_MLG_EN_LO_PERDIDO * FRACCION_PROTEINA_EN_MLG * KCAL_POR_GRAMO["proteina"]
    return (grasa + proteina) * GRAMOS_POR_KILO


@dataclass(frozen=True, slots=True)
class DeficitRecomendado:
    """El déficit diario que hace falta para bajar al ritmo sano."""

    minimo_kcal: Decimal
    maximo_kcal: Decimal
    kcal_por_kilo: Decimal

    def contiene(self, deficit_diario_kcal: Decimal) -> bool:
        return self.minimo_kcal <= deficit_diario_kcal <= self.maximo_kcal


def deficit_recomendado(comp: Composicion) -> DeficitRecomendado:
    """Es el inverso del ritmo recomendado: de 0.5 % a 1 % del peso por semana, en kcal al día.

    Reconstruye la tabla «Déficit recomendado» de la hoja, que quedó en #REF! cuando alguien
    borró la columna de la que colgaba. Del original sobrevivió `× 0.75 × 0.87 × 9 / 7`, que
    es la parte de la grasa; la de la proteína estaba a medias.
    """
    por_dia = comp.peso_kg * energia_por_kilo_perdido() / Decimal(7)
    return DeficitRecomendado(
        minimo_kcal=por_dia * REDUCCION_SEMANAL_MIN,
        maximo_kcal=por_dia * REDUCCION_SEMANAL_MAX,
        kcal_por_kilo=energia_por_kilo_perdido(),
    )


# ---------------------------------------------------------------------------
# Proyecciones
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProyeccionPerdida:
    """**Solo la ve la coach**: asume adherencia perfecta, y enseñarle una fecha exacta a la
    alumna convierte una estimación en una promesa."""

    kg_grasa_por_bajar: Decimal
    kg_mlg_que_se_pierden: Decimal
    kg_totales_por_bajar: Decimal
    kcal_totales: Decimal
    perdida_semanal_kg: Decimal
    porcentaje_semanal: Decimal
    dias_estimados: Decimal
    recomendado_semanal_min_kg: Decimal
    recomendado_semanal_max_kg: Decimal

    @property
    def dentro_de_lo_recomendado(self) -> bool:
        return (
            self.recomendado_semanal_min_kg
            <= self.perdida_semanal_kg
            <= self.recomendado_semanal_max_kg
        )


def proyectar_perdida(
    comp: Composicion, porcentaje_grasa_objetivo: Decimal, energia_calculada: Energia
) -> ProyeccionPerdida:
    """No todo lo perdido es grasa: por cada kilo se van 0.2 kg de masa libre de grasa, y de
    esos el 30 % es proteína."""
    if not energia_calculada.es_deficit:
        raise ErrorDeDominio(Codigo.PROYECCION_SIN_DEFICIT)
    if porcentaje_grasa_objetivo >= comp.porcentaje_grasa:
        raise ErrorDeDominio(
            Codigo.OBJETIVO_DE_GRASA_NO_ES_MENOR,
            actual=str(_r(comp.porcentaje_grasa * Decimal(100))),
            objetivo=str(_r(porcentaje_grasa_objetivo * Decimal(100))),
        )

    masa_grasa = comp.masa_grasa_kg
    # Cuánta grasa quedaría al llegar al objetivo, manteniendo la MLG actual.
    grasa_en_objetivo = porcentaje_grasa_objetivo * masa_grasa / comp.porcentaje_grasa
    grasa_por_bajar = masa_grasa - grasa_en_objetivo

    grasa_pura = grasa_por_bajar * FRACCION_GRASA_PURA
    mlg_perdida = grasa_por_bajar * FRACCION_MLG_PERDIDA
    proteina_pura = mlg_perdida * FRACCION_PROTEINA_EN_MLG

    totales = grasa_por_bajar + mlg_perdida
    kcal_totales = (
        grasa_pura * KCAL_POR_GRAMO["grasa"] + proteina_pura * KCAL_POR_GRAMO["proteina"]
    ) * Decimal(1000)

    deficit_diario = -energia_calculada.ajuste_diario_kcal
    deficit_semanal = -energia_calculada.ajuste_semanal_kcal

    perdida_semanal = deficit_semanal * totales / kcal_totales

    return ProyeccionPerdida(
        kg_grasa_por_bajar=grasa_por_bajar,
        kg_mlg_que_se_pierden=mlg_perdida,
        kg_totales_por_bajar=totales,
        kcal_totales=kcal_totales,
        perdida_semanal_kg=perdida_semanal,
        porcentaje_semanal=perdida_semanal / comp.peso_kg,
        dias_estimados=kcal_totales / deficit_diario,
        recomendado_semanal_min_kg=comp.peso_kg * REDUCCION_SEMANAL_MIN,
        recomendado_semanal_max_kg=comp.peso_kg * REDUCCION_SEMANAL_MAX,
    )


@dataclass(frozen=True, slots=True)
class ProyeccionGanancia:
    """Etapa de volumen. También solo para la coach."""

    aumento_semanal_kg: Decimal
    musculo_semanal_kg: Decimal
    porcentaje_mensual: Decimal
    semanas: int
    aumento_total_kg: Decimal
    musculo_total_kg: Decimal
    grasa_total_kg: Decimal


def proyectar_ganancia(
    comp: Composicion,
    energia_calculada: Energia,
    semanas: int,
    relacion: RelacionGanancia = RelacionGanancia.DOS_A_UNO,
    *,
    exigir_superavit: bool = True,
) -> ProyeccionGanancia:
    """Con `exigir_superavit` en falso devuelve la cuenta aunque el ajuste sea déficit, y
    entonces sale en negativo.

    Eso no es una proyección: es la tabla de consulta, que se lee para comparar las dos
    relaciones aunque hoy la alumna esté bajando. Quien prometa un resultado a alguien tiene
    que dejar la guarda puesta.
    """
    if exigir_superavit and energia_calculada.es_deficit:
        raise ErrorDeDominio(Codigo.PROYECCION_SIN_SUPERAVIT)

    aumento_semanal = energia_calculada.ajuste_semanal_kcal / KCAL_POR_KILO_GANADO
    musculo_semanal = aumento_semanal * PROPORCION_MUSCULO[relacion]
    total = aumento_semanal * Decimal(semanas)
    musculo_total = musculo_semanal * Decimal(semanas)

    return ProyeccionGanancia(
        aumento_semanal_kg=aumento_semanal,
        musculo_semanal_kg=musculo_semanal,
        porcentaje_mensual=aumento_semanal / comp.peso_kg * Decimal(4),
        semanas=semanas,
        aumento_total_kg=total,
        musculo_total_kg=musculo_total,
        grasa_total_kg=total - musculo_total,
    )


# ---------------------------------------------------------------------------
# Fachada
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Prescripcion:
    """Todo lo que la calculadora entrega al constructor de planes."""

    composicion: Composicion
    tmb_kcal: Decimal
    energia: Energia
    macros: Macros
    gramos_por_kilo: dict[str, Decimal]
    avisos_de_rango: dict[str, tuple[Decimal, Decimal]]
    deficit_promedio_semanal: Decimal | None
    deficit_recomendado: DeficitRecomendado


def calcular(
    *,
    peso_kg: Decimal,
    porcentaje_grasa: Decimal,
    estatura_cm: int,
    edad: int,
    sexo: Sexo,
    actividad: NivelActividad,
    porcentaje_ajuste: Decimal,
    reparto: RepartoMacros,
    base_proteina: BaseProteina = BaseProteina.MASA_LIBRE_DE_GRASA,
    dias_refeed: int = 0,
    porcentaje_dia_refeed: Decimal = DEFICIT_DIA_REFEED_POR_DEFECTO,
) -> Prescripcion:
    """Recorrido completo de la hoja, de los datos de la alumna a los gramos del plan."""
    if not (CERO < porcentaje_grasa < UNO):
        raise ErrorDeDominio(Codigo.PORCENTAJE_DE_GRASA_INVALIDO, valor=str(porcentaje_grasa))

    comp = Composicion(peso_kg=peso_kg, porcentaje_grasa=porcentaje_grasa, estatura_cm=estatura_cm)
    tmb = tasa_metabolica_basal(comp, sexo, edad)
    ener = energia(tmb, actividad, porcentaje_ajuste)
    macros_calculados = macros(ener.ajustadas_kcal, reparto)
    gkg = gramos_por_kilo(macros_calculados, comp, base_proteina)

    promedio = (
        deficit_promedio_semanal(abs(porcentaje_ajuste), dias_refeed, porcentaje_dia_refeed)
        if dias_refeed
        else None
    )

    return Prescripcion(
        composicion=comp,
        tmb_kcal=tmb,
        energia=ener,
        macros=macros_calculados,
        gramos_por_kilo=gkg,
        avisos_de_rango=fuera_de_rango(gkg),
        deficit_promedio_semanal=promedio,
        deficit_recomendado=deficit_recomendado(comp),
    )
