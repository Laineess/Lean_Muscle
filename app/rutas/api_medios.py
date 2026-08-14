"""Fotografías, comprobantes, notificaciones y mensajería.

Lo que tienen en común: son los flujos donde el dato sensible entra o sale del sistema, así
que aquí es donde más importa el orden de las operaciones.

**La fotografía se recorta antes de tocar el disco.** El archivo que sube la alumna se
procesa en memoria y se descarta; solo persiste la versión sin cabeza ni cuello. No hay un
instante en que exista un original identificable guardado.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.config import ajustes
from app.datos.modelos import Alumna, Foto, Mensaje, SuscripcionPush
from app.datos.repos import consultas as q
from app.dominio.chequeo import Angulo
from app.rutas import archivos
from app.rutas.esquemas import (
    Esquema,
    LlavePush,
    MensajeNuevo,
    MensajePublico,
    SuscripcionNueva,
)
from app.rutas.sesion import Actor, actor_actual, datos, solo_alumna
from app.servicios import almacenamiento, bitacora, imagenes
from app.servicios.almacenamiento import almacen

ruteador = APIRouter(prefix="/api", tags=["medios"])


def _mi_alumna(s: Session, actor: Actor) -> Alumna:
    alumna = q.alumna_de_usuario(s, actor.usuario_id)
    if alumna is None:
        raise ErrorDeDominio(Codigo.SIN_PERMISO)
    return alumna


# ---------------------------------------------------------------------------
# Fotografías
# ---------------------------------------------------------------------------


class FotoSubida(Esquema):
    angulo: str
    estado_auto: str
    motivo_rechazo: str | None
    nitidez: Decimal
    luminancia: Decimal


@ruteador.put("/mi/chequeos/{ulid}/fotos/{angulo}", response_model=FotoSubida)
async def subir_foto(
    ulid: str,
    angulo: str,
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
    archivo: Annotated[UploadFile, File()],
) -> FotoSubida:
    """Sube una fotografía de chequeo.

    El original **nunca se guarda**: se lee en memoria, se recorta la zona de cabeza y cuello,
    se reescala y se convierte a WebP sin metadatos. Lo que llega al disco ya es la versión
    recortada, así que ni siquiera existe una ventana en la que un original identificable
    esté en el servidor.
    """
    if angulo not in {a.value for a in Angulo}:
        raise HTTPException(422, "Ángulo desconocido")

    alumna = _mi_alumna(s, actor)
    chequeo = q.chequeo_por_ulid(s, ulid)
    if chequeo is None or chequeo.alumna_id != alumna.id:
        raise HTTPException(404, "No existe ese chequeo")
    if chequeo.estado not in {"borrador", "rechazado_calidad"}:
        raise HTTPException(409, "Este chequeo ya se envió y no se puede cambiar")

    try:
        procesada = imagenes.procesar(await archivo.read())
    except imagenes.ImagenInvalida as causa:
        raise HTTPException(422, str(causa)) from causa

    llave = almacenamiento.llave_de_foto(actor.coach_id, alumna.id, chequeo.id, angulo)
    mini = almacenamiento.llave_de_miniatura(actor.coach_id, alumna.id, chequeo.id, angulo)
    almacen().guardar(llave, procesada.contenido)
    almacen().guardar(mini, imagenes.miniatura(procesada.contenido))

    fila = s.scalars(
        select(Foto).where(Foto.chequeo_id == chequeo.id, Foto.angulo == angulo)
    ).first()
    if fila is None:
        fila = Foto(coach_id=actor.coach_id, chequeo_id=chequeo.id, angulo=angulo)
        s.add(fila)

    fila.storage_key = llave
    fila.ancho = procesada.ancho
    fila.alto = procesada.alto
    fila.bytes = procesada.bytes
    fila.nitidez = procesada.nitidez
    fila.luminancia = procesada.luminancia
    fila.estado_auto = procesada.estado_auto
    fila.tomada_en = procesada.tomada_en or ahora_utc()
    fila.subida_en = ahora_utc()
    # La primera toma de cada ángulo es la línea base, y se conserva si la alumna lo autoriza.
    fila.es_linea_base = (
        chequeo.ciclo_id is not None
        and not s.scalars(
            select(Foto).where(Foto.angulo == angulo, Foto.es_linea_base.is_(True))
        ).first()
    )

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="alumna",
        accion=bitacora.Accion.FOTO_SUBIDA,
        entidad="foto",
        entidad_id=fila.id,
        detalle={"angulo": angulo, "estado_auto": procesada.estado_auto},
    )

    return FotoSubida(
        angulo=angulo,
        estado_auto=procesada.estado_auto,
        motivo_rechazo=procesada.motivo_rechazo,
        nitidez=procesada.nitidez,
        luminancia=procesada.luminancia,
    )


@ruteador.delete("/mi/chequeos/{ulid}/fotos/{angulo}", status_code=204)
def repetir_captura(
    ulid: str,
    angulo: str,
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    """«Repetir captura». Borra el archivo, no solo la fila."""
    alumna = _mi_alumna(s, actor)
    chequeo = q.chequeo_por_ulid(s, ulid)
    if chequeo is None or chequeo.alumna_id != alumna.id:
        raise HTTPException(404, "No existe ese chequeo")

    fila = s.scalars(
        select(Foto).where(Foto.chequeo_id == chequeo.id, Foto.angulo == angulo)
    ).first()
    if fila is None:
        return

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="alumna",
        accion=bitacora.Accion.FOTO_ELIMINADA,
        entidad="foto",
        entidad_id=fila.id,
        detalle={"angulo": angulo, "motivo": "repetir captura"},
    )

    if fila.storage_key:
        almacen().borrar(fila.storage_key)
        almacen().borrar(fila.storage_key.replace(".webp", "-mini.webp"))
    s.delete(fila)


@ruteador.get("/fotos/{chequeo_ulid}/{angulo}")
def servir_foto(
    chequeo_ulid: str,
    angulo: str,
    actor: Annotated[Actor, Depends(actor_actual)],
    s: Annotated[Session, Depends(datos)],
    mini: bool = False,
) -> Response:
    """Entrega la imagen con `X-Accel-Redirect`.

    Python **no la carga en memoria**: comprueba el permiso, anota el acceso y le dice a
    nginx qué archivo mandar. Servir fotos desde la aplicación satura los trabajadores con
    media docena de alumnas activas.
    """
    chequeo = q.chequeo_por_ulid(s, chequeo_ulid)
    if chequeo is None:
        raise HTTPException(404, "No existe ese chequeo")

    if actor.es_alumna:
        propia = q.alumna_de_usuario(s, actor.usuario_id)
        if propia is None or propia.id != chequeo.alumna_id:
            raise ErrorDeDominio(Codigo.SIN_PERMISO)

    fila = s.scalars(
        select(Foto).where(Foto.chequeo_id == chequeo.id, Foto.angulo == angulo)
    ).first()
    if fila is None or fila.storage_key is None or fila.purgada_en is not None:
        raise HTTPException(404, "Esa foto ya no está disponible")

    # Capa 4 del aislamiento: la llave lleva el inquilino en el prefijo y se comprueba antes
    # de entregar nada. Adivinar una ruta no basta para leer la foto de otra coach.
    if not almacenamiento.pertenece_a(fila.storage_key, actor.coach_id):
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    bitacora.registrar_acceso(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        alumna_id=chequeo.alumna_id,
        recurso=bitacora.Recurso.FOTO,
    )

    llave = fila.storage_key.replace(".webp", "-mini.webp") if mini else fila.storage_key
    return archivos.servir(llave)


# ---------------------------------------------------------------------------
# Comprobantes de pago
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Notificaciones push
# ---------------------------------------------------------------------------


@ruteador.get("/logo")
def servir_logo(
    actor: Annotated[Actor, Depends(actor_actual)],
    s: Annotated[Session, Depends(datos)],
) -> Response:
    """El logo de la marca del inquilino en curso.

    No es dato sensible —es la marca, se enseña a todo el mundo—, así que no deja fila en la
    bitácora de accesos. Sí va tras la sesión: el `coach_id` sale de ella y nadie pide el
    logo de otro inquilino.
    """
    from app.datos.modelos import Coach

    coach = s.get(Coach, actor.coach_id)
    if coach is None or coach.logo_key is None:
        raise HTTPException(404, "Esta marca no tiene logo")

    return archivos.servir(coach.logo_key)


@ruteador.get("/push/llave", response_model=LlavePush)
def llave_de_push(
    actor: Annotated[Actor, Depends(actor_actual)],
) -> LlavePush:
    """La llave pública VAPID que el navegador necesita para suscribirse.

    Es pública por definición —viaja en cada suscripción—, pero se sirve tras la sesión: no
    hace falta publicar de qué servidor de push depende la plataforma a quien no entró.
    """
    _ = actor
    return LlavePush(publica=ajustes().vapid_publica)


@ruteador.post("/mi/push", status_code=204)
def suscribir_push(
    cuerpo: SuscripcionNueva,
    actor: Annotated[Actor, Depends(actor_actual)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    """Registra este navegador.

    Se identifica por el hash del endpoint: una persona puede tener varias suscripciones
    —teléfono, laptop— y volver a suscribir el mismo navegador solo refresca las llaves en
    lugar de duplicar la fila.
    """
    endpoint_hash = hashlib.sha256(cuerpo.endpoint.encode("utf-8")).hexdigest()

    fila = s.scalars(
        select(SuscripcionPush).where(SuscripcionPush.endpoint_hash == endpoint_hash)
    ).first()
    if fila is None:
        fila = SuscripcionPush(
            coach_id=actor.coach_id,
            usuario_id=actor.usuario_id,
            endpoint=cuerpo.endpoint[:500],
            endpoint_hash=endpoint_hash,
            p256dh=cuerpo.p256dh,
            auth=cuerpo.auth,
        )
        s.add(fila)
    else:
        fila.p256dh = cuerpo.p256dh
        fila.auth = cuerpo.auth
        # Un navegador que vuelve a suscribirse está vivo: se le perdonan los fallos viejos.
        fila.fallos = 0


@ruteador.delete("/mi/push", status_code=204)
def desuscribir_push(
    actor: Annotated[Actor, Depends(actor_actual)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    for fila in s.scalars(
        select(SuscripcionPush).where(SuscripcionPush.usuario_id == actor.usuario_id)
    ):
        s.delete(fila)


# ---------------------------------------------------------------------------
# Mensajería
# ---------------------------------------------------------------------------


def _mensajes_publicos(filas: list[Mensaje]) -> list[MensajePublico]:
    return [
        MensajePublico(
            ulid=m.ulid,
            autor=m.autor,
            cuerpo=m.cuerpo,
            enviado_en=m.enviado_en,
            leido_en=m.leido_en,
        )
        for m in filas
    ]


def _hilo(s: Session, alumna_id: int) -> list[Mensaje]:
    return list(
        s.scalars(
            select(Mensaje).where(Mensaje.alumna_id == alumna_id).order_by(Mensaje.enviado_en)
        ).all()
    )


@ruteador.get("/mi/mensajes", response_model=list[MensajePublico])
def mis_mensajes(
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> list[MensajePublico]:
    alumna = _mi_alumna(s, actor)
    filas = _hilo(s, alumna.id)

    # Abrir el hilo marca como leídos los de la coach, no los propios.
    for m in filas:
        if m.autor == "coach" and m.leido_en is None:
            m.leido_en = ahora_utc()

    return _mensajes_publicos(filas)


@ruteador.post("/mi/mensajes", response_model=MensajePublico, status_code=201)
def escribir_a_mi_coach(
    cuerpo: MensajeNuevo,
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> MensajePublico:
    if not cuerpo.cuerpo.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)

    alumna = _mi_alumna(s, actor)
    mensaje = Mensaje(
        coach_id=actor.coach_id,
        alumna_id=alumna.id,
        autor="alumna",
        cuerpo=cuerpo.cuerpo.strip()[:4000],
        enviado_en=ahora_utc(),
    )
    s.add(mensaje)
    s.flush()
    return _mensajes_publicos([mensaje])[0]


@ruteador.get("/coach/mensajes/{alumna_ulid}", response_model=list[MensajePublico])
def hilo_de_alumna(
    alumna_ulid: str,
    actor: Annotated[Actor, Depends(actor_actual)],
    s: Annotated[Session, Depends(datos)],
) -> list[MensajePublico]:
    if not actor.es_coach:
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    alumna = q.alumna_por_ulid(s, alumna_ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")

    filas = _hilo(s, alumna.id)
    for m in filas:
        if m.autor == "alumna" and m.leido_en is None:
            m.leido_en = ahora_utc()

    return _mensajes_publicos(filas)


@ruteador.post("/coach/mensajes/{alumna_ulid}", response_model=MensajePublico, status_code=201)
def responder_a_alumna(
    alumna_ulid: str,
    cuerpo: MensajeNuevo,
    actor: Annotated[Actor, Depends(actor_actual)],
    s: Annotated[Session, Depends(datos)],
) -> MensajePublico:
    if not actor.es_coach:
        raise ErrorDeDominio(Codigo.SIN_PERMISO)
    if not cuerpo.cuerpo.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)

    alumna = q.alumna_por_ulid(s, alumna_ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")

    mensaje = Mensaje(
        coach_id=actor.coach_id,
        alumna_id=alumna.id,
        autor="coach",
        cuerpo=cuerpo.cuerpo.strip()[:4000],
        enviado_en=ahora_utc(),
    )
    s.add(mensaje)
    s.flush()
    return _mensajes_publicos([mensaje])[0]


_ = datetime  # usado en las anotaciones de los esquemas
