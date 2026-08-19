"""Fotos de comida: las sube la alumna, las mira su coach, se borran a las 36 horas.

La frecuencia la elige la coach al armar el plan de nutrición. Si no pide fotos, a la alumna
no se le pide nada: la pantalla ni siquiera aparece.

**La vigencia se comprueba en cada lectura, no solo al purgar.** El trabajo que borra los
bytes puede caerse; lo que no puede pasar es que una foto siga viéndose pasadas sus 36 horas.
Por eso la consulta filtra por fecha aunque el archivo siga en disco.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.datos.modelos import Alumna, FotoDeComida, Plan
from app.datos.repos import consultas as q
from app.dominio import fotos_de_comida as dominio
from app.rutas import archivos
from app.rutas.esquemas import (
    ComentarioDeFoto,
    FotoDeComidaPublica,
    FotosDeComidaDeAlumna,
)
from app.rutas.sesion import Actor, RutaQueConfirma, actor_actual, datos, solo_alumna, solo_coach
from app.servicios import almacenamiento, bitacora, imagenes
from app.servicios.almacenamiento import almacen

ruteador = APIRouter(prefix="/api", tags=["fotos de comida"], route_class=RutaQueConfirma)

#: Tope por periodo. Suficiente para tres comidas y un antojo; evita que una tarde de
#: aburrimiento llene el disco.
MAXIMO_POR_PERIODO = 12


def _mi_alumna(s: Session, actor: Actor) -> Alumna:
    alumna = q.alumna_de_usuario(s, actor.usuario_id)
    if alumna is None:
        raise ErrorDeDominio(Codigo.SIN_PERMISO)
    return alumna


def _vigentes(s: Session, alumna_id: int) -> list[FotoDeComida]:
    """Las que siguen vivas. El corte va en la consulta: una foto vencida no existe."""
    corte = ahora_utc() - dominio.VIGENCIA
    return list(
        s.scalars(
            select(FotoDeComida)
            .where(
                FotoDeComida.alumna_id == alumna_id,
                FotoDeComida.purgada_en.is_(None),
                FotoDeComida.subida_en > corte,
            )
            .order_by(FotoDeComida.subida_en.desc())
        )
    )


def _publica(f: FotoDeComida) -> FotoDeComidaPublica:
    return FotoDeComidaPublica(
        ulid=f.ulid,
        subida_en=f.subida_en,
        expira_en=dominio.expira_en(f.subida_en),
        tiempo=f.tiempo,
        nota=f.nota,
        comentario=f.comentario,
    )


def _plan_de_nutricion(s: Session, alumna_id: int) -> Plan | None:
    ciclo = q.ciclo_vigente(s, alumna_id)
    if ciclo is None:
        return None
    return q.planes_del_ciclo(s, alumna_id, ciclo.id).get("nutricion")


def _frecuencia(plan: Plan | None) -> dominio.Frecuencia:
    if plan is None:
        return dominio.Frecuencia.NINGUNA
    try:
        return dominio.Frecuencia(plan.frecuencia_fotos)
    except ValueError:  # pragma: no cover - defensivo ante un valor viejo
        return dominio.Frecuencia.NINGUNA


def _referencia(plan: Plan | None, alumna: Alumna) -> date:
    """Desde cuándo se cuentan los periodos: el día en que se publicó su plan."""
    if plan is not None and plan.publicado_en is not None:
        return plan.publicado_en.date()
    return alumna.creado_en.date()


# ---------------------------------------------------------------------------
# Lado de la alumna
# ---------------------------------------------------------------------------


@ruteador.get("/mi/fotos-comida", response_model=FotosDeComidaDeAlumna)
def mis_fotos(
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> FotosDeComidaDeAlumna:
    alumna = _mi_alumna(s, actor)
    plan = _plan_de_nutricion(s, alumna.id)
    frecuencia = _frecuencia(plan)
    fotos = _vigentes(s, alumna.id)

    pendiente = dominio.estado(
        frecuencia,
        _referencia(plan, alumna),
        ahora_utc().date(),
        [f.subida_en.date() for f in fotos],
    )

    return FotosDeComidaDeAlumna(
        frecuencia=frecuencia.value,
        rotulo=dominio.ROTULO[frecuencia],
        desde=pendiente.desde if pendiente else None,
        hasta=pendiente.hasta if pendiente else None,
        cumplido=pendiente.cumplido if pendiente else False,
        fotos=[_publica(f) for f in fotos],
    )


@ruteador.post("/mi/fotos-comida", response_model=FotoDeComidaPublica, status_code=201)
async def subir_foto(
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
    archivo: Annotated[UploadFile, File()],
    tiempo: Annotated[str, Form()] = "",
    nota: Annotated[str, Form()] = "",
) -> FotoDeComidaPublica:
    """Sube la foto de un plato.

    Se reencoda a WebP, y eso **borra el EXIF**: una foto de teléfono trae dentro la
    coordenada de dónde se tomó, y eso es la casa de la alumna.
    """
    alumna = _mi_alumna(s, actor)
    plan = _plan_de_nutricion(s, alumna.id)
    if _frecuencia(plan) is dominio.Frecuencia.NINGUNA:
        raise HTTPException(409, "Tu coach no te está pidiendo fotos de tus comidas")

    if len(_vigentes(s, alumna.id)) >= MAXIMO_POR_PERIODO:
        raise HTTPException(409, f"Ya subiste {MAXIMO_POR_PERIODO} fotos; espera a que expiren")

    try:
        contenido = imagenes.comida(await archivo.read())
    except imagenes.ImagenInvalida as causa:
        raise HTTPException(422, str(causa)) from causa

    foto = FotoDeComida(
        coach_id=actor.coach_id,
        alumna_id=alumna.id,
        subida_en=ahora_utc(),
        tiempo=tiempo.strip()[:60] or None,
        nota=nota.strip()[:1000] or None,
    )
    s.add(foto)
    # El ULID se genera al insertar y la llave lo lleva, así que hay que forzar el flush
    # antes de escribir el archivo.
    s.flush()

    llave = almacenamiento.llave_de_foto_de_comida(actor.coach_id, alumna.id, foto.ulid)
    almacen().guardar(llave, contenido)
    foto.storage_key = llave
    s.flush()

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="alumna",
        accion=bitacora.Accion.FOTO_SUBIDA,
        entidad="foto_de_comida",
        entidad_id=foto.id,
        detalle={"campos_cambiados": "foto_de_comida"},
    )

    return _publica(foto)


@ruteador.delete("/mi/fotos-comida/{ulid}", status_code=204)
def borrar_foto(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    """La alumna se arrepiente. Se borra ya, sin esperar las 36 horas."""
    alumna = _mi_alumna(s, actor)
    foto = s.scalars(select(FotoDeComida).where(FotoDeComida.ulid == ulid)).first()
    if foto is None or foto.alumna_id != alumna.id:
        raise HTTPException(404, "No existe esa foto")

    if foto.storage_key:
        almacen().borrar(foto.storage_key)
    foto.storage_key = None
    foto.purgada_en = ahora_utc()
    s.flush()

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="alumna",
        accion=bitacora.Accion.FOTO_ELIMINADA,
        entidad="foto_de_comida",
        entidad_id=foto.id,
        detalle={"campos_cambiados": "borrada_por_la_alumna"},
    )


# ---------------------------------------------------------------------------
# Lado de la coach
# ---------------------------------------------------------------------------


@ruteador.get("/coach/alumnas/{alumna_ulid}/fotos-comida", response_model=list[FotoDeComidaPublica])
def fotos_de_alumna(
    alumna_ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> list[FotoDeComidaPublica]:
    alumna = q.alumna_por_ulid(s, alumna_ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")

    bitacora.registrar_acceso(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        alumna_id=alumna.id,
        recurso=bitacora.Recurso.FOTO,
    )

    return [_publica(f) for f in _vigentes(s, alumna.id)]


@ruteador.post("/coach/fotos-comida/{ulid}/comentario", response_model=FotoDeComidaPublica)
def comentar(
    ulid: str,
    cuerpo: ComentarioDeFoto,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> FotoDeComidaPublica:
    """Lo que la coach le contesta. Sobrevive a la foto: el comentario no caduca."""
    _ = actor
    foto = s.scalars(select(FotoDeComida).where(FotoDeComida.ulid == ulid)).first()
    if foto is None:
        raise HTTPException(404, "No existe esa foto")

    foto.comentario = cuerpo.comentario.strip()[:1000] or None
    s.flush()
    return _publica(foto)


@ruteador.get("/fotos-comida/{ulid}/imagen")
def ver_imagen(
    ulid: str,
    actor: Annotated[Actor, Depends(actor_actual)],
    s: Annotated[Session, Depends(datos)],
) -> Response:
    """La imagen. La ven la coach y la propia alumna, y solo mientras esté vigente."""
    foto = s.scalars(select(FotoDeComida).where(FotoDeComida.ulid == ulid)).first()
    if foto is None or foto.storage_key is None or foto.purgada_en is not None:
        raise HTTPException(404, "Esa foto ya no está")

    # El corte va aquí también: si el trabajo de purga se retrasó, la foto igual no se sirve.
    if dominio.vencida(foto.subida_en, ahora_utc()):
        raise HTTPException(404, "Esa foto ya expiró")

    if actor.es_alumna:
        propia = q.alumna_de_usuario(s, actor.usuario_id)
        if propia is None or propia.id != foto.alumna_id:
            raise ErrorDeDominio(Codigo.SIN_PERMISO)
    elif not actor.es_coach:
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    if not almacenamiento.pertenece_a(foto.storage_key, actor.coach_id):
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    return archivos.servir(foto.storage_key)
