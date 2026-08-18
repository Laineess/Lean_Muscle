"""Panel de la plataforma: administrar coaches, cobrarles y vigilar lo que falla en silencio.

Vive aparte porque es el único paquete de rutas al que `prueba_fronteras.py` le permite
importar `sin_alcance`.

El superadmin no ve datos de alumnas: ni fotos, ni pesos, ni nombres. Solo cuántas. Frente a
la LFPDPPP la plataforma es Encargado y no Responsable, y eso se sostiene si el acceso
técnico coincide con el contrato.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.config import ajustes
from app.datos.modelos import CobroCoach, SuscripcionCoach
from app.datos.repos import plataforma as q
from app.datos.sin_alcance import sesion_sin_alcance
from app.rutas.esquemas import (
    AltaDeCoach,
    CoachDadaDeAlta,
    CobroNuevo,
    CobroPublico,
    EdicionDeCoach,
    EdicionDeSuscripcion,
    FilaDeCoach,
    MovimientoDeAuditoria,
    ResumenDeFacturacion,
    ResumenMes,
    SaludPublica,
    SuscripcionPublica,
)
from app.rutas.sesion import Actor, solo_admin
from app.servicios import cuentas

ruteador = APIRouter(prefix="/api/plataforma", tags=["plataforma"])

#: Tras estos días sin que nadie entre a una cuenta, conviene preguntar si sigue viva.
DIAS_INACTIVA = 30

ESTADOS_DE_SUSCRIPCION = {"cortesia", "al_corriente", "por_vencer", "vencida", "cancelada"}
ESTADOS_DE_COACH = {"activa", "pausa", "baja"}


def _mb(bytes_: int) -> int:
    return round(bytes_ / 1_048_576)


def _suscripcion_publica(f: SuscripcionCoach | None) -> SuscripcionPublica | None:
    if f is None:
        return None
    return SuscripcionPublica(
        plan=f.plan,
        precio=f.precio,
        periodicidad=f.periodicidad,
        estado=f.estado,
        inicia_en=f.inicia_en,
        vigente_hasta=f.vigente_hasta,
        nota=f.nota,
    )


def _mensual(f: SuscripcionCoach) -> Decimal:
    """Lo que esa suscripción representa al mes, para poder sumar peras con manzanas."""
    if f.estado in {"cancelada", "cortesia"}:
        return Decimal(0)
    return (f.precio / 12) if f.periodicidad == "anual" else f.precio


def _filas(s: Session, hoy: date) -> list[FilaDeCoach]:
    conteos = q.conteos_por_coach(s, hoy)
    subs = q.suscripciones(s)
    ahora = ahora_utc()

    filas: list[FilaDeCoach] = []
    for coach in q.coaches(s):
        c = conteos.get(coach.id)
        ultimo = c.ultimo_acceso if c else None
        dias = (ahora - ultimo).days if ultimo else None

        filas.append(
            FilaDeCoach(
                ulid=coach.ulid,
                nombre=coach.nombre,
                marca=coach.marca or coach.nombre,
                slug=coach.slug,
                email=coach.email,
                plan=coach.plan,
                limite_alumnas=coach.limite_alumnas,
                estado=coach.estado,
                precio_ciclo=coach.precio_ciclo,
                creado_en=coach.creado_en,
                alumnas=c.alumnas if c else 0,
                alumnas_activas=c.alumnas_activas if c else 0,
                chequeos_por_validar=c.chequeos_por_validar if c else 0,
                chequeos_del_mes=c.chequeos_del_mes if c else 0,
                fotos=c.fotos if c else 0,
                mb_fotos=_mb(c.bytes_fotos if c else 0),
                ultimo_acceso=ultimo,
                dias_inactiva=dias,
                suscripcion=_suscripcion_publica(subs.get(coach.id)),
            )
        )
    return filas


# ---------------------------------------------------------------------------
# Coaches
# ---------------------------------------------------------------------------


@ruteador.get("/coaches", response_model=list[FilaDeCoach])
def coaches(actor: Annotated[Actor, Depends(solo_admin)]) -> list[FilaDeCoach]:
    _ = actor
    with sesion_sin_alcance("panel de plataforma: agregados de todos los inquilinos") as s:
        return _filas(s, ahora_utc().date())


@ruteador.post("/coaches", response_model=CoachDadaDeAlta, status_code=201)
def dar_de_alta_coach(
    cuerpo: AltaDeCoach,
    actor: Annotated[Actor, Depends(solo_admin)],
) -> CoachDadaDeAlta:
    """Crea el inquilino y su usuaria coach. La clave se devuelve una sola vez; después solo
    queda su hash, y entrar con ella obliga a cambiarla."""
    _ = actor
    with sesion_sin_alcance("alta de un inquilino nuevo: todavía no existe su alcance") as s:
        ulid, correo, clave = cuentas.dar_de_alta_coach(
            s,
            nombre=cuerpo.nombre,
            marca=cuerpo.marca,
            correo=cuerpo.email,
            slug=cuerpo.slug,
            plan=cuerpo.plan,
            limite_alumnas=cuerpo.limite_alumnas,
            precio_ciclo=cuerpo.precio_ciclo,
            color_acento=cuerpo.color_acento,
            zona_horaria=cuerpo.zona_horaria,
        )
        # Nace en cortesía: cobrarle desde el primer día a alguien que todavía no ha subido
        # una sola alumna genera una factura que nadie va a pagar.
        coach = q.coach_por_ulid(s, ulid)
        if coach is not None:
            s.add(
                SuscripcionCoach(
                    coach_id=coach.id,
                    plan=cuerpo.plan,
                    precio=Decimal(0),
                    periodicidad="mensual",
                    estado="cortesia",
                    inicia_en=ahora_utc().date(),
                )
            )
        return CoachDadaDeAlta(coach_ulid=ulid, email=correo, clave_temporal=clave)


@ruteador.put("/coaches/{ulid}", response_model=FilaDeCoach)
def editar_coach(
    ulid: str,
    cuerpo: EdicionDeCoach,
    actor: Annotated[Actor, Depends(solo_admin)],
) -> FilaDeCoach:
    """Plan, límite de alumnas y estado. Poner una coach en `baja` no borra nada: eliminar
    datos personales es otro flujo, con plazos propios."""
    _ = actor
    if cuerpo.estado not in ESTADOS_DE_COACH:
        raise HTTPException(422, f"Estado desconocido: {cuerpo.estado}")
    if cuerpo.limite_alumnas < 1:
        raise HTTPException(422, "El límite de alumnas tiene que ser al menos 1.")

    with sesion_sin_alcance("panel de plataforma: edición del inquilino") as s:
        coach = q.coach_por_ulid(s, ulid)
        if coach is None:
            raise HTTPException(404, "No existe esa coach")

        coach.nombre = cuerpo.nombre.strip()[:120]
        coach.marca = (cuerpo.marca.strip() or cuerpo.nombre.strip())[:120]
        coach.plan = cuerpo.plan
        coach.limite_alumnas = cuerpo.limite_alumnas
        coach.estado = cuerpo.estado
        coach.precio_ciclo = cuerpo.precio_ciclo
        coach.color_acento = cuerpo.color_acento
        s.flush()

        fila = next(f for f in _filas(s, ahora_utc().date()) if f.ulid == ulid)
        return fila


# ---------------------------------------------------------------------------
# Facturación
# ---------------------------------------------------------------------------


@ruteador.put("/coaches/{ulid}/suscripcion", response_model=SuscripcionPublica)
def editar_suscripcion(
    ulid: str,
    cuerpo: EdicionDeSuscripcion,
    actor: Annotated[Actor, Depends(solo_admin)],
) -> SuscripcionPublica:
    _ = actor
    if cuerpo.estado not in ESTADOS_DE_SUSCRIPCION:
        raise HTTPException(422, f"Estado desconocido: {cuerpo.estado}")
    if cuerpo.periodicidad not in {"mensual", "anual"}:
        raise HTTPException(422, "La periodicidad es mensual o anual.")
    if cuerpo.precio < 0:
        raise ErrorDeDominio(Codigo.MONTO_INVALIDO)

    with sesion_sin_alcance("panel de plataforma: suscripción del inquilino") as s:
        coach = q.coach_por_ulid(s, ulid)
        if coach is None:
            raise HTTPException(404, "No existe esa coach")

        fila = q.suscripcion_de(s, coach.id)
        if fila is None:
            fila = SuscripcionCoach(coach_id=coach.id, inicia_en=ahora_utc().date())
            s.add(fila)

        fila.plan = cuerpo.plan
        fila.precio = cuerpo.precio
        fila.periodicidad = cuerpo.periodicidad
        fila.estado = cuerpo.estado
        fila.vigente_hasta = cuerpo.vigente_hasta
        fila.nota = cuerpo.nota
        s.flush()

        publica = _suscripcion_publica(fila)
        assert publica is not None
        return publica


@ruteador.get("/coaches/{ulid}/cobros", response_model=list[CobroPublico])
def cobros(ulid: str, actor: Annotated[Actor, Depends(solo_admin)]) -> list[CobroPublico]:
    _ = actor
    with sesion_sin_alcance("panel de plataforma: historial de cobros del inquilino") as s:
        coach = q.coach_por_ulid(s, ulid)
        if coach is None:
            raise HTTPException(404, "No existe esa coach")
        return [_cobro_publico(c, ulid) for c in q.cobros_de(s, coach.id)]


@ruteador.post("/coaches/{ulid}/cobros", response_model=CobroPublico, status_code=201)
def registrar_cobro(
    ulid: str,
    cuerpo: CobroNuevo,
    actor: Annotated[Actor, Depends(solo_admin)],
) -> CobroPublico:
    """Registra un pago de la coach. Solo inserción: un cobro mal capturado se corrige con
    otro en negativo. Si trae periodo, la suscripción avanza sola a `al_corriente`."""
    _ = actor
    if cuerpo.monto == 0:
        raise ErrorDeDominio(Codigo.MONTO_INVALIDO)

    with sesion_sin_alcance("panel de plataforma: registro de un cobro al inquilino") as s:
        coach = q.coach_por_ulid(s, ulid)
        if coach is None:
            raise HTTPException(404, "No existe esa coach")

        fila = CobroCoach(
            coach_id=coach.id,
            monto=cuerpo.monto,
            fecha=cuerpo.fecha,
            metodo=cuerpo.metodo[:40],
            periodo_inicia=cuerpo.periodo_inicia,
            periodo_termina=cuerpo.periodo_termina,
            nota=cuerpo.nota,
            registrado_por=actor.usuario_id,
        )
        s.add(fila)

        suscripcion = q.suscripcion_de(s, coach.id)
        if suscripcion is not None and cuerpo.periodo_termina is not None:
            suscripcion.vigente_hasta = cuerpo.periodo_termina
            suscripcion.estado = "al_corriente"

        s.flush()
        return _cobro_publico(fila, ulid)


def _cobro_publico(c: CobroCoach, coach_ulid: str) -> CobroPublico:
    return CobroPublico(
        ulid=c.ulid,
        coach_ulid=coach_ulid,
        monto=c.monto,
        fecha=c.fecha,
        metodo=c.metodo,
        periodo_inicia=c.periodo_inicia,
        periodo_termina=c.periodo_termina,
        nota=c.nota,
    )


@ruteador.get("/facturacion", response_model=ResumenDeFacturacion)
def facturacion(
    actor: Annotated[Actor, Depends(solo_admin)],
    meses: Annotated[int, Query(ge=1, le=36)] = 12,
) -> ResumenDeFacturacion:
    _ = actor
    hoy = ahora_utc().date()
    desde = date(hoy.year, hoy.month, 1)
    for _ in range(meses - 1):
        desde = (desde - timedelta(days=1)).replace(day=1)

    with sesion_sin_alcance("panel de plataforma: facturación agregada") as s:
        subs = q.suscripciones(s)
        esperado = sum((_mensual(f) for f in subs.values()), Decimal(0))

        por_mes = [
            ResumenMes(mes=mes, ingresos=monto, gastos=Decimal(0), utilidad=monto)
            for mes, monto in q.cobros_por_mes(s, desde)
        ]

        return ResumenDeFacturacion(
            cobrado_en_el_ano=q.cobrado_en_el_ano(s, hoy.year),
            facturacion_mensual_esperada=esperado,
            coaches_al_corriente=sum(1 for f in subs.values() if f.estado == "al_corriente"),
            coaches_vencidas=sum(1 for f in subs.values() if f.estado == "vencida"),
            coaches_en_cortesia=sum(1 for f in subs.values() if f.estado == "cortesia"),
            por_mes=por_mes,
        )


# ---------------------------------------------------------------------------
# Salud y auditoría
# ---------------------------------------------------------------------------


@ruteador.get("/salud", response_model=SaludPublica)
def salud(actor: Annotated[Actor, Depends(solo_admin)]) -> SaludPublica:
    """Las piezas que fallan sin avisar: un correo que no salió no manda un correo diciendo
    que no salió, y no purgar a tiempo no da error, da un incumplimiento."""
    _ = actor
    ahora = ahora_utc()
    with sesion_sin_alcance("panel de plataforma: salud del sistema, sin datos personales") as s:
        estado = q.salud(s, ahora, ajustes().retencion_fotos_meses)
        filas = _filas(s, ahora.date())

    return SaludPublica(
        avisos_pendientes=estado.avisos_pendientes,
        avisos_agotados=estado.avisos_agotados,
        ultimo_aviso_enviado=estado.ultimo_aviso_enviado,
        fotos_por_purgar=estado.fotos_por_purgar,
        mb_totales=_mb(estado.bytes_totales),
        suscripciones_push=estado.suscripciones_push,
        sesiones_vivas=estado.sesiones_vivas,
        coaches_activas=sum(
            1 for f in filas if f.dias_inactiva is not None and f.dias_inactiva < DIAS_INACTIVA
        ),
        coaches_inactivas=sum(
            1 for f in filas if f.dias_inactiva is None or f.dias_inactiva >= DIAS_INACTIVA
        ),
    )


@ruteador.get("/auditoria", response_model=list[MovimientoDeAuditoria])
def auditoria(
    actor: Annotated[Actor, Depends(solo_admin)],
    limite: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[MovimientoDeAuditoria]:
    """Qué se ha hecho, sin decir sobre quién: la acción, la cuenta y el momento, nunca el
    detalle ni la entidad. Responde «¿qué pasó en esta cuenta?» sin identificar a nadie."""
    _ = actor
    with sesion_sin_alcance("panel de plataforma: auditoría sin datos personales") as s:
        nombres = {c.id: c.nombre for c in q.coaches(s)}
        return [
            MovimientoDeAuditoria(
                cuando=cuando,
                coach=nombres.get(coach_id, "—"),
                actor_tipo=actor_tipo,
                accion=accion,
                entidad=entidad,
            )
            for cuando, coach_id, actor_tipo, accion, entidad in q.auditoria(s, limite)
        ]


_ = datetime  # usado en las anotaciones de los esquemas
