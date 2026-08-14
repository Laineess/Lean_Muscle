"""API del frente de alumna.

Cada pantalla se sirve en **una sola llamada**. La alumna abre esto en el celular, muchas
veces con mala señal: tres peticiones en cascada se sienten mucho peor que una un poco más
grande.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc, dia_calendario
from app.datos.modelos import Alumna
from app.datos.repos import consultas as q
from app.dominio.ciclo import Ciclo as CicloDominio
from app.dominio.ciclo import EstadoCiclo, EstadoPago, exigir_acceso_al_plan
from app.rutas.esquemas import (
    ChequeoPublico,
    CicloPublico,
    CitaDeAlumna,
    InicioAlumna,
    PerfilAlumna,
    PlanesDeAlumna,
    PlanPublico,
)
from app.rutas.sesion import Actor, datos, solo_alumna

ruteador = APIRouter(prefix="/api/mi", tags=["alumna"])


def _mi_alumna(s: Session, actor: Actor) -> Alumna:
    alumna = q.alumna_de_usuario(s, actor.usuario_id)
    if alumna is None:
        raise ErrorDeDominio(Codigo.SIN_PERMISO)
    return alumna


def _chequeos_publicos(s: Session, alumna_id: int) -> list[ChequeoPublico]:
    chequeos = q.chequeos_de(s, alumna_id)
    ids = [c.id for c in chequeos]
    medidas = q.medidas_de(s, ids)
    pesos = q.peso_de_chequeo(s, ids)

    return [
        ChequeoPublico(
            ulid=c.ulid,
            numero=i + 1,
            fecha=c.fecha,
            estado=c.estado,
            peso_kg=pesos.get(c.id),
            porcentaje_grasa=c.porcentaje_grasa,
            medidas=medidas.get(c.id, {}),
            # El detalle de las fotos no viaja: la imagen se pide aparte, y cada apertura
            # deja fila en la bitácora de accesos sensibles.
            fotos={"frontal": True, "perfil": True, "espalda": True},
            feedback=c.feedback,
            alerta_outlier=c.alerta_outlier,
        )
        for i, c in enumerate(chequeos)
    ]


@ruteador.get("/inicio", response_model=InicioAlumna)
def inicio(
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> InicioAlumna:
    alumna = _mi_alumna(s, actor)
    ciclo = q.ciclo_vigente(s, alumna.id)
    chequeos = _chequeos_publicos(s, alumna.id)
    pago = q.pago_del_ciclo(s, [ciclo.id]).get(ciclo.id) if ciclo else None

    ultimo_feedback = next(
        (c.feedback for c in reversed(chequeos) if c.feedback),
        None,
    )

    return InicioAlumna(
        perfil=PerfilAlumna(
            ulid=alumna.ulid,
            nombre=alumna.nombre,
            correo=actor_correo(s, actor),
            estatura_cm=alumna.estatura_cm,
            plan=_nombre_de_plan(s, alumna),
            bascula_ref=alumna.bascula_ref,
            lugar_ref=alumna.lugar_ref,
            hora_ref=alumna.hora_ref,
            zona_horaria=alumna.zona_horaria,
            cuestionario_completo=alumna.cuestionario_completo,
        ),
        ciclo=CicloPublico(
            numero=ciclo.numero,
            inicia_en=ciclo.inicia_en,
            termina_en=ciclo.termina_en,
            estado_pago=pago.estado if pago else "pendiente",
            precio=ciclo.precio,
        )
        if ciclo
        else None,
        chequeos=chequeos,
        ultimo_feedback=ultimo_feedback,
        avisos_sin_leer=q.avisos_sin_leer(s, actor.usuario_id),
        coach=nombre_de_coach(s, actor),
        proximas_citas=[
            CitaDeAlumna(
                ulid=c.ulid,
                titulo=c.titulo,
                modalidad=c.modalidad,
                estado=c.estado,
                inicia_en=c.inicia_en,
                termina_en=c.termina_en,
            )
            for c in q.proximas_citas_de(s, alumna.id, ahora_utc())
        ],
    )


@ruteador.get("/plan", response_model=PlanesDeAlumna)
def plan(
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> PlanesDeAlumna:
    """Sin pago validado no hay plan.

    La guarda se evalúa aquí y no en el navegador: un cliente comprometido no debe poder
    saltarse el bloqueo por pago.
    """
    alumna = _mi_alumna(s, actor)
    ciclo = q.ciclo_vigente(s, alumna.id)
    historial = q.historial_vigente(s, alumna.id)

    if ciclo is None:
        return PlanesDeAlumna(
            nutricion=None,
            entrenamiento=None,
            bloqueado_por_pago=True,
            motivo_bloqueo="sin_ciclo",
            restricciones=historial.restricciones if historial else None,
            lesiones=historial.lesiones if historial else None,
        )

    pago = q.pago_del_ciclo(s, [ciclo.id]).get(ciclo.id)
    estado_pago = EstadoPago(pago.estado) if pago else EstadoPago.PENDIENTE

    # Se guarda el motivo, no solo el hecho: «bloqueado» a secas hacía que la pantalla dijera
    # «falta tu comprobante» a quien ya había pagado y solo tenía el ciclo terminado.
    # El adeudo manda sobre todo lo demás: es la única palanca de cobro del sistema y la
    # alumna tiene que poder saber que le falta pagar, no que «su ciclo venció».
    hoy = dia_calendario(ahora_utc(), alumna.zona_horaria)
    motivo: str | None = "adeudo" if q.adeudos_vencidos(s, alumna.id, hoy) else None

    try:
        exigir_acceso_al_plan(
            CicloDominio(
                numero=ciclo.numero,
                inicia_en=ciclo.inicia_en,
                estado=EstadoCiclo.ACTIVO,
                estado_pago=estado_pago,
            ),
            dia_calendario(ahora_utc(), alumna.zona_horaria),
        )
    except ErrorDeDominio as causa:
        if motivo is None:
            motivo = "pago" if causa.codigo is Codigo.PAGO_SIN_VALIDAR else "ciclo_vencido"

    planes = {} if motivo else q.planes_del_ciclo(s, alumna.id, ciclo.id)

    return PlanesDeAlumna(
        nutricion=_plan_publico(planes.get("nutricion"), ciclo.numero),
        entrenamiento=_plan_publico(planes.get("entrenamiento"), ciclo.numero),
        bloqueado_por_pago=motivo is not None,
        motivo_bloqueo=motivo,
        restricciones=historial.restricciones if historial else None,
        lesiones=historial.lesiones if historial else None,
    )


def _plan_publico(p, numero_ciclo: int) -> PlanPublico | None:  # type: ignore[no-untyped-def]
    if p is None:
        return None
    return PlanPublico(
        tipo=p.tipo,
        ciclo=numero_ciclo,
        estado=p.estado,
        publicado_en=p.publicado_en,
        contenido=p.contenido or {},
        kcal_objetivo=p.kcal_objetivo,
        proteina_g=p.proteina_g,
        carbohidrato_g=p.carbohidrato_g,
        grasa_g=p.grasa_g,
    )


def ahora():  # type: ignore[no-untyped-def]
    from app.compartido.fechas import ahora_utc

    return ahora_utc()


def _nombre_de_plan(s: Session, alumna: Alumna) -> str | None:
    """El plan que contrató. Sustituye al antiguo objetivo."""
    if alumna.tarifa_id is None:
        return None
    from app.datos.modelos import Tarifa

    plan = s.get(Tarifa, alumna.tarifa_id)
    return plan.nombre if plan else None


def actor_correo(s: Session, actor: Actor) -> str:
    from app.datos.modelos import Usuario

    usuario = s.get(Usuario, actor.usuario_id)
    return usuario.email if usuario else ""


def nombre_de_coach(s: Session, actor: Actor) -> str:
    from app.datos.modelos import Coach

    coach = s.get(Coach, actor.coach_id)
    return coach.nombre if coach else ""
