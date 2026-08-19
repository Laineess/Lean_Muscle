"""Comprobantes de pago: los sube la alumna, los revisa la coach.

El comprobante cuelga del cobro programado, no del ciclo. La alumna elige de sus pendientes
cuál está pagando, así que la coach lo recibe ya emparejado y solo confirma contra su estado
de cuenta.

**El OCR sugiere, no valida.** Un comprobante es una imagen que cualquiera puede editar, y
ningún grado de confianza automática sustituye a que alguien mire el banco. Por eso el cobro
pasa por `en_revision` y no salta directo a `pagado`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.datos.modelos import Alumna, Coach, CobroProgramado, MovimientoFinanciero, Usuario
from app.datos.repos import consultas as q
from app.dominio.avisos import Aviso
from app.rutas import archivos
from app.rutas.api_cobros import MOTIVOS, cobro_publico
from app.rutas.esquemas import CobroDeAlumna, ComprobantePorRevisar, RechazoDeComprobante
from app.rutas.sesion import Actor, RutaQueConfirma, actor_actual, datos, solo_alumna, solo_coach
from app.servicios import almacenamiento, bitacora, imagenes, ocr
from app.servicios import avisos as cola
from app.servicios.almacenamiento import almacen

ruteador = APIRouter(prefix="/api", tags=["comprobantes"], route_class=RutaQueConfirma)


def _mi_alumna(s: Session, actor: Actor) -> Alumna:
    alumna = q.alumna_de_usuario(s, actor.usuario_id)
    if alumna is None:
        raise ErrorDeDominio(Codigo.SIN_PERMISO)
    return alumna


# ---------------------------------------------------------------------------
# Lado de la alumna
# ---------------------------------------------------------------------------


@ruteador.get("/mi/cobros", response_model=list[CobroDeAlumna])
def mis_cobros(
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> list[CobroDeAlumna]:
    """Lo que le toca pagar. Es la lista de la que elige al subir un comprobante."""
    alumna = _mi_alumna(s, actor)
    hoy = ahora_utc().date()
    return [cobro_publico(c, hoy) for c in q.cobros_de(s, alumna.id)]


@ruteador.post("/mi/cobros/{ulid}/comprobante", response_model=CobroDeAlumna)
async def subir_comprobante(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
    archivo: Annotated[UploadFile, File()],
) -> CobroDeAlumna:
    """Sube el comprobante de un cobro concreto y lo deja en revisión.

    El OCR lee monto, fecha, referencia y banco para que la coach compare de un vistazo. No
    decide nada: el cobro queda `en_revision` hasta que ella confirma.
    """
    alumna = _mi_alumna(s, actor)
    cobro = q.cobro_por_ulid(s, ulid)
    if cobro is None or cobro.alumna_id != alumna.id:
        raise HTTPException(404, "No existe ese cobro")
    if cobro.estado == "pagado":
        raise HTTPException(409, "Ese cobro ya está pagado")

    contenido = await archivo.read()
    if not contenido:
        raise HTTPException(422, "El archivo llegó vacío")
    if len(contenido) > imagenes.BYTES_MAXIMOS:
        raise HTTPException(422, "El comprobante pesa demasiado")

    lectura = ocr.leer(contenido)
    extension = (archivo.filename or "comprobante.jpg").rsplit(".", 1)[-1].lower()[:5]
    llave = almacenamiento.llave_de_comprobante_de_cobro(
        actor.coach_id, alumna.id, cobro.id, extension
    )
    almacen().guardar(llave, contenido)

    cobro.comprobante_key = llave
    cobro.ocr = lectura.como_json()
    cobro.confianza = lectura.confianza
    cobro.subido_en = ahora_utc()
    cobro.estado = "en_revision"
    # Se limpia el rechazo anterior: este comprobante es un intento nuevo.
    cobro.motivo_rechazo = None
    # Se fuerza el SQL aquí, no al cerrar la sesión: si la base rechaza el cambio, el error
    # sale dentro de la petición en lugar de después de haber respondido 200.
    s.flush()

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="alumna",
        accion=bitacora.Accion.COMPROBANTE_SUBIDO,
        entidad="cobro_programado",
        entidad_id=cobro.id,
        detalle={"confianza_ocr": str(lectura.confianza)},
    )

    return cobro_publico(cobro, ahora_utc().date())


# ---------------------------------------------------------------------------
# Bandeja de la coach
# ---------------------------------------------------------------------------


def _fecha_del_ocr(datos_ocr: dict[str, object] | None) -> date | None:
    crudo = (datos_ocr or {}).get("fecha")
    if not crudo:
        return None
    try:
        return date.fromisoformat(str(crudo))
    except ValueError:  # pragma: no cover - el OCR puede devolver cualquier cosa
        return None


@ruteador.get("/coach/comprobantes", response_model=list[ComprobantePorRevisar])
def por_revisar(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> list[ComprobantePorRevisar]:
    """La bandeja. Trae lo esperado y lo leído para ver si cuadra sin abrir cada imagen."""
    _ = actor
    # La cartera no trae solicitudes del registro abierto, y aquí eso es lo que se quiere:
    # su comprobante de inscripción lo valida la coach al aceptarlas, junto con lo demás,
    # no suelto en la bandeja de finanzas.
    alumnas = {a.id: a for a in q.cartera(s)}
    planes = {t.id: t.nombre for t in q.tarifas_de_coach(s)}

    filas: list[ComprobantePorRevisar] = []
    for c in q.comprobantes_por_revisar(s):
        alumna = alumnas.get(c.alumna_id)
        if alumna is None:
            continue

        leido = (c.ocr or {}).get("monto")
        monto_leido = Decimal(str(leido)) if leido not in (None, "") else None

        filas.append(
            ComprobantePorRevisar(
                cobro_ulid=c.ulid,
                alumna_ulid=alumna.ulid,
                alumna=alumna.nombre,
                plan=planes.get(alumna.tarifa_id) if alumna.tarifa_id else None,
                fecha_cobro=c.fecha,
                concepto=c.concepto or MOTIVOS.get(c.motivo, c.motivo),
                monto_esperado=c.monto,
                subido_en=c.subido_en,
                monto_leido=monto_leido,
                fecha_leida=_fecha_del_ocr(c.ocr),
                referencia=(c.ocr or {}).get("referencia"),
                banco=(c.ocr or {}).get("banco"),
                confianza=c.confianza or Decimal(0),
                monto_no_cuadra=monto_leido is not None and monto_leido != c.monto,
            )
        )
    return filas


@ruteador.get("/coach/cobros/{ulid}/comprobante")
def ver_comprobante(
    ulid: str,
    actor: Annotated[Actor, Depends(actor_actual)],
    s: Annotated[Session, Depends(datos)],
) -> Response:
    """La imagen. La ven la coach y la propia alumna, nadie más."""
    cobro = q.cobro_por_ulid(s, ulid)
    if cobro is None or cobro.comprobante_key is None:
        raise HTTPException(404, "Ese cobro no tiene comprobante")

    if actor.es_alumna:
        propia = q.alumna_de_usuario(s, actor.usuario_id)
        if propia is None or propia.id != cobro.alumna_id:
            raise ErrorDeDominio(Codigo.SIN_PERMISO)
    elif not actor.es_coach:
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    if not almacenamiento.pertenece_a(cobro.comprobante_key, actor.coach_id):
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    tipo = "application/pdf" if cobro.comprobante_key.endswith(".pdf") else "image/jpeg"
    return archivos.servir(cobro.comprobante_key, tipo)


@ruteador.post("/coach/cobros/{ulid}/validar", status_code=204)
def validar(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    """Confirma el pago: registra el ingreso, salda el cobro y avisa a la alumna.

    Las tres cosas en el mismo gesto. Que la coach tuviera que acordarse de capturar el
    ingreso aparte es exactamente como acaban sin cuadrar el adeudo y la contabilidad.
    """
    cobro = q.cobro_por_ulid(s, ulid)
    if cobro is None:
        raise HTTPException(404, "No existe ese cobro")
    if cobro.estado == "pagado":
        raise HTTPException(409, "Ese cobro ya estaba saldado")

    hoy = ahora_utc().date()
    movimiento = MovimientoFinanciero(
        coach_id=actor.coach_id,
        tipo="ingreso",
        categoria="consulta" if cobro.motivo == "cita" else "ciclo",
        monto=cobro.monto,
        fecha=hoy,
        concepto=cobro.concepto or MOTIVOS.get(cobro.motivo, cobro.motivo),
        alumna_id=cobro.alumna_id,
        # Nace de validar un comprobante, no de una captura a mano: no se edita a mano.
        automatico=True,
    )
    s.add(movimiento)
    s.flush()

    cobro.estado = "pagado"
    cobro.pagado_en = hoy
    cobro.movimiento_id = movimiento.id
    cobro.revisado_en = ahora_utc()
    cobro.motivo_rechazo = None
    s.flush()

    _avisar(s, actor, cobro, Aviso.PAGO_VALIDADO, hoy)


@ruteador.post("/coach/cobros/{ulid}/rechazar", status_code=204)
def rechazar(
    ulid: str,
    cuerpo: RechazoDeComprobante,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    """Devuelve el cobro a pendiente con el motivo, que la alumna lee tal cual."""
    if not cuerpo.motivo.strip():
        raise ErrorDeDominio(Codigo.MOTIVO_DE_RECHAZO_REQUERIDO)

    cobro = q.cobro_por_ulid(s, ulid)
    if cobro is None:
        raise HTTPException(404, "No existe ese cobro")
    if cobro.estado == "pagado":
        raise HTTPException(409, "Ese cobro ya está saldado")

    cobro.estado = "pendiente"
    cobro.motivo_rechazo = cuerpo.motivo.strip()[:500]
    cobro.revisado_en = ahora_utc()
    s.flush()
    # El archivo se conserva: si hay reclamación después, la imagen es la prueba.

    _avisar(s, actor, cobro, Aviso.PAGO_RECHAZADO, ahora_utc().date())


def _avisar(s: Session, actor: Actor, cobro: CobroProgramado, aviso: Aviso, hoy: date) -> None:
    alumna = s.get(Alumna, cobro.alumna_id)
    if alumna is None:  # pragma: no cover - defensivo
        return

    coach = s.get(Coach, actor.coach_id)
    usuario = s.get(Usuario, alumna.usuario_id)
    cola.encolar(
        s,
        aviso,
        coach_id=actor.coach_id,
        llave=f"cobro:{cobro.ulid}:{aviso.value}:{hoy.isoformat()}",
        para=usuario.email if usuario else "",
        contexto={
            "nombre": alumna.nombre.split(" ")[0],
            "coach": (coach.marca or coach.nombre) if coach else "tu coach",
            "monto": f"{cobro.monto:,.2f}",
            "motivo": cobro.motivo_rechazo or "",
            "concepto": cobro.concepto or MOTIVOS.get(cobro.motivo, cobro.motivo),
        },
        destinatario_id=alumna.usuario_id,
    )
