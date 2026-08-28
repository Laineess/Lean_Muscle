"""Biblioteca de alimentos y ejercicios, y guardado de planes.

Los catálogos tienen dos orígenes: las filas con `coach_id` nulo son la base pública que
comparten todas las coaches; las que llevan su `coach_id` son suyas. Por eso estas consultas
**no** pueden apoyarse en el filtro por inquilino: lo público quedaría fuera.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.datos.modelos import Alimento, Chequeo, Ejercicio, ParametrosCiclo, Plan, Tarifa
from app.datos.repos import consultas as q
from app.dominio.fotos_de_comida import Frecuencia
from app.rutas.esquemas import (
    AlimentoCatalogo,
    AlimentoNuevo,
    ChequeoDelConstructor,
    EjercicioCatalogo,
    EjercicioNuevo,
    ExpedienteDeConstructor,
    ParametrosDeCiclo,
    PlanGuardado,
    PlanPublico,
    RepartoDeMacros,
)
from app.rutas.sesion import Actor, RutaQueConfirma, datos, solo_coach
from app.servicios import bitacora

ruteador = APIRouter(prefix="/api/coach", tags=["biblioteca"], route_class=RutaQueConfirma)

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


@ruteador.post("/ejercicios", response_model=EjercicioCatalogo, status_code=201)
def crear_ejercicio(
    cuerpo: EjercicioNuevo,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> EjercicioCatalogo:
    """Ejercicio propio de la coach. Igual que el alimento: no entra a la base pública."""
    if not cuerpo.nombre.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)

    ejercicio = Ejercicio(
        coach_id=actor.coach_id,
        nombre=cuerpo.nombre.strip(),
        grupo=cuerpo.grupo,
        equipo=cuerpo.equipo,
        patron=cuerpo.patron,
    )
    s.add(ejercicio)
    s.flush()
    return EjercicioCatalogo(
        ulid=ejercicio.ulid,
        nombre=ejercicio.nombre,
        grupo=ejercicio.grupo,
        equipo=ejercicio.equipo,
        patron=ejercicio.patron,
        tiene_video=ejercicio.video_key is not None,
        contraindicaciones=ejercicio.contraindicaciones,
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
# Planes
# ---------------------------------------------------------------------------

#: Valores con los que arranca un ciclo sin parámetros guardados. Son los de la hoja.
PARAMETROS_INICIALES = ParametrosDeCiclo(
    actividad="activo",
    porcentaje_ajuste=Decimal("-0.200"),
    reparto=RepartoDeMacros(
        carbohidrato=Decimal("0.400"), proteina=Decimal("0.320"), grasa=Decimal("0.280")
    ),
    base_proteina="masa_libre_de_grasa",
    dias_refeed=1,
    porcentaje_dia_refeed=Decimal("0.000"),
    relacion_ganancia="2:1",
)


def _plan_publico(plan: Plan | None, numero_ciclo: int) -> PlanPublico | None:
    if plan is None:
        return None
    return PlanPublico(
        tipo=plan.tipo,
        ciclo=numero_ciclo,
        estado=plan.estado,
        publicado_en=plan.publicado_en,
        contenido=plan.contenido or {},
        kcal_objetivo=plan.kcal_objetivo,
        proteina_g=plan.proteina_g,
        carbohidrato_g=plan.carbohidrato_g,
        grasa_g=plan.grasa_g,
        frecuencia_fotos=plan.frecuencia_fotos,
    )


@ruteador.get("/planes/{alumna_ulid}", response_model=ExpedienteDeConstructor)
def expediente_de_constructor(
    alumna_ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> ExpedienteDeConstructor:
    """Lo que abre el constructor: la ficha, el último chequeo, los parámetros y los planes.

    Peso y porcentaje de grasa son datos de salud, así que la lectura queda registrada.
    """
    alumna = q.alumna_por_ulid(s, alumna_ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")

    ciclo = q.ciclo_vigente(s, alumna.id)
    if ciclo is None:
        raise HTTPException(409, "Todavía no hay ciclo abierto para esta alumna")

    bitacora.registrar_acceso(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        alumna_id=alumna.id,
        recurso=bitacora.Recurso.EXPEDIENTE,
    )

    chequeos = q.chequeos_de(s, alumna.id)
    ultimo: Chequeo | None = chequeos[-1] if chequeos else None
    peso = q.peso_de_chequeo(s, [ultimo.id]).get(ultimo.id) if ultimo else None

    guardados = s.scalars(
        select(ParametrosCiclo).where(ParametrosCiclo.ciclo_id == ciclo.id)
    ).first()
    parametros = (
        ParametrosDeCiclo(
            actividad=guardados.nivel_actividad,
            porcentaje_ajuste=guardados.porcentaje_ajuste,
            reparto=RepartoDeMacros(
                carbohidrato=guardados.reparto_carbohidrato,
                proteina=guardados.reparto_proteina,
                grasa=guardados.reparto_grasa,
            ),
            base_proteina=guardados.base_proteina,
            dias_refeed=guardados.dias_refeed,
            porcentaje_dia_refeed=guardados.porcentaje_dia_refeed,
            relacion_ganancia=guardados.relacion_ganancia,
        )
        if guardados is not None
        else PARAMETROS_INICIALES
    )

    tarifa = s.get(Tarifa, alumna.tarifa_id) if alumna.tarifa_id else None
    planes = q.planes_del_ciclo(s, alumna.id, ciclo.id)
    return ExpedienteDeConstructor(
        alumna_ulid=alumna.ulid,
        alumna=alumna.nombre,
        ciclo=ciclo.numero,
        fecha_nacimiento=alumna.fecha_nacimiento,
        sexo=alumna.sexo,
        estatura_cm=alumna.estatura_cm,
        porcentaje_grasa_objetivo=alumna.porcentaje_grasa_objetivo,
        chequeo=(
            ChequeoDelConstructor(
                fecha=ultimo.fecha,
                estado=ultimo.estado,
                peso_kg=peso,
                porcentaje_grasa=ultimo.porcentaje_grasa,
            )
            if ultimo is not None
            else None
        ),
        parametros=parametros,
        nutricion=_plan_publico(planes.get("nutricion"), ciclo.numero),
        entrenamiento=_plan_publico(planes.get("entrenamiento"), ciclo.numero),
        plan_nombre=tarifa.nombre if tarifa else None,
        plan_precio=tarifa.precio if tarifa else None,
    )


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

    # Solo el de nutrición: pedir fotos de comida con la rutina de pierna no significa nada.
    if cuerpo.tipo == "nutricion":
        if cuerpo.frecuencia_fotos not in {f.value for f in Frecuencia}:
            raise ErrorDeDominio(
                Codigo.CATEGORIA_INVALIDA, categoria=cuerpo.frecuencia_fotos, tipo="frecuencia"
            )
        plan.frecuencia_fotos = cuerpo.frecuencia_fotos

    if cuerpo.publicar:
        plan.estado = "publicado"
        plan.publicado_en = ahora_utc()

    if cuerpo.parametros is not None:
        _guardar_parametros(s, actor, alumna.id, ciclo.id, cuerpo.parametros)

    # Se fuerza aquí: como dependencia, la sesión hace commit después de responder, y un
    # CHECK roto se perdería con el 204 ya enviado.
    s.flush()


def _guardar_parametros(
    s: Session,
    actor: Actor,
    alumna_id: int,
    ciclo_id: int,
    p: ParametrosDeCiclo,
) -> None:
    """Uno por ciclo: si ya existe se actualiza, y el UNIQUE evita el duplicado."""
    suma = p.reparto.carbohidrato + p.reparto.proteina + p.reparto.grasa
    if suma != 1:
        raise ErrorDeDominio(Codigo.REPARTO_DE_MACROS_NO_SUMA_UNO, suma=str(suma))

    fila = s.scalars(select(ParametrosCiclo).where(ParametrosCiclo.ciclo_id == ciclo_id)).first()
    if fila is None:
        fila = ParametrosCiclo(coach_id=actor.coach_id, alumna_id=alumna_id, ciclo_id=ciclo_id)
        s.add(fila)

    fila.nivel_actividad = p.actividad
    fila.porcentaje_ajuste = p.porcentaje_ajuste
    fila.reparto_carbohidrato = p.reparto.carbohidrato
    fila.reparto_proteina = p.reparto.proteina
    fila.reparto_grasa = p.reparto.grasa
    fila.base_proteina = p.base_proteina
    fila.dias_refeed = p.dias_refeed
    fila.porcentaje_dia_refeed = p.porcentaje_dia_refeed
    fila.relacion_ganancia = p.relacion_ganancia
