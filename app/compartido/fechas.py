"""Fechas y horas.

Regla del proyecto: **todo se guarda en UTC** y se convierte al presentar. La unica
excepcion es `chequeo.fecha`, que es un `date` a proposito porque la regla de negocio
habla de dia calendario, no de instante.

El dia calendario del chequeo se evalua en la zona horaria de la coach, no en la del
servidor: una alumna en Tijuana y su coach en Merida no comparten medianoche.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

ZONA_POR_DEFECTO = "America/Mexico_City"


def ahora_utc() -> datetime:
    return datetime.now(tz=UTC)


def a_utc(momento: datetime) -> datetime:
    """Normaliza a UTC. Un datetime sin zona se considera ya en UTC."""
    if momento.tzinfo is None:
        return momento.replace(tzinfo=UTC)
    return momento.astimezone(UTC)


def dia_calendario(momento: datetime, zona: str = ZONA_POR_DEFECTO) -> date:
    """Dia calendario de `momento` visto desde `zona`."""
    return a_utc(momento).astimezone(ZoneInfo(zona)).date()


def mismo_dia_calendario(a: datetime, b: datetime, zona: str = ZONA_POR_DEFECTO) -> bool:
    return dia_calendario(a, zona) == dia_calendario(b, zona)


def edad_en(nacimiento: date, referencia: date) -> int:
    """Edad cumplida en anios."""
    cumplio = (referencia.month, referencia.day) >= (nacimiento.month, nacimiento.day)
    return referencia.year - nacimiento.year - (0 if cumplio else 1)
