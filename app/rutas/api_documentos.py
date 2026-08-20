"""Descarga de documentos: plan de nutrición, rutina, recibo y el expediente completo.

La alumna descarga los suyos; la coach, los de sus alumnas. En ambos casos el `coach_id`
sale de la sesión, así que un ULID ajeno simplemente no existe.

Cada descarga de un documento con datos de salud deja fila en `acceso_sensible`: es
obligación del Anexo Legal §6, y una descarga es precisamente el momento en que el dato sale
de la plataforma.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.datos.modelos import Alumna, Coach
from app.datos.repos import consultas as q
from app.rutas.sesion import Actor, RutaQueConfirma, actor_actual, datos
from app.servicios import almacenamiento, bitacora, pdf
from app.servicios import expediente as exp
from app.servicios.almacenamiento import almacen

ruteador = APIRouter(prefix="/api/documentos", tags=["documentos"], route_class=RutaQueConfirma)


def _respuesta(documento: pdf.Documento) -> Response:
    return Response(
        content=documento.contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{documento.nombre}"'},
    )


def _marca(s: Session, coach_id: int) -> pdf.Marca:
    """El documento sale con la marca de la coach. Si no subió logo, va solo el nombre."""
    coach = s.get(Coach, coach_id)
    if coach is None:  # pragma: no cover - defensivo
        return pdf.Marca(nombre="")

    logo: bytes | None = None
    if coach.logo_key:
        try:
            logo = almacen().leer(coach.logo_key)
        except FileNotFoundError:
            logo = None

    return pdf.Marca(
        nombre=coach.marca or coach.nombre,
        logo=logo,
        color=coach.color_acento,
    )


def _alumna_visible(s: Session, actor: Actor, ulid: str | None) -> Alumna:
    """La alumna descarga lo suyo; la coach, lo de cualquiera de su cartera."""
    if actor.es_alumna:
        propia = q.alumna_de_usuario(s, actor.usuario_id)
        if propia is None:
            raise ErrorDeDominio(Codigo.SIN_PERMISO)
        # Una alumna que pide el ULID de otra no obtiene 403 sino sus propios datos, porque
        # el parámetro sencillamente se ignora para su rol.
        return propia

    if not ulid:
        raise HTTPException(422, "Falta la alumna")
    alumna = q.alumna_por_ulid(s, ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")
    return alumna


@ruteador.get("/plan-nutricion", response_class=Response)
def plan_nutricion(
    actor: Annotated[Actor, Depends(actor_actual)],
    s: Annotated[Session, Depends(datos)],
    alumna_ulid: str | None = None,
) -> Response:
    alumna = _alumna_visible(s, actor, alumna_ulid)
    ciclo = q.ciclo_vigente(s, alumna.id)
    if ciclo is None:
        raise HTTPException(404, "Todavía no hay ciclo")

    planes = q.planes_del_ciclo(s, alumna.id, ciclo.id)
    plan = planes.get("nutricion")
    if plan is None:
        raise HTTPException(404, "Todavía no hay plan de nutrición publicado")

    historial = q.historial_vigente(s, alumna.id)
    coach = s.get(Coach, actor.coach_id)
    contenido = plan.contenido or {}

    # Una descarga es justo el momento en que el dato sale de la plataforma.
    bitacora.registrar_acceso(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        alumna_id=alumna.id,
        recurso=bitacora.Recurso.PDF_NUTRICION,
    )

    return _respuesta(
        pdf.plan_de_nutricion(
            alumna=alumna.nombre,
            coach=coach.nombre if coach else "",
            marca=_marca(s, actor.coach_id),
            ciclo=ciclo.numero,
            kcal=plan.kcal_objetivo or 0,
            proteina_g=plan.proteina_g or 0,
            carbohidrato_g=plan.carbohidrato_g or 0,
            grasa_g=plan.grasa_g or 0,
            tiempos=contenido.get("tiempos", []),
            notas=contenido.get("notas"),
            restricciones=historial.restricciones if historial else None,
        )
    )


@ruteador.get("/rutina", response_class=Response)
def rutina(
    actor: Annotated[Actor, Depends(actor_actual)],
    s: Annotated[Session, Depends(datos)],
    alumna_ulid: str | None = None,
) -> Response:
    alumna = _alumna_visible(s, actor, alumna_ulid)
    ciclo = q.ciclo_vigente(s, alumna.id)
    if ciclo is None:
        raise HTTPException(404, "Todavía no hay ciclo")

    plan = q.planes_del_ciclo(s, alumna.id, ciclo.id).get("entrenamiento")
    if plan is None:
        raise HTTPException(404, "Todavía no hay rutina publicada")

    historial = q.historial_vigente(s, alumna.id)
    coach = s.get(Coach, actor.coach_id)
    contenido = plan.contenido or {}

    bitacora.registrar_acceso(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        alumna_id=alumna.id,
        recurso=bitacora.Recurso.PDF_RUTINA,
    )

    return _respuesta(
        pdf.rutina(
            alumna=alumna.nombre,
            coach=coach.nombre if coach else "",
            marca=_marca(s, actor.coach_id),
            ciclo=ciclo.numero,
            plantilla=contenido.get("plantilla"),
            dias=contenido.get("dias", []),
            notas=contenido.get("notas"),
            lesiones=historial.lesiones if historial else None,
        )
    )


@ruteador.get("/evolucion", response_class=Response)
def evolucion(
    actor: Annotated[Actor, Depends(actor_actual)],
    s: Annotated[Session, Depends(datos)],
    alumna_ulid: str | None = None,
) -> Response:
    """El historial de chequeos en papel. Sin fotografías: se quedan en la plataforma."""
    alumna = _alumna_visible(s, actor, alumna_ulid)
    chequeos = [c for c in q.chequeos_de(s, alumna.id) if c.estado == "validado"]
    coach = s.get(Coach, actor.coach_id)

    bitacora.registrar_acceso(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        alumna_id=alumna.id,
        recurso=bitacora.Recurso.EXPEDIENTE,
    )

    pesos = q.peso_de_chequeo(s, [c.id for c in chequeos])
    medidas = q.medidas_de(s, [c.id for c in chequeos])

    filas = [
        {
            "numero": i + 1,
            "fecha": f"{c.fecha:%d/%m/%Y}",
            "peso_kg": pesos.get(c.id),
            "porcentaje_grasa": (c.porcentaje_grasa * 100) if c.porcentaje_grasa else None,
            "medidas": medidas.get(c.id, {}),
        }
        for i, c in enumerate(chequeos)
    ]
    tipos = sorted({t for m in medidas.values() for t in m})

    return _respuesta(
        pdf.evolucion(
            alumna=alumna.nombre,
            coach=coach.nombre if coach else "",
            marca=_marca(s, actor.coach_id),
            chequeos=filas,
            medidas=tipos,
            feedback=chequeos[-1].feedback if chequeos else None,
        )
    )


@ruteador.get("/recibo/{pago_ulid}", response_class=Response)
def recibo(
    pago_ulid: str,
    actor: Annotated[Actor, Depends(actor_actual)],
    s: Annotated[Session, Depends(datos)],
) -> Response:
    from sqlalchemy import select

    from app.datos.modelos import Ciclo, Pago

    pago = s.scalars(select(Pago).where(Pago.ulid == pago_ulid)).first()
    if pago is None:
        raise HTTPException(404, "No existe ese pago")

    # Solo se emite recibo de lo cobrado: uno de un pago sin validar diría que se recibió
    # dinero que todavía no se confirmó.
    if pago.estado != "validado":
        raise HTTPException(409, "Ese pago todavía no ha sido validado")

    alumna = s.get(Alumna, pago.alumna_id)
    ciclo = s.get(Ciclo, pago.ciclo_id)
    coach = s.get(Coach, actor.coach_id)
    if alumna is None or ciclo is None:  # pragma: no cover - defensivo
        raise HTTPException(404, "Datos incompletos")

    if actor.es_alumna:
        propia = q.alumna_de_usuario(s, actor.usuario_id)
        if propia is None or propia.id != alumna.id:
            raise ErrorDeDominio(Codigo.SIN_PERMISO)

    bitacora.registrar_acceso(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        alumna_id=alumna.id,
        recurso=bitacora.Recurso.EXPEDIENTE,
    )

    return _respuesta(
        pdf.recibo(
            folio=pago.ulid[-8:].upper(),
            alumna=alumna.nombre,
            coach=coach.nombre if coach else "",
            marca=_marca(s, actor.coach_id),
            concepto=f"Ciclo {ciclo.numero} de acompañamiento",
            monto=pago.monto,
            metodo=pago.metodo or "Transferencia",
            pagado_el=(pago.validado_en or pago.creado_en).date(),
            vigencia_inicia=ciclo.inicia_en,
            vigencia_termina=ciclo.termina_en,
        )
    )


@ruteador.get("/expediente", response_class=Response)
def expediente(
    actor: Annotated[Actor, Depends(actor_actual)],
    s: Annotated[Session, Depends(datos)],
    alumna_ulid: str | None = None,
) -> Response:
    """Todo lo suyo en un ZIP: las fotos que siguen vivas y el historial en PDF.

    Es la salida que la plataforma le promete cuando avisa de una purga o de una baja. Se
    arma en memoria porque son unas pocas decenas de imágenes ya recortadas; un expediente
    de años sigue pesando menos que un video corto.

    Las que ya se purgaron no aparecen ni dejan hueco: la fila existe para la bitácora, pero
    el archivo no está y anunciarlo en el ZIP solo confundiría.
    """
    alumna = _alumna_visible(s, actor, alumna_ulid)
    coach = s.get(Coach, actor.coach_id)
    chequeos = [c for c in q.chequeos_de(s, alumna.id) if c.estado == "validado"]

    bitacora.registrar_acceso(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        alumna_id=alumna.id,
        recurso=bitacora.Recurso.EXPEDIENTE,
    )

    pesos = q.peso_de_chequeo(s, [c.id for c in chequeos])
    medidas = q.medidas_de(s, [c.id for c in chequeos])
    filas = [
        {
            "numero": i + 1,
            "fecha": f"{c.fecha:%d/%m/%Y}",
            "peso_kg": pesos.get(c.id),
            "porcentaje_grasa": (c.porcentaje_grasa * 100) if c.porcentaje_grasa else None,
            "medidas": medidas.get(c.id, {}),
        }
        for i, c in enumerate(chequeos)
    ]

    historial = pdf.evolucion(
        alumna=alumna.nombre,
        coach=coach.nombre if coach else "",
        marca=_marca(s, actor.coach_id),
        chequeos=filas,
        medidas=sorted({t for m in medidas.values() for t in m}),
        feedback=chequeos[-1].feedback if chequeos else None,
    )

    piezas = [exp.Pieza("historial.pdf", historial.contenido)]
    for i, chequeo in enumerate(chequeos, start=1):
        carpeta = exp.carpeta_de_chequeo(i, f"{chequeo.fecha:%Y-%m-%d}")
        for foto in q.fotos_de(s, chequeo.id):
            if foto.storage_key is None or foto.purgada_en is not None:
                continue
            # La llave lleva el inquilino en el prefijo, igual que al servir una suelta.
            if not almacenamiento.pertenece_a(foto.storage_key, actor.coach_id):
                continue
            try:
                imagen = almacen().leer(foto.storage_key)
            except Exception:  # pragma: no cover - un archivo perdido no tumba la descarga
                continue
            piezas.append(exp.Pieza(f"{carpeta}/{foto.angulo}.webp", imagen))

    nombre = f"expediente-{alumna.nombre.split()[0].lower()}.zip"
    return Response(
        content=exp.empaquetar(piezas),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
