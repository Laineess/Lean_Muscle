"""Biblioteca de alimentos y ejercicios, y guardado de planes.

Los catálogos tienen dos orígenes: las filas con `coach_id` nulo son la base pública que
comparten todas las coaches; las que llevan su `coach_id` son suyas. Por eso estas consultas
**no** pueden apoyarse en el filtro por inquilino: lo público quedaría fuera.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.datos.modelos import Alimento, Ejercicio, Plan
from app.datos.repos import consultas as q
from app.rutas.esquemas import (
    AlimentoCatalogo,
    AlimentoNuevo,
    EjercicioCatalogo,
    PlanGuardado,
)
from app.rutas.sesion import Actor, datos, solo_coach

ruteador = APIRouter(prefix="/api/coach", tags=["biblioteca"])

LIMITE_BUSQUEDA = 30


@ruteador.get("/alimentos", response_model=list[AlimentoCatalogo])
def alimentos(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
    q_texto: Annotated[str, Query(alias="q", max_length=80)] = "",
) -> list[AlimentoCatalogo]:
    """Busca en la base pública más los alimentos propios de la coach.

    Se consulta sin alcance a propósito y se filtra a mano: el gancho por inquilino
    excluiría las filas públicas, que son la mayor parte del catálogo.
    """
    consulta = (
        select(Alimento)
        .where(or_(Alimento.coach_id.is_(None), Alimento.coach_id == actor.coach_id))
        .order_by(Alimento.nombre)
        .limit(LIMITE_BUSQUEDA)
    )
    if q_texto.strip():
        consulta = consulta.where(Alimento.nombre.like(f"%{q_texto.strip()}%"))

    filas = s.scalars(consulta.execution_options(sin_alcance=True)).all()
    return [
        AlimentoCatalogo(
            ulid=a.ulid,
            nombre=a.nombre,
            marca=a.marca,
            porcion=a.porcion,
            unidad=a.unidad,
            kcal=a.kcal,
            proteina=a.proteina,
            carbo=a.carbo,
            grasa=a.grasa,
            grupo=a.grupo_equivalente,
            propio=a.coach_id is not None,
        )
        for a in filas
    ]


@ruteador.post("/alimentos", response_model=AlimentoCatalogo, status_code=201)
def crear_alimento(
    cuerpo: AlimentoNuevo,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> AlimentoCatalogo:
    """Alimento propio de la coach. No entra a la base pública: cada quien es responsable de
    los valores que captura."""
    if not cuerpo.nombre.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)
    if cuerpo.porcion <= 0 or cuerpo.kcal < 0:
        raise ErrorDeDominio(Codigo.MONTO_INVALIDO, monto=str(cuerpo.porcion))

    alimento = Alimento(
        coach_id=actor.coach_id,
        nombre=cuerpo.nombre.strip(),
        marca=cuerpo.marca,
        porcion=cuerpo.porcion,
        unidad=cuerpo.unidad,
        kcal=cuerpo.kcal,
        proteina=cuerpo.proteina,
        carbo=cuerpo.carbo,
        grasa=cuerpo.grasa,
        grupo_equivalente=cuerpo.grupo,
    )
    s.add(alimento)
    s.flush()
    return AlimentoCatalogo(
        ulid=alimento.ulid,
        nombre=alimento.nombre,
        marca=alimento.marca,
        porcion=alimento.porcion,
        unidad=alimento.unidad,
        kcal=alimento.kcal,
        proteina=alimento.proteina,
        carbo=alimento.carbo,
        grasa=alimento.grasa,
        grupo=alimento.grupo_equivalente,
        propio=True,
    )


@ruteador.get("/ejercicios", response_model=list[EjercicioCatalogo])
def ejercicios(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
    q_texto: Annotated[str, Query(alias="q", max_length=80)] = "",
) -> list[EjercicioCatalogo]:
    consulta = (
        select(Ejercicio)
        .where(or_(Ejercicio.coach_id.is_(None), Ejercicio.coach_id == actor.coach_id))
        .order_by(Ejercicio.nombre)
        .limit(LIMITE_BUSQUEDA)
    )
    if q_texto.strip():
        consulta = consulta.where(Ejercicio.nombre.like(f"%{q_texto.strip()}%"))

    filas = s.scalars(consulta.execution_options(sin_alcance=True)).all()
    return [
        EjercicioCatalogo(
            ulid=e.ulid,
            nombre=e.nombre,
            grupo=e.grupo,
            equipo=e.equipo,
            patron=e.patron,
            tiene_video=e.video_key is not None,
            contraindicaciones=e.contraindicaciones,
            propio=e.coach_id is not None,
        )
        for e in filas
    ]


# ---------------------------------------------------------------------------
# Guardado de planes
# ---------------------------------------------------------------------------


@ruteador.put("/planes/{alumna_ulid}", status_code=204)
def guardar_plan(
    alumna_ulid: str,
    cuerpo: PlanGuardado,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    """Guarda el borrador y, si se pide, lo publica.

    Las guardas de publicación se evalúan aquí y no en el navegador: sin chequeo validado no
    hay plan nuevo, y sin calorías ni macros tampoco. Guardar el borrador siempre se permite
    —la coach puede dejarlo a medias— pero publicar exige que esté completo.
    """
    from app.dominio.chequeo import EstadoChequeo
    from app.dominio.plan import ContextoPublicacion, Macros, TipoPlan, guardas_de_publicacion

    if cuerpo.tipo not in {"nutricion", "entrenamiento"}:
        raise ErrorDeDominio(Codigo.CATEGORIA_INVALIDA, categoria=cuerpo.tipo, tipo="plan")

    alumna = q.alumna_por_ulid(s, alumna_ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")

    ciclo = q.ciclo_vigente(s, alumna.id)
    if ciclo is None:
        raise HTTPException(409, "Todavía no hay ciclo abierto para esta alumna")

    if cuerpo.publicar:
        chequeos = q.chequeos_de(s, alumna.id)
        ultimo = chequeos[-1] if chequeos else None
        estado = EstadoChequeo(ultimo.estado) if ultimo else EstadoChequeo.BORRADOR

        errores = guardas_de_publicacion(
            ContextoPublicacion(
                tipo=TipoPlan(cuerpo.tipo),
                estado_chequeo_del_ciclo=estado,
                fotos_aprobadas=estado is EstadoChequeo.VALIDADO,
                chequeo_anterior_validado=estado is EstadoChequeo.VALIDADO,
                kcal_objetivo=cuerpo.kcal_objetivo,
                macros=(
                    Macros(
                        proteina_g=cuerpo.proteina_g,  # type: ignore[arg-type]
                        carbohidrato_g=cuerpo.carbohidrato_g,  # type: ignore[arg-type]
                        grasa_g=cuerpo.grasa_g,  # type: ignore[arg-type]
                    )
                    if None not in (cuerpo.proteina_g, cuerpo.carbohidrato_g, cuerpo.grasa_g)
                    else None
                ),
            )
        )
        if errores:
            # Se levanta el primero: la pantalla ya avisa de todos mientras se edita, y aquí
            # lo que importa es no publicar.
            raise errores[0]

    plan = q.planes_del_ciclo(s, alumna.id, ciclo.id).get(cuerpo.tipo)
    if plan is None:
        plan = Plan(
            coach_id=actor.coach_id,
            alumna_id=alumna.id,
            ciclo_id=ciclo.id,
            tipo=cuerpo.tipo,
            contenido={},
        )
        s.add(plan)

    plan.contenido = cuerpo.contenido
    plan.kcal_objetivo = cuerpo.kcal_objetivo
    plan.proteina_g = cuerpo.proteina_g
    plan.carbohidrato_g = cuerpo.carbohidrato_g
    plan.grasa_g = cuerpo.grasa_g

    if cuerpo.publicar:
        plan.estado = "publicado"
        plan.publicado_en = ahora_utc()
