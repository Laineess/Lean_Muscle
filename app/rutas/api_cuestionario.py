"""Cuestionario inicial: núcleo clínico fijo más las preguntas de cada coach.

Dos mitades y la separación no es capricho. Lesiones, condiciones, medicación y
restricciones son columnas de `historial_clinico`: el constructor las lee al elegir
ejercicios, el PDF las imprime y la ley exige consentimiento expreso para ellas. Si la coach
pudiera borrarlas, el aviso de «cuidado con la rodilla» dejaría de existir sin que nadie se
enterara.

Encima de eso, ella agrega las preguntas que quiera, con su tipo. Esas sí son libres.

Contestarlo es lo que marca a la alumna como completa, y es también el momento en que acepta
los consentimientos: aceptarlos es suyo y personal, no algo que la coach capture por ella.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.datos.modelos import (
    Alumna,
    Consentimiento,
    HistorialClinico,
    PreguntaCuestionario,
    RespuestaCuestionario,
    Tarifa,
)
from app.datos.repos import consultas as q
from app.rutas.esquemas import (
    CuestionarioParaAlumna,
    EnvioDeCuestionario,
    NucleoClinico,
    PlanParaElegir,
    PreguntaNueva,
    PreguntaPublica,
    RespuestaDeAlumna,
    RespuestaDePregunta,
)
from app.rutas.sesion import Actor, RutaQueConfirma, datos, solo_alumna, solo_coach
from app.servicios import bitacora, legales

ruteador = APIRouter(prefix="/api", tags=["cuestionario"], route_class=RutaQueConfirma)

TIPOS = {"texto", "texto_largo", "numero", "opcion", "si_no"}

#: Los cuatro que exige el Anexo Legal. Los dos últimos cubren datos sensibles.
CONSENTIMIENTOS = ("terminos", "privacidad", "datos_salud", "protocolo_foto")

LIMITE_PREGUNTAS = 40


def _preguntas(s: Session, coach_id: int, solo_activas: bool = True) -> list[PreguntaCuestionario]:
    consulta = select(PreguntaCuestionario).where(PreguntaCuestionario.coach_id == coach_id)
    if solo_activas:
        consulta = consulta.where(PreguntaCuestionario.activa.is_(True))
    return list(s.scalars(consulta.order_by(PreguntaCuestionario.orden, PreguntaCuestionario.id)))


def _publica(p: PreguntaCuestionario) -> PreguntaPublica:
    return PreguntaPublica(
        ulid=p.ulid,
        texto=p.texto,
        ayuda=p.ayuda,
        tipo=p.tipo,
        opciones=p.opciones or [],
        obligatoria=p.obligatoria,
        orden=p.orden,
        activa=p.activa,
    )


# ---------------------------------------------------------------------------
# La coach arma su cuestionario
# ---------------------------------------------------------------------------


@ruteador.get("/coach/preguntas", response_model=list[PreguntaPublica])
def listar_preguntas(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> list[PreguntaPublica]:
    """Incluye las apagadas: la coach tiene que poder volver a encenderlas."""
    return [_publica(p) for p in _preguntas(s, actor.coach_id, solo_activas=False)]


@ruteador.post("/coach/preguntas", response_model=PreguntaPublica, status_code=201)
def crear_pregunta(
    cuerpo: PreguntaNueva,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> PreguntaPublica:
    if cuerpo.tipo not in TIPOS:
        raise ErrorDeDominio(Codigo.CATEGORIA_INVALIDA, categoria=cuerpo.tipo, tipo="pregunta")
    if not cuerpo.texto.strip():
        raise HTTPException(422, "La pregunta necesita texto")

    existentes = _preguntas(s, actor.coach_id, solo_activas=False)
    if len(existentes) >= LIMITE_PREGUNTAS:
        raise HTTPException(422, f"El cuestionario admite hasta {LIMITE_PREGUNTAS} preguntas")

    # Al final de la lista salvo que pida otro sitio: es donde espera verla aparecer.
    orden = cuerpo.orden or (max((p.orden for p in existentes), default=0) + 1)

    pregunta = PreguntaCuestionario(
        coach_id=actor.coach_id,
        texto=cuerpo.texto.strip()[:300],
        ayuda=(cuerpo.ayuda or "").strip()[:300] or None,
        tipo=cuerpo.tipo,
        opciones=[o.strip() for o in cuerpo.opciones if o.strip()],
        obligatoria=cuerpo.obligatoria,
        orden=orden,
        activa=cuerpo.activa,
    )
    s.add(pregunta)
    s.flush()
    return _publica(pregunta)


@ruteador.put("/coach/preguntas/{ulid}", response_model=PreguntaPublica)
def editar_pregunta(
    ulid: str,
    cuerpo: PreguntaNueva,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> PreguntaPublica:
    if cuerpo.tipo not in TIPOS:
        raise ErrorDeDominio(Codigo.CATEGORIA_INVALIDA, categoria=cuerpo.tipo, tipo="pregunta")

    pregunta = s.scalars(
        select(PreguntaCuestionario).where(PreguntaCuestionario.ulid == ulid)
    ).first()
    if pregunta is None:
        raise HTTPException(404, "No existe esa pregunta")

    pregunta.texto = cuerpo.texto.strip()[:300]
    pregunta.ayuda = (cuerpo.ayuda or "").strip()[:300] or None
    pregunta.tipo = cuerpo.tipo
    pregunta.opciones = [o.strip() for o in cuerpo.opciones if o.strip()]
    pregunta.obligatoria = cuerpo.obligatoria
    pregunta.orden = cuerpo.orden
    pregunta.activa = cuerpo.activa
    s.flush()
    return _publica(pregunta)


@ruteador.delete("/coach/preguntas/{ulid}", status_code=204)
def quitar_pregunta(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    """Se apaga, no se borra: las respuestas ya dadas se quedarían sin su pregunta."""
    _ = actor
    pregunta = s.scalars(
        select(PreguntaCuestionario).where(PreguntaCuestionario.ulid == ulid)
    ).first()
    if pregunta is None:
        raise HTTPException(404, "No existe esa pregunta")
    pregunta.activa = False
    s.flush()


@ruteador.get("/coach/alumnas/{alumna_ulid}/cuestionario", response_model=list[RespuestaDeAlumna])
def respuestas_de_alumna(
    alumna_ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> list[RespuestaDeAlumna]:
    """Lo que contestó. Va con el expediente, así que la lectura queda registrada."""
    alumna = q.alumna_por_ulid(s, alumna_ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")

    bitacora.registrar_acceso(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        alumna_id=alumna.id,
        recurso=bitacora.Recurso.EXPEDIENTE,
    )

    preguntas = {p.id: p for p in _preguntas(s, actor.coach_id, solo_activas=False)}
    filas = s.scalars(
        select(RespuestaCuestionario).where(RespuestaCuestionario.alumna_id == alumna.id)
    )

    respuestas: list[RespuestaDeAlumna] = []
    for r in filas:
        pregunta = preguntas.get(r.pregunta_id)
        if pregunta is None:  # pragma: no cover - defensivo
            continue
        respuestas.append(
            RespuestaDeAlumna(pregunta=pregunta.texto, tipo=pregunta.tipo, valor=r.valor)
        )
    return respuestas


# ---------------------------------------------------------------------------
# La alumna lo contesta
# ---------------------------------------------------------------------------


def _mi_alumna(s: Session, actor: Actor) -> Alumna:
    alumna = q.alumna_de_usuario(s, actor.usuario_id)
    if alumna is None:
        raise ErrorDeDominio(Codigo.SIN_PERMISO)
    return alumna


@ruteador.get("/mi/cuestionario", response_model=CuestionarioParaAlumna)
def mi_cuestionario(
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> CuestionarioParaAlumna:
    alumna = _mi_alumna(s, actor)
    preguntas = _preguntas(s, actor.coach_id)
    por_id = {p.id: p for p in preguntas}

    dadas = s.scalars(
        select(RespuestaCuestionario).where(RespuestaCuestionario.alumna_id == alumna.id)
    )
    respuestas = [
        RespuestaDePregunta(pregunta_ulid=por_id[r.pregunta_id].ulid, valor=r.valor)
        for r in dadas
        if r.pregunta_id in por_id
    ]

    historial = q.historial_vigente(s, alumna.id)
    aceptados = {
        c.tipo
        for c in s.scalars(
            select(Consentimiento).where(
                Consentimiento.alumna_id == alumna.id, Consentimiento.revocado_en.is_(None)
            )
        )
    }

    planes = s.scalars(select(Tarifa).where(Tarifa.activa.is_(True)).order_by(Tarifa.precio)).all()
    elegido = next((t.ulid for t in planes if t.id == alumna.tarifa_id), None)

    return CuestionarioParaAlumna(
        planes=[
            PlanParaElegir(
                ulid=t.ulid,
                nombre=t.nombre,
                descripcion=t.descripcion,
                precio=t.precio,
                dias=t.dias,
                intensidad=t.intensidad,
            )
            for t in planes
        ],
        plan_elegido=elegido,
        completo=alumna.cuestionario_completo,
        nucleo=NucleoClinico(
            lesiones=historial.lesiones if historial else None,
            condiciones=historial.condiciones if historial else None,
            medicacion=historial.medicacion if historial else None,
            restricciones=historial.restricciones if historial else None,
        ),
        preguntas=[_publica(p) for p in preguntas],
        respuestas=respuestas,
        consentimientos_pendientes=[t for t in CONSENTIMIENTOS if t not in aceptados],
    )


@ruteador.post("/mi/cuestionario", status_code=204)
def enviar_cuestionario(
    cuerpo: EnvioDeCuestionario,
    peticion: Request,
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    """Guarda el historial, las respuestas y los consentimientos, y la marca como completa.

    El historial no se actualiza: se inserta una versión nueva, que es como está diseñado
    desde el principio. Nunca se pierde lo que declaró antes.
    """
    alumna = _mi_alumna(s, actor)
    preguntas = {p.ulid: p for p in _preguntas(s, actor.coach_id)}

    faltantes = [
        p.texto
        for p in preguntas.values()
        if p.obligatoria
        and not next((r.valor.strip() for r in cuerpo.respuestas if r.pregunta_ulid == p.ulid), "")
    ]
    if faltantes:
        raise HTTPException(422, f"Falta contestar: {faltantes[0]}")

    s.add(
        HistorialClinico(
            coach_id=actor.coach_id,
            alumna_id=alumna.id,
            lesiones=cuerpo.nucleo.lesiones,
            condiciones=cuerpo.nucleo.condiciones,
            medicacion=cuerpo.nucleo.medicacion,
            restricciones=cuerpo.nucleo.restricciones,
            vigente_desde=ahora_utc(),
            registrado_por=actor.usuario_id,
        )
    )

    ya_dadas = {
        r.pregunta_id: r
        for r in s.scalars(
            select(RespuestaCuestionario).where(RespuestaCuestionario.alumna_id == alumna.id)
        )
    }
    for enviada in cuerpo.respuestas:
        pregunta = preguntas.get(enviada.pregunta_ulid)
        if pregunta is None:
            continue
        fila = ya_dadas.get(pregunta.id)
        if fila is None:
            fila = RespuestaCuestionario(
                coach_id=actor.coach_id, alumna_id=alumna.id, pregunta_id=pregunta.id
            )
            s.add(fila)
        fila.valor = enviada.valor.strip()[:4000]

    _registrar_consentimientos(s, actor, alumna, cuerpo.consentimientos, peticion)

    # El plan que pide es una solicitud, no un contrato: el ciclo se crea cuando la coach
    # acepta, con el plan que ella confirme.
    if cuerpo.tarifa_ulid:
        pedido = s.scalars(select(Tarifa).where(Tarifa.ulid == cuerpo.tarifa_ulid)).first()
        if pedido is None or not pedido.activa:
            raise HTTPException(422, "Ese plan ya no está disponible")
        alumna.tarifa_id = pedido.id

    alumna.cuestionario_completo = True
    s.flush()

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="alumna",
        accion=bitacora.Accion.HISTORIAL_ACTUALIZADO,
        entidad="alumna",
        entidad_id=alumna.id,
        detalle={"campos_cambiados": "cuestionario_inicial"},
    )


def _registrar_consentimientos(
    s: Session,
    actor: Actor,
    alumna: Alumna,
    tipos: list[str],
    peticion: Request,
) -> None:
    """Cada aceptación guarda **qué texto exacto** se aceptó, no solo que se aceptó."""
    aceptados = {
        c.tipo
        for c in s.scalars(
            select(Consentimiento).where(
                Consentimiento.alumna_id == alumna.id, Consentimiento.revocado_en.is_(None)
            )
        )
    }
    agente = (peticion.headers.get("user-agent") or "")[:255]
    ip = peticion.client.host if peticion.client else None

    for tipo in tipos:
        if tipo not in CONSENTIMIENTOS or tipo in aceptados:
            continue
        version, huella = legales.version_y_hash(tipo)
        s.add(
            Consentimiento(
                coach_id=actor.coach_id,
                alumna_id=alumna.id,
                tipo=tipo,
                version_texto=version,
                texto_hash=huella,
                aceptado_en=ahora_utc(),
                ip=ip,
                user_agent=agente,
            )
        )
