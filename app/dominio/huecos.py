"""Qué horas quedan libres para que una alumna reserve.

Sale de tres cosas: el horario que declaró la coach, lo que ya tiene ocupado y dos plazos
—no reservar sobre la hora ni a un año vista—. Es un cálculo, no una consulta: recibe la
agenda armada y responde.

Todo entra y sale en UTC. El horario se declara en la hora local de la coach, así que la
conversión ocurre aquí y en ningún otro sitio.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import a_utc
from app.dominio.agenda import Franja

#: Lunes es 0, como en `date.weekday()`.
DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")

#: Valores de fábrica. La coach los cambia en su pantalla de horario.
DURACION_POR_DEFECTO = 60
MARGEN_POR_DEFECTO = 15
ANTELACION_POR_DEFECTO = 24
HORIZONTE_POR_DEFECTO = 8

#: Topes de lo que se puede configurar, para que un dedazo no genere un año de huecos.
DURACION_MINIMA = 15
DURACION_MAXIMA = 240
MARGEN_MAXIMO = 120
ANTELACION_MAXIMA = 24 * 30
HORIZONTE_MAXIMO = 26


@dataclass(frozen=True, slots=True)
class Bloque:
    """Un tramo de atención de un día de la semana, en hora local de la coach."""

    dia: int
    desde: time
    hasta: time

    def __post_init__(self) -> None:
        if not 0 <= self.dia <= 6:
            raise ErrorDeDominio(Codigo.CATEGORIA_INVALIDA, categoria=str(self.dia), tipo="día")
        if self.desde >= self.hasta:
            raise ErrorDeDominio(
                Codigo.HORARIO_INVALIDO, desde=str(self.desde), hasta=str(self.hasta)
            )


@dataclass(frozen=True, slots=True)
class Reglas:
    """Cómo trocea la coach su horario y con cuánto aire quiere reservar."""

    duracion_min: int = DURACION_POR_DEFECTO
    margen_min: int = MARGEN_POR_DEFECTO
    antelacion_horas: int = ANTELACION_POR_DEFECTO
    horizonte_semanas: int = HORIZONTE_POR_DEFECTO

    def __post_init__(self) -> None:
        if not DURACION_MINIMA <= self.duracion_min <= DURACION_MAXIMA:
            raise ErrorDeDominio(Codigo.HORARIO_INVALIDO, desde="15", hasta="240")
        if not 0 <= self.margen_min <= MARGEN_MAXIMO:
            raise ErrorDeDominio(Codigo.HORARIO_INVALIDO, desde="0", hasta="120")
        if not 0 <= self.antelacion_horas <= ANTELACION_MAXIMA:
            raise ErrorDeDominio(Codigo.HORARIO_INVALIDO, desde="0", hasta=str(ANTELACION_MAXIMA))
        if not 1 <= self.horizonte_semanas <= HORIZONTE_MAXIMO:
            raise ErrorDeDominio(Codigo.HORARIO_INVALIDO, desde="1", hasta=str(HORIZONTE_MAXIMO))

    @property
    def paso(self) -> timedelta:
        """De cuánto en cuánto empieza una consulta: la duración más su respiro."""
        return timedelta(minutes=self.duracion_min + self.margen_min)

    @property
    def duracion(self) -> timedelta:
        return timedelta(minutes=self.duracion_min)


@dataclass(frozen=True, slots=True)
class Hueco:
    inicia_en: datetime
    termina_en: datetime


def revisar_horario(bloques: list[Bloque]) -> None:
    """Falla si dos tramos del mismo día se pisan.

    Encimados, la misma hora sale dos veces en la lista de la alumna: reserva una y la otra
    se queda ahí, ofreciendo un rato que ya no existe.
    """
    for i, a in enumerate(bloques):
        for b in bloques[i + 1 :]:
            if a.dia == b.dia and a.desde < b.hasta and b.desde < a.hasta:
                raise ErrorDeDominio(
                    Codigo.TRAMOS_ENCIMADOS,
                    dia=DIAS[a.dia],
                    desde=str(max(a.desde, b.desde)),
                    hasta=str(min(a.hasta, b.hasta)),
                )


def ventana(reglas: Reglas, ahora: datetime) -> tuple[datetime, datetime]:
    """Desde cuándo y hasta cuándo se puede reservar."""
    inicio = a_utc(ahora) + timedelta(hours=reglas.antelacion_horas)
    fin = a_utc(ahora) + timedelta(weeks=reglas.horizonte_semanas)
    return inicio, fin


def _choca(hueco: Hueco, ocupadas: list[Franja]) -> bool:
    """Se solapa con algo ya agendado. Un bloque de trabajo estorba igual que una consulta."""
    return any(
        hueco.inicia_en < f.termina_en and f.inicia_en < hueco.termina_en
        for f in ocupadas
        if f.ocupa
    )


def _del_dia(dia: date, bloques: list[Bloque], reglas: Reglas, zona: str) -> list[Hueco]:
    tz = ZoneInfo(zona)
    salida: list[Hueco] = []
    for bloque in (b for b in bloques if b.dia == dia.weekday()):
        cursor = datetime.combine(dia, bloque.desde, tzinfo=tz)
        cierre = datetime.combine(dia, bloque.hasta, tzinfo=tz)
        while cursor + reglas.duracion <= cierre:
            salida.append(
                Hueco(
                    inicia_en=a_utc(cursor),
                    termina_en=a_utc(cursor + reglas.duracion),
                )
            )
            cursor += reglas.paso
    return salida


def libres(
    bloques: list[Bloque],
    ocupadas: list[Franja],
    reglas: Reglas,
    zona: str,
    ahora: datetime,
    tope: int = 200,
) -> list[Hueco]:
    """Los huecos que la alumna puede tomar, del más cercano al más lejano.

    Se recorre día a día en la zona de la coach: su jornada es local aunque todo se guarde
    en UTC, y en un cambio de horario de verano las horas no se mueven solas.
    """
    if not bloques:
        return []

    desde, hasta = ventana(reglas, ahora)
    tz = ZoneInfo(zona)
    dia = desde.astimezone(tz).date()
    ultimo = hasta.astimezone(tz).date()

    salida: list[Hueco] = []
    while dia <= ultimo and len(salida) < tope:
        for hueco in _del_dia(dia, bloques, reglas, zona):
            if (
                desde <= hueco.inicia_en
                and hueco.termina_en <= hasta
                and not _choca(hueco, ocupadas)
            ):
                salida.append(hueco)
                if len(salida) >= tope:
                    break
        dia += timedelta(days=1)
    return salida


def reservable(
    momento: datetime,
    bloques: list[Bloque],
    ocupadas: list[Franja],
    reglas: Reglas,
    zona: str,
    ahora: datetime,
) -> Hueco:
    """El hueco que empieza justo ahí, o falla diciendo por qué no se puede.

    Se vuelve a comprobar al reservar y no solo al listar: entre que la alumna ve la
    pantalla y toca el botón, alguien más pudo tomar ese mismo hueco.
    """
    objetivo = a_utc(momento)
    for hueco in libres(bloques, ocupadas, reglas, zona, ahora, tope=10_000):
        if hueco.inicia_en == objetivo:
            return hueco
    raise ErrorDeDominio(Codigo.HUECO_NO_DISPONIBLE, momento=objetivo.isoformat())
