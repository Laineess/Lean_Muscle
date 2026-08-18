"""Derechos ARCO: qué se pidió, cuándo vence y en qué estado va.

Los plazos son de la LFPDPPP: 20 días hábiles para contestar y 15 hábiles más para
ejecutar. Se cuentan en hábiles, no naturales, así que la cuenta no es una resta.

Módulo puro: decide, no guarda.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

#: Días hábiles desde que se recibe hasta que hay que contestar.
PLAZO_RESPUESTA = 20

#: Días hábiles más, ya contestada, para ejecutar lo que se prometió.
PLAZO_EJECUCION = 15

#: Cuando faltan estos días o menos, urge.
UMBRAL_DE_AVISO = 5


class Derecho(StrEnum):
    ACCESO = "A"
    RECTIFICACION = "R"
    CANCELACION = "C"
    OPOSICION = "O"


class Estado(StrEnum):
    RECIBIDA = "recibida"
    RESPONDIDA = "respondida"
    RESUELTA = "resuelta"


ROTULO: dict[Derecho, str] = {
    Derecho.ACCESO: "Acceso",
    Derecho.RECTIFICACION: "Rectificación",
    Derecho.CANCELACION: "Cancelación",
    Derecho.OPOSICION: "Oposición",
}


def sumar_habiles(desde: date, habiles: int) -> date:
    """Sábados y domingos no cuentan. Los feriados oficiales sí, y eso juega en contra
    nuestra: el plazo real es algo más largo, nunca más corto."""
    dia = desde
    restantes = habiles
    while restantes > 0:
        dia += timedelta(days=1)
        if dia.weekday() < 5:
            restantes -= 1
    return dia


@dataclass(frozen=True, slots=True)
class Plazo:
    vence_el: date
    dias_restantes: int

    @property
    def vencido(self) -> bool:
        return self.dias_restantes < 0

    @property
    def urge(self) -> bool:
        return not self.vencido and self.dias_restantes <= UMBRAL_DE_AVISO


def plazo_de(estado: Estado, recibida_el: date, respondida_el: date | None, hoy: date) -> Plazo | None:
    """Qué fecha manda ahora. Una solicitud resuelta ya no tiene plazo que correr."""
    if estado is Estado.RESUELTA:
        return None
    if estado is Estado.RECIBIDA:
        vence = sumar_habiles(recibida_el, PLAZO_RESPUESTA)
    else:
        base = respondida_el or recibida_el
        vence = sumar_habiles(base, PLAZO_EJECUCION)
    return Plazo(vence_el=vence, dias_restantes=(vence - hoy).days)


def siguiente(estado: Estado) -> Estado:
    """Recibida → respondida → resuelta. No hay vuelta atrás."""
    return {Estado.RECIBIDA: Estado.RESPONDIDA, Estado.RESPONDIDA: Estado.RESUELTA}.get(
        estado, Estado.RESUELTA
    )
