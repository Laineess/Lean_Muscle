"""Horario de atención de la coach y reserva de consultas por la alumna.

La coach declara en qué ratos atiende; de ahí, de lo que ya tiene ocupado y de dos plazos
salen los huecos. La alumna toma uno y queda agendado en firme: si a la coach le estorba,
lo reagenda desde su calendario.
"""

from __future__ import annotations

from datetime import time
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc, en_zona
from app.datos.modelos import Alumna, Cita, Coach, HorarioDeAtencion
from app.datos.repos import consultas as q
from app.dominio import huecos as h
from app.dominio.agenda import EstadoCita, Franja, Modalidad, TipoCita
from app.dominio.avisos import Aviso
from app.rutas.esquemas import (
    CitaDeAlumna,
    HorarioDeCoach,
    HuecoPublico,
    ReservaDeConsulta,
    TramoDeHorario,
)
from app.rutas.sesion import Actor, RutaQueConfirma, datos, solo_alumna, solo_coach
from app.servicios import avisos as cola
from app.servicios import bitacora

ruteador = APIRouter(prefix="/api", tags=["reserva de consultas"], route_class=RutaQueConfirma)

#: Cuántos huecos se le enseñan. Más que esto no se recorre en un teléfono.
TOPE_DE_HUECOS = 120


def _reglas(coach: Coach) -> h.Reglas:
    return h.Reglas(
        duracion_min=coach.duracion_consulta_min,
        margen_min=coach.margen_consulta_min,
        antelacion_horas=coach.antelacion_horas,
        horizonte_semanas=coach.horizonte_semanas,
    )


def _tramos(s: Session) -> list[HorarioDeAtencion]:
    return list(
        s.scalars(
            select(HorarioDeAtencion).order_by(
                HorarioDeAtencion.dia_semana, HorarioDeAtencion.desde
            )
        ).all()
    )


def _bloques(s: Session) -> list[h.Bloque]:
    return [h.Bloque(dia=f.dia_semana, desde=f.desde, hasta=f.hasta) for f in _tramos(s)]


def _ocupadas(s: Session) -> list[Franja]:
    """Todo lo agendado. Un bloque de trabajo suyo estorba igual que una consulta."""
    return [
        Franja(id=c.id, inicia_en=c.inicia_en, termina_en=c.termina_en, estado=EstadoCita(c.estado))
        for c in s.scalars(select(Cita))
    ]


def _coach(s: Session, coach_id: int) -> Coach:
    coach = s.get(Coach, coach_id)
    if coach is None:  # pragma: no cover - defensivo
        raise ErrorDeDominio(Codigo.SIN_PERMISO)
    return coach


def _hora(texto: str) -> time:
    hh, mm = texto.split(":")
    return time(int(hh), int(mm))


# ---------------------------------------------------------------------------
# Lo configura la coach
# ---------------------------------------------------------------------------


