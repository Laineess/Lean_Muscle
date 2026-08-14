"""Consultas del superadmin. **Solo agregados.**

De las tablas con datos de alumnas aqui solo salen COUNT, SUM, MIN y MAX. Nunca una fila,
nunca un nombre, nunca una fotografia: frente a la LFPDPPP la plataforma es Encargado, no
Responsable, y esa posicion solo se sostiene si el acceso tecnico coincide con el contrato.

`pruebas/aislamiento/prueba_plataforma.py` lo comprueba leyendo el arbol sintactico.

Todas reciben una sesion **sin alcance**, con su motivo por escrito en cada llamada.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.datos.modelos import (
    Alumna,
    AvisoEnviado,
    Bitacora,
    Chequeo,
    Coach,
    CobroCoach,
    Foto,
    Sesion,
    SuscripcionCoach,
    SuscripcionPush,
    Usuario,
)

#: Ventana de «actividad reciente» para decidir si una coach sigue usando la plataforma.
DIAS_ACTIVIDAD = 30


@dataclass(frozen=True, slots=True)
class Conteos:
    """Cuántas, no quiénes."""

    alumnas: int
    alumnas_activas: int
    chequeos_por_validar: int
    chequeos_del_mes: int
    fotos: int
    bytes_fotos: int
    ultimo_acceso: datetime | None


@dataclass(frozen=True, slots=True)
class Salud:
    """Lo que hay que mirar una vez al mes para saber si la plataforma está sana."""

    avisos_pendientes: int
    avisos_agotados: int
    ultimo_aviso_enviado: datetime | None
    fotos_por_purgar: int
    bytes_totales: int
    suscripciones_push: int
    sesiones_vivas: int


def coaches(s: Session) -> list[Coach]:
    """Los inquilinos. `coach` no lleva datos de alumnas: es la relación comercial."""
    return list(s.scalars(select(Coach).order_by(Coach.nombre)).all())


def coach_por_ulid(s: Session, ulid: str) -> Coach | None:
    return s.scalars(select(Coach).where(Coach.ulid == ulid)).first()


def coach_por_email(s: Session, email: str) -> Coach | None:
    return s.scalars(select(Coach).where(Coach.email == email.strip().lower())).first()


def conteos_por_coach(s: Session, hoy: date) -> dict[int, Conteos]:
    """Un agregado por inquilino, en cuatro consultas y no una por coach.

    Con veinte coaches la diferencia no se nota; con doscientas, una consulta por coach son
    doscientas idas a la base cada vez que se abre el panel.
    """
    inicio_mes = hoy.replace(day=1)

    alumnas: dict[int, tuple[int, int]] = {}
    for coach_id, total, activas in s.execute(
        select(
            Alumna.coach_id,
            func.count(Alumna.id),
            func.sum(func.if_(Alumna.estado == "activa", 1, 0)),
        ).group_by(Alumna.coach_id)
    ):
        alumnas[coach_id] = (int(total or 0), int(activas or 0))

    chequeos: dict[int, tuple[int, int]] = {}
    for coach_id, por_validar, del_mes in s.execute(
        select(
            Chequeo.coach_id,
            func.sum(func.if_(Chequeo.estado == "pendiente_evaluacion", 1, 0)),
            func.sum(func.if_(Chequeo.fecha >= inicio_mes, 1, 0)),
        ).group_by(Chequeo.coach_id)
    ):
        chequeos[coach_id] = (int(por_validar or 0), int(del_mes or 0))

    fotos: dict[int, tuple[int, int]] = {}
    for coach_id, cuantas, peso in s.execute(
        select(Foto.coach_id, func.count(Foto.id), func.sum(Foto.bytes))
        .where(Foto.purgada_en.is_(None))
        .group_by(Foto.coach_id)
    ):
        fotos[coach_id] = (int(cuantas or 0), int(peso or 0))

    accesos: dict[int, datetime | None] = {}
    for coach_id, ultimo in s.execute(
        select(Usuario.coach_id, func.max(Usuario.ultimo_acceso_en)).group_by(Usuario.coach_id)
    ):
        accesos[coach_id] = ultimo

    resultado: dict[int, Conteos] = {}
    for coach in s.scalars(select(Coach.id)):
        total, activas = alumnas.get(coach, (0, 0))
        por_validar, del_mes = chequeos.get(coach, (0, 0))
        cuantas, peso = fotos.get(coach, (0, 0))
        resultado[coach] = Conteos(
            alumnas=total,
            alumnas_activas=activas,
            chequeos_por_validar=por_validar,
            chequeos_del_mes=del_mes,
            fotos=cuantas,
            bytes_fotos=peso,
            ultimo_acceso=accesos.get(coach),
        )
    return resultado


def suscripciones(s: Session) -> dict[int, SuscripcionCoach]:
    return {f.coach_id: f for f in s.scalars(select(SuscripcionCoach))}


def suscripcion_de(s: Session, coach_id: int) -> SuscripcionCoach | None:
    return s.scalars(select(SuscripcionCoach).where(SuscripcionCoach.coach_id == coach_id)).first()


def cobros_de(s: Session, coach_id: int, limite: int = 24) -> list[CobroCoach]:
    return list(
        s.scalars(
            select(CobroCoach)
            .where(CobroCoach.coach_id == coach_id)
            .order_by(CobroCoach.fecha.desc())
            .limit(limite)
        ).all()
    )


def cobrado_en_el_ano(s: Session, ano: int) -> Decimal:
    total = s.scalar(
        select(func.sum(CobroCoach.monto)).where(
            CobroCoach.fecha >= date(ano, 1, 1), CobroCoach.fecha <= date(ano, 12, 31)
        )
    )
    return Decimal(total or 0)


def cobros_por_mes(s: Session, desde: date) -> list[tuple[str, Decimal]]:
    filas = s.execute(
        select(
            func.date_format(CobroCoach.fecha, "%Y-%m"),
            func.sum(CobroCoach.monto),
        )
        .where(CobroCoach.fecha >= desde)
        .group_by(func.date_format(CobroCoach.fecha, "%Y-%m"))
        .order_by(func.date_format(CobroCoach.fecha, "%Y-%m"))
    )
    return [(str(mes), Decimal(monto or 0)) for mes, monto in filas]


def salud(s: Session, ahora: datetime, retencion_meses: int) -> Salud:
    """El estado de las piezas que fallan en silencio.

    La cola de avisos y la purga de fotografías son las dos que nadie nota hasta que alguien
    reclama: la primera porque un correo que no salió no avisa de que no salió, y la segunda
    porque incumplir el plazo de conservación no produce ningún error.
    """
    corte = ahora - timedelta(days=30 * retencion_meses)

    pendientes = s.scalar(
        select(func.count(AvisoEnviado.id)).where(
            AvisoEnviado.enviado_en.is_(None), AvisoEnviado.intentos < 5
        )
    )
    agotados = s.scalar(
        select(func.count(AvisoEnviado.id)).where(
            AvisoEnviado.enviado_en.is_(None), AvisoEnviado.intentos >= 5
        )
    )
    ultimo = s.scalar(select(func.max(AvisoEnviado.enviado_en)))

    por_purgar = s.scalar(
        select(func.count(Foto.id)).where(Foto.purgada_en.is_(None), Foto.tomada_en < corte)
    )
    bytes_totales = s.scalar(select(func.sum(Foto.bytes)).where(Foto.purgada_en.is_(None)))

    push = s.scalar(select(func.count(SuscripcionPush.id)))
    sesiones = s.scalar(
        select(func.count(Sesion.id)).where(Sesion.revocada_en.is_(None), Sesion.vence_en > ahora)
    )

    return Salud(
        avisos_pendientes=int(pendientes or 0),
        avisos_agotados=int(agotados or 0),
        ultimo_aviso_enviado=ultimo,
        fotos_por_purgar=int(por_purgar or 0),
        bytes_totales=int(bytes_totales or 0),
        suscripciones_push=int(push or 0),
        sesiones_vivas=int(sesiones or 0),
    )


def auditoria(s: Session, limite: int = 100) -> list[tuple[datetime, int, str, str, str]]:
    """Movimientos recientes de la bitácora, **sin `detalle` y sin `entidad_id`**.

    Con eso basta para responder «¿qué se ha estado haciendo en esta cuenta?» ante un reclamo.
    Traer `detalle` o el identificador de la entidad permitiría reconstruir a qué alumna
    corresponde cada movimiento, que es justo lo que este panel no debe poder hacer.
    """
    filas = s.execute(
        select(
            Bitacora.creado_en,
            Bitacora.coach_id,
            Bitacora.actor_tipo,
            Bitacora.accion,
            Bitacora.entidad,
        )
        .order_by(Bitacora.creado_en.desc())
        .limit(limite)
    )
    return [
        (cuando, coach, actor, accion, entidad) for cuando, coach, actor, accion, entidad in filas
    ]
