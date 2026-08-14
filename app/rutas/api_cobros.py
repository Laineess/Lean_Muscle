"""Planes comerciales y cobros programados.

Es la dinámica de cobro entera: la coach crea planes con su precio, cada alumna pertenece a
uno, y la coach marca en un calendario las fechas en las que esa alumna debe pagar algo.

**Un cobro vencido y sin pagar pausa el plan de la alumna.** Esa es la única palanca de
cobro del sistema, y por eso vive en el cobro y no en el ciclo: el ciclo mide el método, no
el dinero.

El plan comercial se guarda en la tabla `tarifa`. Hacia afuera se llama plan porque `Plan`
ya es el de nutrición y entrenamiento, y dos cosas con el mismo nombre en la misma pantalla
se confunden.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.datos.modelos import CobroProgramado, Tarifa
from app.datos.repos import consultas as q
from app.rutas.esquemas import (
    AlumnaConCobros,
    CobroDeAlumna,
    CobroNuevoProgramado,
    PlanComercial,
    PlanComercialNuevo,
)
from app.rutas.sesion import Actor, datos, solo_coach

ruteador = APIRouter(prefix="/api/coach", tags=["cobros"])

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
        vencido=c.estado == "pendiente" and c.fecha < hoy,
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
    """Alumnas con algo pendiente, para el buscador de finanzas.

    Trae también sus cobros para poder autocompletar monto y concepto: volver a teclear lo
    que el sistema ya sabe es como se acaba registrando un importe que no cuadra.
    """
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
