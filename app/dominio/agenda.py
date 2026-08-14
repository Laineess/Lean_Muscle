"""Reglas de la agenda de la coach.

Dos citas no pueden solaparse aunque una sea consulta y la otra un bloque de trabajo: el
tiempo de la coach es uno solo. Es la regla que evita el error caro de esta pantalla, que
es agendar dos alumnas a la misma hora.

Módulo puro: recibe lo que ya hay en la agenda y responde. No consulta la base.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import a_utc

#: Duración mínima con sentido para una consulta. Menos de esto suele ser un dedazo.
DURACION_MINIMA = timedelta(minutes=10)
#: Tope para atrapar el error de poner una fecha de fin del día equivocado.
DURACION_MAXIMA = timedelta(hours=8)
#: Con cuánta anticipación se le recuerda a la alumna.
ANTICIPACION_RECORDATORIO = timedelta(days=1)


class TipoCita(StrEnum):
    CONSULTA = "consulta"
    BLOQUEO = "bloqueo"


class EstadoCita(StrEnum):
    AGENDADA = "agendada"
    CONFIRMADA = "confirmada"
    REALIZADA = "realizada"
    CANCELADA = "cancelada"


class Modalidad(StrEnum):
    PRESENCIAL = "presencial"
    VIDEO = "video"
    TELEFONO = "telefono"


#: Estados que ya no ocupan hueco en la agenda.
ESTADOS_LIBERADOS = frozenset({EstadoCita.CANCELADA})


@dataclass(frozen=True, slots=True)
class Franja:
    """Un hueco ocupado en la agenda. Es todo lo que la regla de solape necesita saber."""

    id: int | None
    inicia_en: datetime
    termina_en: datetime
    estado: EstadoCita = EstadoCita.AGENDADA

    @property
    def duracion(self) -> timedelta:
        return self.termina_en - self.inicia_en

    @property
    def ocupa(self) -> bool:
        return self.estado not in ESTADOS_LIBERADOS

    def choca_con(self, otra: Franja) -> bool:
        """Solape de intervalos medio abiertos: una cita que empieza justo cuando termina
        la anterior **no** choca. Sin esa apertura, agendar consultas seguidas es imposible."""
        if not (self.ocupa and otra.ocupa):
            return False
        return a_utc(self.inicia_en) < a_utc(otra.termina_en) and a_utc(otra.inicia_en) < a_utc(
            self.termina_en
        )


def validar_franja(
    franja: Franja, *, ahora: datetime | None = None, permitir_pasado: bool = False
) -> None:
    """Rango coherente y duración con sentido."""
    inicia = a_utc(franja.inicia_en)
    termina = a_utc(franja.termina_en)

    if termina <= inicia:
        raise ErrorDeDominio(
            Codigo.CITA_RANGO_INVALIDO,
            inicia_en=inicia.isoformat(),
            termina_en=termina.isoformat(),
        )

    duracion = termina - inicia
    if duracion < DURACION_MINIMA or duracion > DURACION_MAXIMA:
        raise ErrorDeDominio(
            Codigo.CITA_DURACION_INVALIDA,
            minutos=int(duracion.total_seconds() // 60),
            minimo=int(DURACION_MINIMA.total_seconds() // 60),
            maximo=int(DURACION_MAXIMA.total_seconds() // 60),
        )

    # Registrar una consulta que ya ocurrió es legítimo; agendarla a futuro en el pasado, no.
    if not permitir_pasado and ahora is not None and inicia < a_utc(ahora):
        raise ErrorDeDominio(Codigo.CITA_EN_EL_PASADO, inicia_en=inicia.isoformat())


def buscar_choque(nueva: Franja, agenda: list[Franja]) -> Franja | None:
    """Primera cita de la agenda que choca con `nueva`, o None.

    Al editar, la propia cita se excluye por `id`: si no, toda edición chocaría consigo misma.
    """
    for existente in agenda:
        if nueva.id is not None and existente.id == nueva.id:
            continue
        if nueva.choca_con(existente):
            return existente
    return None


def exigir_hueco_libre(nueva: Franja, agenda: list[Franja]) -> None:
    choque = buscar_choque(nueva, agenda)
    if choque is not None:
        raise ErrorDeDominio(
            Codigo.CITA_SE_SOLAPA,
            inicia_en=a_utc(choque.inicia_en).isoformat(),
            termina_en=a_utc(choque.termina_en).isoformat(),
        )


def agendar(
    nueva: Franja,
    agenda: list[Franja],
    *,
    ahora: datetime | None = None,
    permitir_pasado: bool = False,
) -> None:
    """Todas las guardas del alta y la edición, en el orden en que importan."""
    validar_franja(nueva, ahora=ahora, permitir_pasado=permitir_pasado)
    exigir_hueco_libre(nueva, agenda)


def transicionar(
    estado: EstadoCita, destino: EstadoCita, *, motivo: str | None = None
) -> EstadoCita:
    """Cambios de estado permitidos. Cancelar exige motivo: la alumna lo va a leer."""
    permitidas: dict[EstadoCita, frozenset[EstadoCita]] = {
        EstadoCita.AGENDADA: frozenset(
            {EstadoCita.CONFIRMADA, EstadoCita.CANCELADA, EstadoCita.REALIZADA}
        ),
        EstadoCita.CONFIRMADA: frozenset({EstadoCita.REALIZADA, EstadoCita.CANCELADA}),
        EstadoCita.REALIZADA: frozenset(),
        EstadoCita.CANCELADA: frozenset(),
    }

    if destino not in permitidas[estado]:
        raise ErrorDeDominio(
            Codigo.TRANSICION_NO_PERMITIDA, estado=estado.value, transicion=destino.value
        )

    if destino is EstadoCita.CANCELADA and not (motivo or "").strip():
        raise ErrorDeDominio(Codigo.MOTIVO_DE_CANCELACION_REQUERIDO)

    return destino


def toca_recordatorio(franja: Franja, ahora: datetime, ya_enviado: bool) -> bool:
    """Si falta un día o menos y todavía no se avisó."""
    if ya_enviado or not franja.ocupa:
        return False
    return a_utc(franja.inicia_en) - a_utc(ahora) <= ANTICIPACION_RECORDATORIO
