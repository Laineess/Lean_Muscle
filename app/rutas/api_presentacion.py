"""Presentación de la coach: la escribe ella, la lee su alumna nueva.

Va antes del cuestionario. Se le piden lesiones, medicación y peso a alguien que todavía no
sabe con quién está hablando, y presentarse primero es lo que convierte ese formulario en
una conversación.

El texto y la ficha son suyos por completo: la plataforma no impone ni un rótulo.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.datos.modelos import Coach, PresentacionCoach
from app.rutas import archivos
from app.rutas.esquemas import (
    DatoDeFicha,
    EdicionDePresentacion,
    PresentacionPublica,
)
from app.rutas.sesion import Actor, RutaQueConfirma, actor_actual, datos, solo_alumna, solo_coach
from app.servicios import almacenamiento, imagenes
from app.servicios.almacenamiento import almacen

ruteador = APIRouter(prefix="/api", tags=["presentacion"], route_class=RutaQueConfirma)

#: Tope del texto libre. Suficiente para dos o tres párrafos; más que eso nadie lo lee antes
#: de un formulario.
LIMITE_TEXTO = 4000
LIMITE_FICHA = 8


def _fila(s: Session, coach_id: int) -> PresentacionCoach | None:
    return s.scalars(
        select(PresentacionCoach).where(PresentacionCoach.coach_id == coach_id)
    ).first()


def _publica(fila: PresentacionCoach | None, coach: Coach | None) -> PresentacionPublica:
    return PresentacionPublica(
        titulo=fila.titulo if fila else "",
        texto=fila.texto if fila else "",
        ficha=[DatoDeFicha(**d) for d in (fila.ficha if fila else [])],
        # Sin fila todavía no hay nada que enseñar: se trata como apagada.
        activa=bool(fila and fila.activa),
        tiene_foto=bool(fila and fila.foto_key),
        marca=(coach.marca or coach.nombre) if coach else "",
        color_acento=coach.color_acento if coach else "#c9a227",
        color_secundario=coach.color_secundario if coach else "#0e3b2b",
    )


# ---------------------------------------------------------------------------
# Lado de la coach
# ---------------------------------------------------------------------------


@ruteador.get("/coach/presentacion", response_model=PresentacionPublica)
def mi_presentacion(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> PresentacionPublica:
    return _publica(_fila(s, actor.coach_id), s.get(Coach, actor.coach_id))


@ruteador.put("/coach/presentacion", response_model=PresentacionPublica)
def guardar_presentacion(
    cuerpo: EdicionDePresentacion,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> PresentacionPublica:
    """Una por coach: si ya existe se actualiza, y el UNIQUE evita el duplicado."""
    if len(cuerpo.texto) > LIMITE_TEXTO:
        raise HTTPException(422, "El texto es demasiado largo")
    if len(cuerpo.ficha) > LIMITE_FICHA:
        raise HTTPException(422, f"La ficha admite hasta {LIMITE_FICHA} datos")

    fila = _fila(s, actor.coach_id)
    if fila is None:
        fila = PresentacionCoach(coach_id=actor.coach_id)
        s.add(fila)

    fila.titulo = cuerpo.titulo.strip()[:160]
    fila.texto = cuerpo.texto.strip()
    fila.ficha = [
        {"rotulo": d.rotulo.strip()[:60], "valor": d.valor.strip()[:200]}
        for d in cuerpo.ficha
        if d.rotulo.strip() and d.valor.strip()
    ]
    fila.activa = cuerpo.activa
    s.flush()

    return _publica(fila, s.get(Coach, actor.coach_id))


@ruteador.put("/coach/presentacion/foto", response_model=PresentacionPublica)
async def subir_foto(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
    archivo: Annotated[UploadFile, File()],
) -> PresentacionPublica:
    """Su foto. Se cuadra y se reescala, no se recorta la cara: aquí la cara es el punto."""
    fila = _fila(s, actor.coach_id)
    if fila is None:
        fila = PresentacionCoach(coach_id=actor.coach_id)
        s.add(fila)
        s.flush()

    try:
        contenido = imagenes.logo(await archivo.read())
    except imagenes.ImagenInvalida as causa:
        raise HTTPException(422, str(causa)) from causa

    llave = almacenamiento.llave_de_foto_de_coach(actor.coach_id)
    almacen().guardar(llave, contenido)
    fila.foto_key = llave
    s.flush()

    return _publica(fila, s.get(Coach, actor.coach_id))


# ---------------------------------------------------------------------------
# Lado de la alumna
# ---------------------------------------------------------------------------


@ruteador.get("/mi/presentacion", response_model=PresentacionPublica)
def presentacion_de_mi_coach(
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> PresentacionPublica:
    return _publica(_fila(s, actor.coach_id), s.get(Coach, actor.coach_id))


@ruteador.get("/presentacion/foto")
def foto_de_coach(
    actor: Annotated[Actor, Depends(actor_actual)],
    s: Annotated[Session, Depends(datos)],
) -> Response:
    """La foto de la coach de quien pregunta. No hace falta identificarla: es la suya."""
    fila = _fila(s, actor.coach_id)
    if fila is None or fila.foto_key is None:
        raise HTTPException(404, "Todavía no hay foto")
    return archivos.servir(fila.foto_key)
