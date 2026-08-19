"""Derechos ARCO: la alumna los ejerce, la coach los atiende.

La coach es la Responsable frente a la LFPDPPP, así que la solicitud le llega a ella y el
plazo le corre a ella. La plataforma solo guarda la constancia.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.datos.modelos import Alumna, SolicitudArco
from app.datos.repos import consultas as q
from app.dominio import arco
from app.rutas.esquemas import RespuestaArco, SolicitudArcoNueva, SolicitudArcoPublica
from app.rutas.sesion import Actor, RutaQueConfirma, datos, solo_alumna, solo_coach
from app.servicios import bitacora

ruteador = APIRouter(prefix="/api", tags=["derechos arco"], route_class=RutaQueConfirma)


def _publica(s: SolicitudArco, nombre: str | None = None) -> SolicitudArcoPublica:
    dia = ahora_utc().date()
    estado = arco.Estado(s.estado)
    plazo = arco.plazo_de(
        estado,
        s.recibida_en.date(),
        s.respondida_en.date() if s.respondida_en else None,
        dia,
    )
    return SolicitudArcoPublica(
        ulid=s.ulid,
        derecho=s.derecho,
        rotulo=arco.ROTULO[arco.Derecho(s.derecho)],
        estado=s.estado,
        detalle=s.detalle,
        respuesta=s.respuesta,
        recibida_en=s.recibida_en,
        respondida_en=s.respondida_en,
        resuelta_en=s.resuelta_en,
        vence_el=plazo.vence_el if plazo else None,
        dias_restantes=plazo.dias_restantes if plazo else None,
        alumna=nombre,
    )


def _mi_alumna(s: Session, actor: Actor) -> Alumna:
    alumna = q.alumna_de_usuario(s, actor.usuario_id)
    if alumna is None:
        raise ErrorDeDominio(Codigo.SIN_PERMISO)
    return alumna


# ---------------------------------------------------------------------------
# Lado de la alumna
# ---------------------------------------------------------------------------


@ruteador.post("/mi/arco", response_model=SolicitudArcoPublica, status_code=201)
def ejercer_derecho(
    cuerpo: SolicitudArcoNueva,
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> SolicitudArcoPublica:
    """Registra la solicitud y arranca el plazo. No se puede editar después."""
    alumna = _mi_alumna(s, actor)

    solicitud = SolicitudArco(
        coach_id=actor.coach_id,
        alumna_id=alumna.id,
        derecho=cuerpo.derecho,
        recibida_en=ahora_utc(),
        estado=arco.Estado.RECIBIDA.value,
        detalle=cuerpo.detalle.strip() or None,
    )
    s.add(solicitud)
    s.flush()

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="alumna",
        accion=bitacora.Accion.ARCO_RECIBIDA,
        entidad="solicitud_arco",
        entidad_id=solicitud.id,
        detalle={"derecho": cuerpo.derecho},
    )

    return _publica(solicitud)


@ruteador.get("/mi/arco", response_model=list[SolicitudArcoPublica])
def mis_solicitudes(
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> list[SolicitudArcoPublica]:
    alumna = _mi_alumna(s, actor)
    filas = s.scalars(
        select(SolicitudArco)
        .where(SolicitudArco.alumna_id == alumna.id)
        .order_by(SolicitudArco.recibida_en.desc())
    ).all()
    return [_publica(f) for f in filas]


# ---------------------------------------------------------------------------
# Lado de la coach
# ---------------------------------------------------------------------------


@ruteador.get("/coach/arco", response_model=list[SolicitudArcoPublica])
def solicitudes_recibidas(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> list[SolicitudArcoPublica]:
    """Las suyas, primero lo que vence antes."""
    _ = actor
    filas = list(
        s.scalars(select(SolicitudArco).order_by(SolicitudArco.recibida_en)).all()
    )
    nombres = {
        a.id: a.nombre
        for a in s.scalars(select(Alumna).where(Alumna.id.in_([f.alumna_id for f in filas])))
    }
    publicas = [_publica(f, nombres.get(f.alumna_id)) for f in filas]
    pendientes = [p for p in publicas if p.dias_restantes is not None]
    resueltas = [p for p in publicas if p.dias_restantes is None]
    pendientes.sort(key=lambda p: p.dias_restantes or 0)
    return pendientes + resueltas


def _suya(s: Session, ulid: str) -> SolicitudArco:
    fila = s.scalars(select(SolicitudArco).where(SolicitudArco.ulid == ulid)).first()
    if fila is None:
        raise HTTPException(404, "No existe esa solicitud")
    return fila


@ruteador.post("/coach/arco/{ulid}/responder", response_model=SolicitudArcoPublica)
def responder(
    ulid: str,
    cuerpo: RespuestaArco,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> SolicitudArcoPublica:
    """Contesta dentro del plazo. La respuesta se guarda: es la constancia."""
    if not cuerpo.respuesta.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)

    solicitud = _suya(s, ulid)
    if solicitud.estado != arco.Estado.RECIBIDA.value:
        raise HTTPException(409, "Esa solicitud ya fue contestada")

    solicitud.respuesta = cuerpo.respuesta.strip()
    solicitud.respondida_en = ahora_utc()
    solicitud.estado = arco.Estado.RESPONDIDA.value

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="coach",
        accion=bitacora.Accion.ARCO_RESPONDIDA,
        entidad="solicitud_arco",
        entidad_id=solicitud.id,
        detalle={"derecho": solicitud.derecho},
    )
    s.flush()
    return _publica(solicitud)


@ruteador.post("/coach/arco/{ulid}/resolver", response_model=SolicitudArcoPublica)
def resolver(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> SolicitudArcoPublica:
    """Cierra la solicitud: lo prometido ya se hizo."""
    solicitud = _suya(s, ulid)
    if solicitud.estado == arco.Estado.RECIBIDA.value:
        raise HTTPException(409, "Contéstala antes de darla por resuelta")
    if solicitud.estado == arco.Estado.RESUELTA.value:
        raise HTTPException(409, "Esa solicitud ya está resuelta")

    solicitud.resuelta_en = ahora_utc()
    solicitud.estado = arco.Estado.RESUELTA.value

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="coach",
        accion=bitacora.Accion.ARCO_RESUELTA,
        entidad="solicitud_arco",
        entidad_id=solicitud.id,
        detalle={"derecho": solicitud.derecho},
    )
    s.flush()
    return _publica(solicitud)
