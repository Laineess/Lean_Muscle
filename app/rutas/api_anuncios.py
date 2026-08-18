"""Avisos de la coach a sus alumnas: un título y una frase.

Van en una sola dirección, a varias a la vez y sin hilo, que es lo que los distingue de la
mensajería. Salen por notificación y quedan en la app: **una frase de ánimo por correo es
correo basura**, y el correo aquí se reserva para acceso, dinero y privacidad.

El texto lo escribe ella. Es el único aviso de la plataforma que no lleva plantilla, así que
el título y el cuerpo viajan en el contexto y llegan tal cual.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.datos.modelos import Alumna, Anuncio, Notificacion, Usuario
from app.datos.repos import consultas as q
from app.dominio.avisos import Aviso
from app.rutas.esquemas import AnuncioNuevo, AnuncioPublico, AvisoDeAlumna
from app.rutas.sesion import Actor, datos, solo_alumna, solo_coach
from app.servicios import avisos as cola
from app.servicios import bitacora

ruteador = APIRouter(prefix="/api", tags=["avisos de la coach"])

#: Cuántos anuncios se le muestran a la coach en su historial.
HISTORIAL = 30


def _publico(s: Session, a: Anuncio) -> AnuncioPublico:
    enviadas = (
        s.scalar(
            select(func.count()).select_from(Notificacion).where(Notificacion.anuncio_id == a.id)
        )
        or 0
    )
    leidas = (
        s.scalar(
            select(func.count())
            .select_from(Notificacion)
            .where(Notificacion.anuncio_id == a.id, Notificacion.leida_en.is_not(None))
        )
        or 0
    )
    return AnuncioPublico(
        ulid=a.ulid,
        titulo=a.titulo,
        cuerpo=a.cuerpo,
        enviado_en=a.enviado_en,
        enviadas=enviadas,
        leidas=leidas,
    )


# ---------------------------------------------------------------------------
# Lado de la coach
# ---------------------------------------------------------------------------


@ruteador.post("/coach/anuncios", response_model=AnuncioPublico, status_code=201)
def enviar_anuncio(
    cuerpo: AnuncioNuevo,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> AnuncioPublico:
    """Manda la frase a las alumnas elegidas, o a todas las activas si no elige ninguna."""
    titulo = cuerpo.titulo.strip()
    texto = cuerpo.cuerpo.strip()
    if not titulo or not texto:
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)

    if cuerpo.alumnas:
        elegidas: list[Alumna] = []
        for ulid in cuerpo.alumnas:
            alumna = q.alumna_por_ulid(s, ulid)
            # Un ULID de otra coach no existe para esta sesión: 404 sin decir que existe.
            if alumna is None:
                raise HTTPException(404, "No existe esa alumna")
            elegidas.append(alumna)
    else:
        elegidas = [a for a in q.cartera(s) if a.estado == "activa"]

    if not elegidas:
        raise HTTPException(409, "No tienes alumnas activas a las que mandarlo")

    anuncio = Anuncio(
        coach_id=actor.coach_id,
        titulo=titulo,
        cuerpo=texto,
        enviado_por=actor.usuario_id,
        enviado_en=ahora_utc(),
    )
    s.add(anuncio)
    # El ULID se genera al insertar y la etiqueta del push lo lleva.
    s.flush()

    correos = {
        u.id: u.email
        for u in s.scalars(select(Usuario).where(Usuario.id.in_([a.usuario_id for a in elegidas])))
    }

    for alumna in elegidas:
        s.add(
            Notificacion(
                coach_id=actor.coach_id,
                destinatario_id=alumna.usuario_id,
                tipo=Aviso.MENSAJE_DE_COACH.value,
                payload={"titulo": titulo, "cuerpo": texto},
                canal="push",
                enviada_en=ahora_utc(),
                anuncio_id=anuncio.id,
            )
        )
        cola.encolar(
            s,
            Aviso.MENSAJE_DE_COACH,
            coach_id=actor.coach_id,
            llave=f"anuncio:{anuncio.ulid}:{alumna.id}",
            para=correos.get(alumna.usuario_id, ""),
            contexto={
                "titulo": titulo,
                "cuerpo": texto,
                # Sin etiqueta propia, dos frases seguidas se pisarían en la bandeja.
                "etiqueta": f"anuncio:{anuncio.ulid}",
            },
            destinatario_id=alumna.usuario_id,
        )

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="coach",
        accion=bitacora.Accion.ANUNCIO_ENVIADO,
        entidad="anuncio",
        entidad_id=anuncio.id,
        detalle={"destinatarias": len(elegidas)},
    )

    return _publico(s, anuncio)


@ruteador.get("/coach/anuncios", response_model=list[AnuncioPublico])
def anuncios_enviados(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
    limite: Annotated[int, Query(ge=1, le=HISTORIAL)] = HISTORIAL,
) -> list[AnuncioPublico]:
    _ = actor
    filas = s.scalars(select(Anuncio).order_by(Anuncio.enviado_en.desc()).limit(limite)).all()
    return [_publico(s, a) for a in filas]


# ---------------------------------------------------------------------------
# Lado de la alumna
# ---------------------------------------------------------------------------


@ruteador.get("/mi/avisos", response_model=list[AvisoDeAlumna])
def mis_avisos(
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> list[AvisoDeAlumna]:
    """Los avisos que le mandó su coach. Abrir la pantalla los marca como leídos."""
    filas = list(
        s.scalars(
            select(Notificacion)
            .where(Notificacion.destinatario_id == actor.usuario_id)
            .order_by(Notificacion.creado_en.desc())
        ).all()
    )

    salida: list[AvisoDeAlumna] = []
    for n in filas:
        payload = dict(n.payload)
        salida.append(
            AvisoDeAlumna(
                ulid=n.ulid,
                titulo=str(payload.get("titulo", "Aviso de tu coach")),
                cuerpo=str(payload.get("cuerpo", "")),
                recibido_en=n.enviada_en or n.creado_en,
                leido_en=n.leida_en,
            )
        )
        if n.leida_en is None:
            n.leida_en = ahora_utc()

    return salida
