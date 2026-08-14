"""Consultas de lectura.

Todas reciben la sesión ya atada al inquilino (`sesion_con_alcance`). **Ninguna filtra por
`coach_id` a mano**: eso lo hace el gancho de `alcance.py` sobre cada SELECT, incluidos los
JOIN y la carga diferida. Escribir el filtro a mano aquí sería precisamente el olvido que
esa capa existe para evitar.

Cada función de este archivo necesita su prueba en `pruebas/aislamiento`. Una función nueva
sin ella no pasa el CI.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.datos.modelos import (
    Alumna,
    Chequeo,
    Ciclo,
    Cita,
    Consentimiento,
    Foto,
    HistorialClinico,
    Medida,
    Mensaje,
    Notificacion,
    Pago,
    Pesaje,
    Plan,
    Usuario,
)


def alumna_por_ulid(s: Session, ulid: str) -> Alumna | None:
    return s.scalars(select(Alumna).where(Alumna.ulid == ulid)).first()


def alumna_de_usuario(s: Session, usuario_id: int) -> Alumna | None:
    return s.scalars(select(Alumna).where(Alumna.usuario_id == usuario_id)).first()


def ciclo_vigente(s: Session, alumna_id: int) -> Ciclo | None:
    return s.scalars(
        select(Ciclo).where(Ciclo.alumna_id == alumna_id).order_by(Ciclo.numero.desc())
    ).first()


def chequeos_de(s: Session, alumna_id: int, limite: int = 24) -> list[Chequeo]:
    """Del más viejo al más nuevo: las gráficas se leen en ese orden."""
    filas = s.scalars(
        select(Chequeo)
        .where(Chequeo.alumna_id == alumna_id, Chequeo.estado != "descartado")
        .order_by(Chequeo.fecha.desc())
        .limit(limite)
    ).all()
    return list(reversed(filas))


def medidas_de(s: Session, chequeo_ids: list[int]) -> dict[int, dict[str, Decimal]]:
    if not chequeo_ids:
        return {}
    agrupadas: dict[int, dict[str, Decimal]] = {i: {} for i in chequeo_ids}
    for m in s.scalars(select(Medida).where(Medida.chequeo_id.in_(chequeo_ids))):
        agrupadas[m.chequeo_id][m.tipo] = m.valor
    return agrupadas


def pesajes_del_ciclo(s: Session, alumna_id: int, ciclo_id: int) -> list[Pesaje]:
    """Hasta 3 por ciclo; el promedio alimenta la calculadora."""
    return list(
        s.scalars(
            select(Pesaje)
            .join(Chequeo, Chequeo.id == Pesaje.chequeo_id)
            .where(Pesaje.alumna_id == alumna_id, Chequeo.ciclo_id == ciclo_id)
            .order_by(Pesaje.fecha)
        ).all()
    )


def peso_de_chequeo(s: Session, chequeo_ids: list[int]) -> dict[int, Decimal]:
    if not chequeo_ids:
        return {}
    return {
        p.chequeo_id: p.peso_kg
        for p in s.scalars(select(Pesaje).where(Pesaje.chequeo_id.in_(chequeo_ids)))
        if p.chequeo_id is not None
    }


def planes_del_ciclo(s: Session, alumna_id: int, ciclo_id: int) -> dict[str, Plan]:
    filas = s.scalars(
        select(Plan).where(Plan.alumna_id == alumna_id, Plan.ciclo_id == ciclo_id)
    ).all()
    return {p.tipo: p for p in filas}


def historial_vigente(s: Session, alumna_id: int) -> HistorialClinico | None:
    """El historial se versiona: la vigente es la última insertada."""
    return s.scalars(
        select(HistorialClinico)
        .where(HistorialClinico.alumna_id == alumna_id)
        .order_by(HistorialClinico.vigente_desde.desc())
    ).first()


def avisos_sin_leer(s: Session, usuario_id: int) -> int:
    return (
        s.scalar(
            select(func.count())
            .select_from(Notificacion)
            .where(Notificacion.destinatario_id == usuario_id, Notificacion.leida_en.is_(None))
        )
        or 0
    )


def cartera(s: Session) -> list[Alumna]:
    return list(s.scalars(select(Alumna).order_by(Alumna.nombre)).all())


def ultimo_acceso_de(s: Session, usuario_ids: list[int]) -> dict[int, datetime | None]:
    if not usuario_ids:
        return {}
    return {
        u.id: u.ultimo_acceso_en
        for u in s.scalars(select(Usuario).where(Usuario.id.in_(usuario_ids)))
    }


def ultimo_chequeo_por_alumna(s: Session, alumna_ids: list[int]) -> dict[int, Chequeo]:
    """El chequeo más reciente de cada alumna. Es lo que ordena la bandeja de validación."""
    if not alumna_ids:
        return {}
    ultimos: dict[int, Chequeo] = {}
    for c in s.scalars(
        select(Chequeo)
        .where(Chequeo.alumna_id.in_(alumna_ids), Chequeo.estado != "descartado")
        .order_by(Chequeo.fecha)
    ):
        ultimos[c.alumna_id] = c  # el orden ascendente deja el más nuevo al final
    return ultimos


def pago_del_ciclo(s: Session, ciclo_ids: list[int]) -> dict[int, Pago]:
    if not ciclo_ids:
        return {}
    return {p.ciclo_id: p for p in s.scalars(select(Pago).where(Pago.ciclo_id.in_(ciclo_ids)))}


def ciclos_vigentes(s: Session, alumna_ids: list[int]) -> dict[int, Ciclo]:
    if not alumna_ids:
        return {}
    vigentes: dict[int, Ciclo] = {}
    for c in s.scalars(select(Ciclo).where(Ciclo.alumna_id.in_(alumna_ids)).order_by(Ciclo.numero)):
        vigentes[c.alumna_id] = c
    return vigentes


def citas_entre(s: Session, desde: datetime, hasta: datetime) -> list[Cita]:
    return list(
        s.scalars(
            select(Cita)
            .where(Cita.inicia_en >= desde, Cita.inicia_en < hasta)
            .order_by(Cita.inicia_en)
        ).all()
    )


def citas_del_dia(s: Session, dia: date) -> list[Cita]:
    inicio = datetime.combine(dia, datetime.min.time())
    fin = datetime.combine(dia, datetime.max.time())
    return citas_entre(s, inicio, fin)


def proximas_citas_de(s: Session, alumna_id: int, desde: datetime, limite: int = 3) -> list[Cita]:
    """Las citas que le vienen a una alumna. Las canceladas no cuentan como próximas."""
    return list(
        s.scalars(
            select(Cita)
            .where(
                Cita.alumna_id == alumna_id,
                Cita.inicia_en >= desde,
                Cita.estado != "cancelada",
            )
            .order_by(Cita.inicia_en)
            .limit(limite)
        ).all()
    )


def cita_por_ulid(s: Session, ulid: str) -> Cita | None:
    return s.scalars(select(Cita).where(Cita.ulid == ulid)).first()


def chequeo_por_ulid(s: Session, ulid: str) -> Chequeo | None:
    return s.scalars(select(Chequeo).where(Chequeo.ulid == ulid)).first()


def borrador_de(s: Session, alumna_id: int, ciclo_id: int) -> Chequeo | None:
    """El chequeo abierto del ciclo, si lo hay.

    `rechazado_calidad` cuenta como abierto: la alumna vuelve a la misma captura a repetir
    lo que la coach le pidió, no empieza un chequeo nuevo que rompería la numeración.
    """
    return s.scalars(
        select(Chequeo)
        .where(
            Chequeo.alumna_id == alumna_id,
            Chequeo.ciclo_id == ciclo_id,
            Chequeo.estado.in_(("borrador", "rechazado_calidad")),
        )
        .order_by(Chequeo.fecha.desc())
    ).first()


def fotos_de(s: Session, chequeo_id: int) -> list[Foto]:
    return list(
        s.scalars(select(Foto).where(Foto.chequeo_id == chequeo_id).order_by(Foto.angulo)).all()
    )


def medidas_del_chequeo(s: Session, chequeo_id: int) -> list[Medida]:
    return list(s.scalars(select(Medida).where(Medida.chequeo_id == chequeo_id)).all())


def consentimiento_vigente(s: Session, alumna_id: int, tipo: str) -> Consentimiento | None:
    """El consentimiento aceptado y no revocado más reciente de ese tipo.

    Revocar no borra la fila: se inserta la revocación sobre la que había. Por eso se pide el
    último y se comprueba `revocado_en`, en lugar de confiar en que exista alguna fila.
    """
    return s.scalars(
        select(Consentimiento)
        .where(
            Consentimiento.alumna_id == alumna_id,
            Consentimiento.tipo == tipo,
            Consentimiento.revocado_en.is_(None),
        )
        .order_by(Consentimiento.aceptado_en.desc())
    ).first()


def mensajes_de(s: Session, alumna_id: int) -> list[Mensaje]:
    """El hilo completo, del más viejo al más nuevo: se lee como una conversación."""
    return list(
        s.scalars(
            select(Mensaje).where(Mensaje.alumna_id == alumna_id).order_by(Mensaje.enviado_en)
        ).all()
    )