@ruteador.get("/coach/horario", response_model=HorarioDeCoach)
def ver_horario(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> HorarioDeCoach:
    coach = _coach(s, actor.coach_id)
    return HorarioDeCoach(
        tramos=[
            TramoDeHorario(
                dia_semana=f.dia_semana,
                desde=f.desde.strftime("%H:%M"),
                hasta=f.hasta.strftime("%H:%M"),
            )
            for f in _tramos(s)
        ],
        duracion_consulta_min=coach.duracion_consulta_min,
        margen_consulta_min=coach.margen_consulta_min,
        antelacion_horas=coach.antelacion_horas,
        horizonte_semanas=coach.horizonte_semanas,
        zona_horaria=coach.zona_horaria,
    )


@ruteador.put("/coach/horario", response_model=HorarioDeCoach)
def guardar_horario(
    cuerpo: HorarioDeCoach,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> HorarioDeCoach:
    """Reemplaza el horario entero."""
    coach = _coach(s, actor.coach_id)

    # Se construyen antes de borrar: un tramo al revés falla sin dejarla sin horario.
    nuevos = [
        h.Bloque(dia=t.dia_semana, desde=_hora(t.desde), hasta=_hora(t.hasta))
        for t in cuerpo.tramos
    ]
    h.revisar_horario(nuevos)
    reglas = h.Reglas(
        duracion_min=cuerpo.duracion_consulta_min,
        margen_min=cuerpo.margen_consulta_min,
        antelacion_horas=cuerpo.antelacion_horas,
        horizonte_semanas=cuerpo.horizonte_semanas,
    )

    s.execute(delete(HorarioDeAtencion))
    for bloque in nuevos:
        s.add(
            HorarioDeAtencion(
                coach_id=actor.coach_id,
                dia_semana=bloque.dia,
                desde=bloque.desde,
                hasta=bloque.hasta,
            )
        )

    coach.duracion_consulta_min = reglas.duracion_min
    coach.margen_consulta_min = reglas.margen_min
    coach.antelacion_horas = reglas.antelacion_horas
    coach.horizonte_semanas = reglas.horizonte_semanas
    if cuerpo.zona_horaria:
        coach.zona_horaria = cuerpo.zona_horaria
    s.flush()

    return ver_horario(actor, s)


# ---------------------------------------------------------------------------
# Lo usa la alumna
# ---------------------------------------------------------------------------


def _avisar_a_la_coach(s: Session, coach_id: int, coach: Coach, alumna: Alumna, cita: Cita) -> None:
    """La alumna agenda sola: sin esto, la coach se entera al abrir su calendario."""
    usuario = q.usuario_de_coach(s)
    if usuario is None:  # pragma: no cover - defensivo
        return

    inicia = en_zona(cita.inicia_en, coach.zona_horaria)
    fin = en_zona(cita.termina_en, coach.zona_horaria)
    enc = _comprobante_para_la_coach(s, alumna.id)
    contexto = {
        "alumna": alumna.nombre,
        "fecha": f"{inicia:%d/%m/%Y}",
        "hora_inicio": f"{inicia:%H:%M}",
        "hora_fin": f"{fin:%H:%M}",
        "modalidad": _nombre_modalidad(cita.modalidad),
        "whatsapp": alumna.whatsapp or "—",
        "correo": _correo_de_alumna(s, alumna),
        "comprobante_key": enc["comprobante_key"],
        "comprobante_nombre": enc["comprobante_nombre"],
        "comprobante_nota": enc["comprobante_nota"],
    }
    cola.encolar(
        s,
        Aviso.CONSULTA_RESERVADA,
        coach_id=coach_id,
        llave=f"cita:{cita.ulid}:reservada",
        para=usuario.email,
        contexto=contexto,
        destinatario_id=usuario.id,
    )


def _nombre_modalidad(modalidad: str) -> str:
    return {
        "presencial": "Presencial",
        "video": "Videollamada",
        "telefono": "Por teléfono",
    }.get(modalidad, modalidad)


def _correo_de_alumna(s: Session, alumna: Alumna) -> str:
    from app.datos.modelos import Usuario

    if alumna.usuario_id is None:  # pragma: no cover - defensivo
        return "—"
    usuario = s.get(Usuario, alumna.usuario_id)
    return usuario.email if usuario is not None else "—"


def _comprobante_para_la_coach(s: Session, alumna_id: int) -> dict[str, str]:
    """Metadatos del comprobante más reciente de la alumna, para adjuntarlo en el correo.

    El archivo mismo lo lee el emisor desde el almacén con la `comprobante_key`: aquí solo
    se copia la llave y un nombre para el adjunto. Si todavía no hay comprobante, el correo
    lo dice en lugar de enchinar la cola con una llave vacía.
    """
    ultimo = None
    for c in q.cobros_de(s, alumna_id):
        if c.comprobante_key:
            ultimo = c
    if ultimo is None or ultimo.comprobante_key is None:
        return {"comprobante_key": "", "comprobante_nombre": "", "comprobante_nota": "Todavía no subió comprobante."}

    llave = ultimo.comprobante_key
    extension = llave.rsplit(".", 1)[-1].lower()
    nombre = f"comprobante.{extension}"
    return {
        "comprobante_key": llave,
        "comprobante_nombre": nombre,
        "comprobante_nota": "Su comprobante va adjunto.",
    }


@ruteador.get("/mi/huecos", response_model=list[HuecoPublico])
def huecos_libres(
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> list[HuecoPublico]:
    """Las horas en que puede reservar su consulta."""
    coach = _coach(s, actor.coach_id)
    bloques = _bloques(s)
    if not bloques:
        raise ErrorDeDominio(Codigo.SIN_HORARIO_DE_ATENCION)

    libres = h.libres(
        bloques, _ocupadas(s), _reglas(coach), coach.zona_horaria, ahora_utc(), TOPE_DE_HUECOS
    )
    return [
        HuecoPublico(
            inicia_en=x.inicia_en, termina_en=x.termina_en, datos_bancarios=coach.datos_bancarios
        )
        for x in libres
    ]


@ruteador.post("/mi/citas", response_model=CitaDeAlumna, status_code=201)
def reservar_consulta(
    cuerpo: ReservaDeConsulta,
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> CitaDeAlumna:
    """Toma un hueco libre.

    Se vuelve a comprobar aquí y no solo al listar: entre que lo vio y lo tocó, otra alumna
    pudo ganárselo.
    """
    alumna = q.alumna_de_usuario(s, actor.usuario_id)
    if alumna is None:
        raise ErrorDeDominio(Codigo.SIN_PERMISO)
    if cuerpo.modalidad not in {m.value for m in Modalidad}:
        raise ErrorDeDominio(
            Codigo.CATEGORIA_INVALIDA, categoria=cuerpo.modalidad, tipo="modalidad"
        )

    coach = _coach(s, actor.coach_id)
    bloques = _bloques(s)
    if not bloques:
        raise ErrorDeDominio(Codigo.SIN_HORARIO_DE_ATENCION)

    hueco = h.reservable(
        cuerpo.inicia_en, bloques, _ocupadas(s), _reglas(coach), coach.zona_horaria, ahora_utc()
    )

    cita = Cita(
        coach_id=actor.coach_id,
        alumna_id=alumna.id,
        titulo=f"Consulta · {alumna.nombre}",
        tipo=TipoCita.CONSULTA.value,
        estado=EstadoCita.AGENDADA.value,
        modalidad=cuerpo.modalidad,
        inicia_en=hueco.inicia_en,
        termina_en=hueco.termina_en,
    )
    s.add(cita)
    s.flush()

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="alumna",
        accion=bitacora.Accion.CITA_RESERVADA,
        entidad="cita",
        entidad_id=cita.id,
        detalle={"inicia_en": hueco.inicia_en.isoformat()},
    )

    _avisar_a_la_coach(s, actor.coach_id, coach, alumna, cita)

    return CitaDeAlumna(
        ulid=cita.ulid,
        titulo=cita.titulo,
        modalidad=cita.modalidad,
        estado=cita.estado,
        inicia_en=cita.inicia_en,
        termina_en=cita.termina_en,
    )
