"""Rangos antropometricos y varianzas de peso.

Fuente: Documento de Requerimientos v1.2, seccion 7.1 (diccionario de datos) y
seccion 11 (reglas de negocio). Modulo puro: no toca base de datos ni HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.compartido.errores import Codigo, ErrorDeDominio

UN_DECIMAL = Decimal("0.1")


class TipoMedida(StrEnum):
    """Los 8 perimetros del chequeo. La estatura no esta aqui: vive en el perfil de la alumna
    porque es un registro unico inicial (Requerimientos v1.2, seccion 9)."""

    CINTURA = "cintura"
    ABDOMEN = "abdomen"
    CADERA = "cadera"
    BUSTO = "busto"
    PECHO = "pecho"
    BRAZO = "brazo"
    MUSLO = "muslo"
    PANTORRILLA = "pantorrilla"


#: El chequeo no se envia con menos de estas 8. Junto con la estatura del perfil suman las
#: "9 medidas" que menciona el documento de requerimientos.
MEDIDAS_REQUERIDAS: frozenset[TipoMedida] = frozenset(TipoMedida)


@dataclass(frozen=True, slots=True)
class Rango:
    minimo: Decimal
    maximo: Decimal

    def contiene(self, valor: Decimal) -> bool:
        return self.minimo <= valor <= self.maximo


RANGO_PESO_KG = Rango(Decimal("30.0"), Decimal("250.0"))
RANGO_ESTATURA_CM = Rango(Decimal("100"), Decimal("250"))

RANGOS_MEDIDA_CM: dict[TipoMedida, Rango] = {
    TipoMedida.CINTURA: Rango(Decimal("40.0"), Decimal("200.0")),
    TipoMedida.ABDOMEN: Rango(Decimal("40.0"), Decimal("200.0")),
    TipoMedida.CADERA: Rango(Decimal("50.0"), Decimal("250.0")),
    TipoMedida.BUSTO: Rango(Decimal("50.0"), Decimal("200.0")),
    TipoMedida.PECHO: Rango(Decimal("50.0"), Decimal("200.0")),
    TipoMedida.BRAZO: Rango(Decimal("15.0"), Decimal("70.0")),
    TipoMedida.MUSLO: Rango(Decimal("30.0"), Decimal("100.0")),
    TipoMedida.PANTORRILLA: Rango(Decimal("15.0"), Decimal("70.0")),
}

#: Fuera de este margen el sistema pide confirmacion explicita a la alumna antes de cerrar.
MARGEN_VARIANZA_ALUMNA = Decimal("0.03")
#: Por encima de esto se levanta alerta para la coach; sobrescribirla exige justificacion.
MARGEN_VARIANZA_COACH = Decimal("0.10")


def redondear_1(valor: Decimal) -> Decimal:
    return valor.quantize(UN_DECIMAL, rounding=ROUND_HALF_UP)


def validar_peso(peso_kg: Decimal) -> Decimal:
    """Devuelve el peso normalizado a un decimal, o lanza si esta fuera de rango."""
    if peso_kg <= 0 or not RANGO_PESO_KG.contiene(peso_kg):
        raise ErrorDeDominio(
            Codigo.PESO_FUERA_DE_RANGO,
            valor=str(peso_kg),
            minimo=str(RANGO_PESO_KG.minimo),
            maximo=str(RANGO_PESO_KG.maximo),
        )
    return redondear_1(peso_kg)


def validar_estatura(estatura_cm: Decimal) -> int:
    if estatura_cm <= 0 or not RANGO_ESTATURA_CM.contiene(estatura_cm):
        raise ErrorDeDominio(
            Codigo.ESTATURA_FUERA_DE_RANGO,
            valor=str(estatura_cm),
            minimo=str(RANGO_ESTATURA_CM.minimo),
            maximo=str(RANGO_ESTATURA_CM.maximo),
        )
    return int(estatura_cm)


def validar_medida(tipo: TipoMedida, valor_cm: Decimal) -> Decimal:
    """Ninguna medida puede ser cero; el diccionario de datos lo prohibe explicitamente."""
    if valor_cm == 0:
        raise ErrorDeDominio(Codigo.MEDIDA_EN_CERO, tipo=tipo.value)
    rango = RANGOS_MEDIDA_CM[tipo]
    if valor_cm < 0 or not rango.contiene(valor_cm):
        raise ErrorDeDominio(
            Codigo.MEDIDA_FUERA_DE_RANGO,
            tipo=tipo.value,
            valor=str(valor_cm),
            minimo=str(rango.minimo),
            maximo=str(rango.maximo),
        )
    return redondear_1(valor_cm)


def faltantes(capturadas: set[TipoMedida]) -> frozenset[TipoMedida]:
    return frozenset(MEDIDAS_REQUERIDAS - capturadas)


class NivelVarianza(StrEnum):
    NORMAL = "normal"
    #: Fuera de +/-3 %: la alumna confirma el dato antes de cerrar el chequeo.
    CONFIRMA_ALUMNA = "confirma_alumna"
    #: Fuera de +/-10 %: ademas se levanta alerta para la coach.
    ALERTA_COACH = "alerta_coach"


@dataclass(frozen=True, slots=True)
class Varianza:
    nivel: NivelVarianza
    proporcion: Decimal
    """Peso actual / peso anterior. 1.0 = sin cambio."""

    @property
    def porcentaje(self) -> Decimal:
        return redondear_1((self.proporcion - Decimal(1)) * Decimal(100))


def evaluar_varianza(peso_actual: Decimal, peso_anterior: Decimal | None) -> Varianza:
    """Compara contra el chequeo anterior. Sin referencia previa no hay varianza que juzgar."""
    if peso_anterior is None or peso_anterior <= 0:
        return Varianza(NivelVarianza.NORMAL, Decimal(1))

    proporcion = peso_actual / peso_anterior
    desvio = abs(proporcion - Decimal(1))

    if desvio > MARGEN_VARIANZA_COACH:
        nivel = NivelVarianza.ALERTA_COACH
    elif desvio > MARGEN_VARIANZA_ALUMNA:
        nivel = NivelVarianza.CONFIRMA_ALUMNA
    else:
        nivel = NivelVarianza.NORMAL

    return Varianza(nivel, proporcion)


#: Cuantas fechas distintas de pesaje admite un ciclo (Requerimientos v1.2, Flujo Alternativo A).
MAX_PESAJES_POR_CICLO = 3


def promedio_de_pesajes(pesos_kg: list[Decimal]) -> Decimal:
    """Promedio de hasta 3 pesajes en ayunas de fechas distintas del ciclo.

    Reduce el ruido de una medicion atipica sin permitir repetir el peso el mismo dia:
    esa unicidad la impone la base con UNIQUE (alumna_id, fecha).
    """
    if not pesos_kg:
        raise ValueError("no hay pesajes que promediar")
    if len(pesos_kg) > MAX_PESAJES_POR_CICLO:
        raise ErrorDeDominio(
            Codigo.PESAJES_DEL_CICLO_AGOTADOS,
            capturados=len(pesos_kg),
            maximo=MAX_PESAJES_POR_CICLO,
        )
    return redondear_1(sum(pesos_kg, Decimal(0)) / Decimal(len(pesos_kg)))
