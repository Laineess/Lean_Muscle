"""Planes comerciales y cobros programados: la coach crea planes con su precio y marca en un
calendario cuándo debe pagar cada alumna.

Un cobro vencido y sin pagar pausa el plan. Es la única palanca de cobro, y por eso vive en
el cobro y no en el ciclo: el ciclo mide el método, no el dinero.

El plan comercial se guarda en `tarifa`; hacia afuera se llama plan porque `Plan` ya es el
de nutrición y entrenamiento.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.datos.modelos import CobroProgramado, Servicio, Tarifa
from app.datos.repos import consultas as q
from app.rutas.esquemas import (
    AlumnaConCobros,
    CitaDeAlumna,
    CobroDeAlumna,
    CobroNuevoProgramado,
    PlanComercial,
    PlanComercialNuevo,
    ServicioNuevo,
    ServicioPublico,
)
from app.rutas.sesion import Actor, RutaQueConfirma, datos, solo_coach

ruteador = APIRouter(prefix="/api/coach", tags=["cobros"], route_class=RutaQueConfirma)

INTENSIDADES = {"baja", "media", "alta"}

#: Qué se cobra. El rótulo es lo que lee la alumna cuando la coach no escribe concepto.
MOTIVOS: dict[str, str] = {
    "inscripcion": "Inscripción",
    "mensualidad": "Mensualidad del plan",
    "cita": "Consulta",
    "material": "Material",
    "otro": "Otro concepto",
}


# ---------------------------------------------------------------------------
# Planes comerciales
# ---------------------------------------------------------------------------


def _plan_publico(t: Tarifa, alumnas: int) -> PlanComercial:
    return PlanComercial(
        ulid=t.ulid,
        codigo=t.codigo,
        nombre=t.nombre,
        descripcion=t.descripcion,
        precio=t.precio,
        dias=t.dias,
        intensidad=t.intensidad,
        activa=t.activa,
        alumnas=alumnas,
    )


def _cuantas_por_plan(s: Session) -> dict[int, int]:
    conteo: dict[int, int] = {}
    for a in q.cartera(s):
        if a.tarifa_id is not None:
            conteo[a.tarifa_id] = conteo.get(a.tarifa_id, 0) + 1
    return conteo


@ruteador.get("/tarifas", response_model=list[PlanComercial])
def planes(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> list[PlanComercial]:
    _ = actor
    conteo = _cuantas_por_plan(s)
    return [_plan_publico(t, conteo.get(t.id, 0)) for t in q.tarifas_de_coach(s)]


def _validar(cuerpo: PlanComercialNuevo) -> None:
    if not cuerpo.nombre.strip() or not cuerpo.codigo.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)
    if cuerpo.precio <= 0:
        raise ErrorDeDominio(Codigo.MONTO_INVALIDO)
    if not 1 <= cuerpo.dias <= 365:
        raise ErrorDeDominio(Codigo.DURACION_DE_TARIFA_INVALIDA, dias=cuerpo.dias)
    if cuerpo.intensidad not in INTENSIDADES:
        raise HTTPException(422, "La intensidad es baja, media o alta")


@ruteador.post("/tarifas", response_model=PlanComercial, status_code=201)
def crear_plan(
    cuerpo: PlanComercialNuevo,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> PlanComercial:
    _validar(cuerpo)
    codigo = cuerpo.codigo.strip().upper()
    if any(t.codigo == codigo for t in q.tarifas_de_coach(s)):
        raise ErrorDeDominio(Codigo.CATEGORIA_INVALIDA, categoria=codigo, tipo="plan")

    plan = Tarifa(
        coach_id=actor.coach_id,
        codigo=codigo,
        nombre=cuerpo.nombre.strip(),
        descripcion=cuerpo.descripcion,
        precio=cuerpo.precio,
        dias=cuerpo.dias,
        intensidad=cuerpo.intensidad,
        activa=cuerpo.activa,
    )
    s.add(plan)
    s.flush()
    return _plan_publico(plan, 0)


@ruteador.put("/tarifas/{ulid}", response_model=PlanComercial)
def editar_plan(
    ulid: str,
    cuerpo: PlanComercialNuevo,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> PlanComercial:
    """Cambiar el precio no toca lo ya programado: cada cobro guarda su propio monto."""
    _ = actor
    _validar(cuerpo)
    plan = q.tarifa_por_ulid(s, ulid)
    if plan is None:
        raise HTTPException(404, "No existe ese plan")

    plan.nombre = cuerpo.nombre.strip()
    plan.descripcion = cuerpo.descripcion
    plan.precio = cuerpo.precio
    plan.dias = cuerpo.dias
    plan.intensidad = cuerpo.intensidad
    plan.activa = cuerpo.activa
    s.flush()
    return _plan_publico(plan, _cuantas_por_plan(s).get(plan.id, 0))


@ruteador.delete("/tarifas/{ulid}", status_code=204)
def desactivar_plan(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    """Se desactiva, no se borra: con el plan se iría la explicación de por qué una alumna
    paga lo que paga."""
    _ = actor
    plan = q.tarifa_por_ulid(s, ulid)
    if plan is None:
        raise HTTPException(404, "No existe ese plan")
    plan.activa = False


# ---------------------------------------------------------------------------
# Catálogo de precios sueltos
# ---------------------------------------------------------------------------


def _servicio_publico(x: Servicio) -> ServicioPublico:
    return ServicioPublico(
        ulid=x.ulid,
        nombre=x.nombre,
        descripcion=x.descripcion,
        motivo=x.motivo,
        precio=x.precio,
        activo=x.activo,
    )


@ruteador.get("/servicios", response_model=list[ServicioPublico])
def servicios(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> list[ServicioPublico]:
    """Su lista de precios. Incluye los apagados: se pueden volver a encender."""
    _ = actor
    filas = s.scalars(select(Servicio).order_by(Servicio.motivo, Servicio.nombre))
    return [_servicio_publico(x) for x in filas]


@ruteador.post("/servicios", response_model=ServicioPublico, status_code=201)
def crear_servicio(
    cuerpo: ServicioNuevo,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> ServicioPublico:
    _validar_servicio(cuerpo)
    servicio = Servicio(
        coach_id=actor.coach_id,
        nombre=cuerpo.nombre.strip()[:120],
        descripcion=(cuerpo.descripcion or "").strip()[:1000] or None,
        motivo=cuerpo.motivo,
        precio=cuerpo.precio,
        activo=cuerpo.activo,
    )
    s.add(servicio)
    s.flush()
    return _servicio_publico(servicio)


@ruteador.put("/servicios/{ulid}", response_model=ServicioPublico)
def editar_servicio(
    ulid: str,
    cuerpo: ServicioNuevo,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> ServicioPublico:
    """Cambiar el precio no reescribe los cobros ya programados: ahí el importe se copió."""
    _ = actor
    _validar_servicio(cuerpo)
    servicio = s.scalars(select(Servicio).where(Servicio.ulid == ulid)).first()
    if servicio is None:
        raise HTTPException(404, "No existe ese servicio")

    servicio.nombre = cuerpo.nombre.strip()[:120]
    servicio.descripcion = (cuerpo.descripcion or "").strip()[:1000] or None
    servicio.motivo = cuerpo.motivo
    servicio.precio = cuerpo.precio
    servicio.activo = cuerpo.activo
    s.flush()
    return _servicio_publico(servicio)


@ruteador.delete("/servicios/{ulid}", status_code=204)
def borrar_servicio(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    """Este sí se borra. A diferencia del plan, no explica por qué nadie paga lo que paga:
    el importe ya quedó copiado en cada cobro que se programó con él."""
    _ = actor
    servicio = s.scalars(select(Servicio).where(Servicio.ulid == ulid)).first()
    if servicio is None:
        raise HTTPException(404, "No existe ese servicio")
    s.delete(servicio)


def _validar_servicio(cuerpo: ServicioNuevo) -> None:
    if not cuerpo.nombre.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)
    if cuerpo.precio <= 0:
        raise ErrorDeDominio(Codigo.MONTO_INVALIDO, monto=str(cuerpo.precio))
    if cuerpo.motivo not in MOTIVOS:
        raise ErrorDeDominio(Codigo.CATEGORIA_INVALIDA, categoria=cuerpo.motivo, tipo="cobro")


# ---------------------------------------------------------------------------
# Cobros programados
# ---------------------------------------------------------------------------


def cobro_publico(c: CobroProgramado, hoy: date) -> CobroDeAlumna:
    return CobroDeAlumna(
        ulid=c.ulid,
        fecha=c.fecha,
        motivo=c.motivo,
        concepto=c.concepto or MOTIVOS.get(c.motivo, c.motivo),
        monto=c.monto,
        estado=c.estado,
        pagado_en=c.pagado_en,
        nota=c.nota,
        # Un comprobante en revisión no cuenta como vencido: la alumna hizo lo suyo y
        # pausarle el plan sería castigarla por la demora de la coach.
        vencido=c.estado == "pendiente" and c.fecha < hoy,
        tiene_comprobante=c.comprobante_key is not None,
        motivo_rechazo=c.motivo_rechazo,
    )


@ruteador.get("/alumnas/{ulid}/cobros", response_model=list[CobroDeAlumna])
def cobros_de_alumna(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> list[CobroDeAlumna]:
    _ = actor
    alumna = q.alumna_por_ulid(s, ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")
    hoy = ahora_utc().date()
    return [cobro_publico(c, hoy) for c in q.cobros_de(s, alumna.id)]


@ruteador.get("/alumnas/{ulid}/citas", response_model=list[CitaDeAlumna])
def citas_de_alumna(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> list[CitaDeAlumna]:
    """Sus consultas: la misma cita que sale en la agenda, vista desde el expediente."""
    _ = actor
    alumna = q.alumna_por_ulid(s, ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")

    return [
        CitaDeAlumna(
            ulid=c.ulid,
            titulo=c.titulo,
            modalidad=c.modalidad,
            estado=c.estado,
            inicia_en=c.inicia_en,
            termina_en=c.termina_en,
        )
        for c in q.citas_de_alumna(s, alumna.id)
    ]


@ruteador.post("/alumnas/{ulid}/cobros", response_model=CobroDeAlumna, status_code=201)
def programar_cobro(
    ulid: str,
    cuerpo: CobroNuevoProgramado,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> CobroDeAlumna:
    """Marca una fecha en la que la alumna debe pagar algo."""
    alumna = q.alumna_por_ulid(s, ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")
    if cuerpo.monto <= 0:
        raise ErrorDeDominio(Codigo.MONTO_INVALIDO)
    if cuerpo.motivo not in MOTIVOS:
        raise HTTPException(422, f"Motivo desconocido: {cuerpo.motivo}")

    cobro = CobroProgramado(
        coach_id=actor.coach_id,
        alumna_id=alumna.id,
        fecha=cuerpo.fecha,
        motivo=cuerpo.motivo,
        concepto=(cuerpo.concepto or "").strip()[:180] or None,
        monto=cuerpo.monto,
        nota=cuerpo.nota,
    )
    s.add(cobro)
    s.flush()
    return cobro_publico(cobro, ahora_utc().date())


@ruteador.delete("/cobros/{ulid}", status_code=204)
def cancelar_cobro(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    """Un cobro pagado no se cancela: sería borrar un ingreso por la puerta de atrás."""
    _ = actor
    cobro = q.cobro_por_ulid(s, ulid)
    if cobro is None:
        raise HTTPException(404, "No existe ese cobro")
    if cobro.estado == "pagado":
        raise HTTPException(409, "Ese cobro ya está pagado. Corrige el movimiento en finanzas.")
    s.delete(cobro)


@ruteador.get("/cobrar", response_model=list[AlumnaConCobros])
def a_quien_cobrar(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
    texto: Annotated[str, Query(alias="q")] = "",
) -> list[AlumnaConCobros]:
    """Alumnas con algo pendiente, con sus cobros: teclear otra vez lo que el sistema ya
    sabe es como se acaba registrando un importe que no cuadra."""
    _ = actor
    busca = texto.strip().lower()
    hoy = ahora_utc().date()
    planes = {t.id: t.nombre for t in q.tarifas_de_coach(s)}

    filas: list[AlumnaConCobros] = []
    for alumna in q.cartera(s):
        if busca and busca not in alumna.nombre.lower():
            continue
        pendientes = q.cobros_pendientes_de(s, alumna.id)
        if not pendientes:
            continue
        filas.append(
            AlumnaConCobros(
                ulid=alumna.ulid,
                nombre=alumna.nombre,
                plan=planes.get(alumna.tarifa_id) if alumna.tarifa_id else None,
                pendientes=[cobro_publico(c, hoy) for c in pendientes],
                adeudo=sum((c.monto for c in pendientes if c.fecha < hoy), Decimal(0)),
            )
        )

    # Primero quien más debe: es a quien hay que perseguir.
    filas.sort(key=lambda f: (-f.adeudo, f.nombre))
    return filas
