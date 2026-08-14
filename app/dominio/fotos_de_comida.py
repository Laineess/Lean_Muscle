"""Cada cuanto le toca mandar fotos, y cuanto duran.

Dos reglas y ninguna es negociable desde la interfaz. La frecuencia la elige la coach al
armar el plan de nutricion; la vigencia no la elige nadie.

**36 horas.** Es lo unico que hace razonable pedirle a alguien que fotografie lo que come:
la foto sirve para que su coach la mire esta semana, no para quedarse. Que la ventana sea
corta y fija es parte del trato, no un ajuste.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

#: Lo que vive una foto de comida desde que se sube.
VIGENCIA = timedelta(hours=36)


class Frecuencia(StrEnum):
    """Cada cuanto se le piden fotos. `NINGUNA` es el valor de fabrica: si la coach no lo
    pide, a la alumna no se le pide nada."""

    NINGUNA = "ninguna"
    DIARIA = "diaria"
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"


#: Cada cuantos dias toca. `NINGUNA` no aparece: no tiene periodo.
DIAS: dict[Frecuencia, int] = {
    Frecuencia.DIARIA: 1,
    Frecuencia.SEMANAL: 7,
    Frecuencia.QUINCENAL: 15,
    Frecuencia.MENSUAL: 30,
}

ROTULO: dict[Frecuencia, str] = {
    Frecuencia.NINGUNA: "No se piden",
    Frecuencia.DIARIA: "Todos los días",
    Frecuencia.SEMANAL: "Una vez por semana",
    Frecuencia.QUINCENAL: "Cada quince días",
    Frecuencia.MENSUAL: "Una vez al mes",
}


def vencida(subida_en: datetime, ahora: datetime) -> bool:
    """Si ya paso su ventana. Se pregunta en cada lectura, no solo al purgar: si el trabajo
    de borrado se cae, la foto tiene que dejar de verse igual."""
    return ahora - subida_en >= VIGENCIA


def expira_en(subida_en: datetime) -> datetime:
    return subida_en + VIGENCIA


@dataclass(frozen=True, slots=True)
class Pendiente:
    """Lo que le toca a la alumna en este periodo."""

    frecuencia: Frecuencia
    #: Primer dia del periodo en curso.
    desde: date
    #: Ultimo dia para mandarla.
    hasta: date
    #: Si ya mando al menos una dentro del periodo.
    cumplido: bool

    @property
    def dias_restantes(self) -> int:
        return (self.hasta - self.desde).days


def periodo(frecuencia: Frecuencia, referencia: date, hoy: date) -> tuple[date, date]:
    """Periodo en curso, contado desde `referencia` —el dia en que se publico el plan—.

    Se cuenta desde ahi y no desde el primero de mes para que la alumna a la que se le dio
    de alta un dia 20 no reciba su primer 'te toca' al dia siguiente.
    """
    dias = DIAS[frecuencia]
    transcurridos = max((hoy - referencia).days, 0)
    inicio = referencia + timedelta(days=(transcurridos // dias) * dias)
    return inicio, inicio + timedelta(days=dias - 1)


def estado(
    frecuencia: Frecuencia,
    referencia: date,
    hoy: date,
    fechas_enviadas: list[date],
) -> Pendiente | None:
    """Que le toca hoy. Nulo cuando la coach no pide fotos."""
    if frecuencia is Frecuencia.NINGUNA:
        return None

    desde, hasta = periodo(frecuencia, referencia, hoy)
    return Pendiente(
        frecuencia=frecuencia,
        desde=desde,
        hasta=hasta,
        cumplido=any(desde <= f <= hasta for f in fechas_enviadas),
    )
