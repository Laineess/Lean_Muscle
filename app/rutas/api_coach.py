"""API del panel de coach.

Todas las lecturas van sobre la sesión con alcance: el `coach_id` sale del token y nunca
del cliente. Un `ulid` de otra coach simplemente no existe para esta sesión, así que
devuelve 404 sin revelar que existe en otro inquilino.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.config import ajustes
from app.datos.modelos import Alumna, Chequeo, Cita, Coach, Usuario
from app.datos.repos import consultas as q
from app.dominio.agenda import EstadoCita, Franja, agendar, transicionar
from app.dominio.avisos import Aviso
from app.rutas.esquemas import (
    AgendaDeCoach,
    AltaDeAlumna,
    AlumnaDadaDeAlta,
    CancelacionCita,
    ChequeoDeValidacion,
    CitaNueva,
    CitaPublica,
    ClaveTemporalEmitida,
    ClaveTemporalPedida,
    EdicionDeAlumna,
    EdicionDeMarca,
    EstimacionGrasa,
    ExpedienteDeValidacion,
    FilaCartera,
    FotoPublica,
    HistorialPublico,
    MarcaDeCobro,
    MarcaPublica,
    RechazoChequeo,
    ResumenPanel,
    ValidacionChequeo,
)
from app.rutas.sesion import Actor, datos, solo_coach
from app.servicios import almacenamiento, bitacora, cuentas, imagenes
from app.servicios import avisos as cola
from app.servicios.almacenamiento import almacen
from app.servicios.seguridad import VIGENCIA_CLAVE_TEMPORAL

ruteador = APIRouter(prefix="/api/coach", tags=["coach"])

DIAS_INACTIVIDAD = 3


def _encolar_correo(
    s: Session,
    coach_id: int,
    aviso: Aviso,
    *,
    para: str,
    llave: str,
    contexto: dict[str, object],
    destinatario_id: int | None = None,
) -> None:
    """Encola el aviso en todos sus canales. El envío lo hace el trabajador."""
    cola.encolar(
        s,
        aviso,
        coach_id=coach_id,
        llave=llave,
        para=para,
        contexto=contexto,
        destinatario_id=destinatario_id,
    )


# ---------------------------------------------------------------------------
# Cartera y panel
# ---------------------------------------------------------------------------


def _filas_de_cartera(s: Session) -> list[FilaCartera]:
    alumnas = q.cartera(s)
    ids = [a.id for a in alumnas]

    ciclos = q.ciclos_vigentes(s, ids)
    planes = {t.id: t.nombre for t in q.tarifas_de_coach(s)}
    ultimos = q.ultimo_chequeo_por_alumna(s, ids)
    accesos = q.ultimo_acceso_de(s, [a.usuario_id for a in alumnas])

    pesos_por_chequeo = q.peso_de_chequeo(s, [c.id for c in ultimos.values()])
    hoy = ahora_utc().date()

    filas: list[FilaCartera] = []
    for a in alumnas:
        ciclo = ciclos.get(a.id)
        chequeo = ultimos.get(a.id)
        acceso = accesos.get(a.usuario_id)
        acceso_dia = acceso.date() if acceso else None

        # Prioridad de la alerta: primero lo que bloquea el método, luego lo que cuesta
        # dinero, al final lo que solo requiere un empujón.
        # Lo que de verdad se debe: cobros con fecha pasada y sin pagar.
        vencidos = q.adeudos_vencidos(s, a.id, hoy)
        adeudo = sum((c.monto for c in vencidos), Decimal(0))

        alerta: str | None = None
        if chequeo is not None and chequeo.alerta_outlier:
            alerta = "outlier"
        elif adeudo > 0:
            alerta = "pago"
        elif acceso_dia is None or (hoy - acceso_dia).days >= DIAS_INACTIVIDAD:
            alerta = "inactividad"

        filas.append(
            FilaCartera(
                ulid=a.ulid,
                nombre=a.nombre,
                ciclo=ciclo.numero if ciclo else 0,
                estado=a.estado,
                chequeo_estado=chequeo.estado if chequeo else None,
                chequeo_fecha=chequeo.fecha if chequeo else None,
                peso_kg=pesos_por_chequeo.get(chequeo.id) if chequeo else None,
                peso_previo=None,
                plan=planes.get(a.tarifa_id) if a.tarifa_id else None,
                pago="con adeudo" if adeudo > 0 else "al corriente",
                ultimo_acceso=acceso_dia,
                alerta=alerta,
                adeudo=adeudo,
            )
        )
    return filas


@ruteador.get("/panel", response_model=ResumenPanel)
def panel(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> ResumenPanel:
    coach = s.get(Coach, actor.coach_id)
    if coach is None:  # pragma: no cover - solo si el inquilino se borró bajo los pies
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    filas = _filas_de_cartera(s)

    return ResumenPanel(
        coach=coach.nombre,
        marca=coach.marca or coach.nombre,
        plan=coach.plan,
        limite_alumnas=coach.limite_alumnas,
        precio_ciclo=coach.precio_ciclo,
        por_validar=[f for f in filas if f.chequeo_estado == "pendiente_evaluacion"],
        con_alerta=[f for f in filas if f.alerta is not None],
        activas=sum(1 for f in filas if f.estado == "activa"),
        por_cobrar=sum(1 for f in filas if f.adeudo > 0),
    )


@ruteador.get("/alumnas", response_model=list[FilaCartera])
def alumnas(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> list[FilaCartera]:
    return _filas_de_cartera(s)


@ruteador.post("/alumnas", response_model=AlumnaDadaDeAlta, status_code=201)
def dar_de_alta_alumna(
    cuerpo: AltaDeAlumna,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> AlumnaDadaDeAlta:
    """Alta de una alumna con su ciclo inicial y su invitación.

    La clave temporal se devuelve **una sola vez**, para que la coach pueda dictarla si el
    correo no llega. No se puede consultar después: solo se guarda su hash.
    """
    plan = q.tarifa_por_ulid(s, cuerpo.tarifa_ulid) if cuerpo.tarifa_ulid else None
    alta = cuentas.dar_de_alta(
        s,
        coach_id=actor.coach_id,
        nombre=cuerpo.nombre,
        correo=cuerpo.correo,
        whatsapp=cuerpo.whatsapp,
        fecha_nacimiento=cuerpo.fecha_nacimiento,
        estatura_cm=cuerpo.estatura_cm,
        tarifa_id=plan.id if plan else None,
        nivel_experiencia=cuerpo.nivel_experiencia,
        emitida_por=actor.usuario_id,
    )

    coach = s.get(Coach, actor.coach_id)
    _encolar_correo(
        s,
        actor.coach_id,
        Aviso.BIENVENIDA,
        para=alta.correo,
        llave=f"alumna:{alta.alumna_ulid}:bienvenida",
        contexto={
            "nombre": cuerpo.nombre.split(" ")[0],
            "coach": coach.nombre if coach else "tu coach",
            "clave": alta.clave_temporal,
        },
    )

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="coach",
        accion=bitacora.Accion.ALUMNA_DADA_DE_ALTA,
        entidad="alumna",
        detalle={"alumna_ulid": alta.alumna_ulid},
    )

    return AlumnaDadaDeAlta(
        alumna_ulid=alta.alumna_ulid, correo=alta.correo, clave_temporal=alta.clave_temporal
    )


@ruteador.put("/alumnas/{ulid}", response_model=FilaCartera)
def editar_alumna(
    ulid: str,
    cuerpo: EdicionDeAlumna,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> FilaCartera:
    """Edita el perfil operativo.

    **No toca el historial clínico ni los consentimientos**: esos los mantiene la alumna. Que
    la coach pueda editarlos rompería la trazabilidad de quién declaró qué.
    """
    alumna = q.alumna_por_ulid(s, ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")

    if not cuerpo.nombre.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)

    antes = {
        "nombre": alumna.nombre,
        "whatsapp": alumna.whatsapp,
        "estatura_cm": alumna.estatura_cm,
        "tarifa_id": alumna.tarifa_id,
        "nivel_experiencia": alumna.nivel_experiencia,
        "equipo": alumna.equipo,
        "ocupacion": alumna.ocupacion,
        "bascula_ref": alumna.bascula_ref,
        "lugar_ref": alumna.lugar_ref,
        "hora_ref": alumna.hora_ref,
        "estado": alumna.estado,
    }

    alumna.nombre = cuerpo.nombre.strip()
    alumna.whatsapp = cuerpo.whatsapp
    alumna.estatura_cm = cuerpo.estatura_cm
    plan = q.tarifa_por_ulid(s, cuerpo.tarifa_ulid) if cuerpo.tarifa_ulid else None
    alumna.tarifa_id = plan.id if plan else None
    alumna.nivel_experiencia = cuerpo.nivel_experiencia
    alumna.equipo = cuerpo.equipo
    alumna.ocupacion = cuerpo.ocupacion
    alumna.bascula_ref = cuerpo.bascula_ref
    alumna.lugar_ref = cuerpo.lugar_ref
    alumna.hora_ref = cuerpo.hora_ref
    if cuerpo.zona_horaria:
        alumna.zona_horaria = cuerpo.zona_horaria
    alumna.porcentaje_grasa_objetivo = cuerpo.porcentaje_grasa_objetivo
    if cuerpo.estado in {"activa", "pausa", "baja"}:
        alumna.estado = cuerpo.estado

    # Solo los nombres de los campos: copiar los valores duplicaría el dato sensible en un
    # registro que se conserva cinco años y sobrevive a la cancelación.
    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="coach",
        accion=bitacora.Accion.ALUMNA_EDITADA,
        entidad="alumna",
        entidad_id=alumna.id,
        detalle={
            "campos": bitacora.campos_cambiados(
                antes,
                {
                    "nombre": alumna.nombre,
                    "whatsapp": alumna.whatsapp,
                    "estatura_cm": alumna.estatura_cm,
                    "tarifa_id": alumna.tarifa_id,
                    "nivel_experiencia": alumna.nivel_experiencia,
                    "equipo": alumna.equipo,
                    "ocupacion": alumna.ocupacion,
                    "bascula_ref": alumna.bascula_ref,
                    "lugar_ref": alumna.lugar_ref,
                    "hora_ref": alumna.hora_ref,
                    "estado": alumna.estado,
                },
            )
        },
    )

    s.flush()
    fila = next((f for f in _filas_de_cartera(s) if f.ulid == ulid), None)
    if fila is None:  # pragma: no cover - defensivo
        raise HTTPException(404, "No existe esa alumna")
    return fila


@ruteador.delete("/alumnas/{ulid}", status_code=204)
def dar_de_baja_alumna(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    """Marca la baja; **no borra**.

    El borrado real es un derecho de la alumna (Cancelación, ARCO) y se procesa por ese
    flujo, con su constancia. Que la coach pueda borrar un expediente de un clic destruiría
    la trazabilidad que la ley exige conservar.
    """
    alumna = q.alumna_por_ulid(s, ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")

    alumna.estado = "baja"
    usuario = s.get(Usuario, alumna.usuario_id)
    if usuario is not None:
        usuario.estado = "inactivo"

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="coach",
        accion=bitacora.Accion.ALUMNA_DADA_DE_BAJA,
        entidad="alumna",
        entidad_id=alumna.id,
    )


@ruteador.post("/alumnas/{ulid}/clave-temporal", response_model=ClaveTemporalEmitida)
def clave_temporal(
    ulid: str,
    cuerpo: ClaveTemporalPedida,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> ClaveTemporalEmitida:
    alumna = q.alumna_por_ulid(s, ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")

    clave = cuentas.emitir_clave_temporal(s, alumna, actor.usuario_id, cuerpo.motivo_verificacion)

    coach = s.get(Coach, actor.coach_id)
    usuario = s.get(Usuario, alumna.usuario_id)
    if usuario is not None:
        _encolar_correo(
            s,
            actor.coach_id,
            Aviso.CLAVE_TEMPORAL,
            para=usuario.email,
            llave=f"alumna:{ulid}:clave:{ahora_utc().isoformat()}",
            contexto={
                "nombre": alumna.nombre.split(" ")[0],
                "coach": coach.nombre if coach else "tu coach",
                "clave": clave,
            },
        )

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="coach",
        accion=bitacora.Accion.CLAVE_TEMPORAL_EMITIDA,
        entidad="alumna",
        entidad_id=alumna.id,
        detalle={"verificacion": cuerpo.motivo_verificacion.strip()[:200]},
    )

    return ClaveTemporalEmitida(clave=clave, vence_en=ahora_utc() + VIGENCIA_CLAVE_TEMPORAL)


@ruteador.get("/alumnas/{ulid}/historial", response_model=HistorialPublico)
def historial_clinico(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> HistorialPublico:
    """Historial clínico de una alumna.

    **Cada apertura queda registrada** en `acceso_sensible` con quién y cuándo. Es obligación
    del Anexo Legal §6 y es lo que permite responder a una alumna que pregunta quién ha visto
    su expediente.
    """
    from sqlalchemy import func
    from sqlalchemy import select as _select

    from app.datos.modelos import HistorialClinico

    alumna = q.alumna_por_ulid(s, ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")

    historial = q.historial_vigente(s, alumna.id)
    if historial is None:
        raise HTTPException(404, "Todavía no hay historial clínico")

    # Se anota antes de devolver: si la respuesta falla a medio camino, es preferible una
    # lectura anotada de más que una sin anotar.
    bitacora.registrar_acceso(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        alumna_id=alumna.id,
        recurso=bitacora.Recurso.HISTORIAL_CLINICO,
    )

    versiones = (
        s.scalar(
            _select(func.count())
            .select_from(HistorialClinico)
            .where(HistorialClinico.alumna_id == alumna.id)
        )
        or 1
    )

    return HistorialPublico(
        lesiones=historial.lesiones,
        condiciones=historial.condiciones,
        medicacion=historial.medicacion,
        restricciones=historial.restricciones,
        vigente_desde=historial.vigente_desde,
        versiones=int(versiones),
    )


# ---------------------------------------------------------------------------
# Validación de chequeos
# ---------------------------------------------------------------------------


@ruteador.get("/chequeos/{ulid}/fotos", response_model=list[FotoPublica])
def fotos_de_chequeo(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> list[FotoPublica]:
    """Metadatos de las tres fotografías de un chequeo.

    **Cada apertura queda registrada.** La imagen en sí se pide por su propia ruta —servida
    con `X-Accel-Redirect` para que nginx la entregue sin cargarla en memoria de Python— y
    esa lectura vuelve a anotarse.
    """
    from sqlalchemy import select as _select

    from app.datos.modelos import Foto

    chequeo = q.chequeo_por_ulid(s, ulid)
    if chequeo is None:
        raise HTTPException(404, "No existe ese chequeo")

    bitacora.registrar_acceso(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        alumna_id=chequeo.alumna_id,
        recurso=bitacora.Recurso.FOTOS_DE_CHEQUEO,
    )

    retencion_dias = ajustes().retencion_fotos_meses * 30
    hoy = ahora_utc().date()

    fotos = s.scalars(_select(Foto).where(Foto.chequeo_id == chequeo.id).order_by(Foto.angulo))
    return [
        FotoPublica(
            angulo=f.angulo,
            disponible=f.purgada_en is None and f.storage_key is not None,
            nitidez=f.nitidez,
            luminancia=f.luminancia,
            estado_auto=f.estado_auto,
            es_linea_base=f.es_linea_base,
            tomada_en=f.tomada_en,
            purgada_en=f.purgada_en,
            # La línea base no se purga mientras la alumna siga activa, si lo autorizó.
            dias_para_purga=(
                None
                if f.purgada_en is not None or f.tomada_en is None or f.es_linea_base
                else max(0, retencion_dias - (hoy - f.tomada_en.date()).days)
            ),
        )
        for f in fotos
    ]


@ruteador.put("/chequeos/{ulid}/grasa", status_code=204)
def estimar_grasa(
    ulid: str,
    cuerpo: EstimacionGrasa,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    """El porcentaje de grasa que estima la coach viendo las fotos.

    Vive en el chequeo y no en el perfil: es lo que permite graficar su evolución mes a mes,
    y es la entrada que manda toda la cadena de la calculadora.
    """
    if not (0 < float(cuerpo.porcentaje_grasa) < 1):
        raise ErrorDeDominio(
            Codigo.PORCENTAJE_DE_GRASA_INVALIDO, valor=str(cuerpo.porcentaje_grasa)
        )

    chequeo = q.chequeo_por_ulid(s, ulid)
    if chequeo is None:
        raise HTTPException(404, "No existe ese chequeo")

    chequeo.porcentaje_grasa = cuerpo.porcentaje_grasa
    chequeo.estimado_por = actor.usuario_id

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="coach",
        accion=bitacora.Accion.GRASA_ESTIMADA,
        entidad="chequeo",
        entidad_id=chequeo.id,
    )


@ruteador.post("/chequeos/{ulid}/validar", status_code=204)
def validar(
    ulid: str,
    cuerpo: ValidacionChequeo,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    from app.dominio.chequeo import EstadoChequeo, Transicion
    from app.dominio.chequeo import transicionar as transicionar_chequeo

    chequeo = q.chequeo_por_ulid(s, ulid)
    if chequeo is None:
        raise HTTPException(404, "No existe ese chequeo")

    # Sin porcentaje de grasa no se puede armar el plan del ciclo siguiente, así que validar
    # sin él dejaría el expediente a medias.
    if chequeo.porcentaje_grasa is None:
        raise ErrorDeDominio(Codigo.SIN_PORCENTAJE_DE_GRASA_DEL_CHEQUEO)

    chequeo.estado = transicionar_chequeo(
        EstadoChequeo(chequeo.estado),
        Transicion.VALIDAR,
        justificacion_outlier=cuerpo.justificacion_outlier,
        alerta_outlier_abierta=chequeo.alerta_outlier,
    ).value
    chequeo.feedback = cuerpo.feedback
    chequeo.justificacion_outlier = cuerpo.justificacion_outlier
    chequeo.validado_en = ahora_utc()
    chequeo.validado_por = actor.usuario_id

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="coach",
        accion=bitacora.Accion.CHEQUEO_VALIDADO,
        entidad="chequeo",
        entidad_id=chequeo.id,
        detalle={"sobrescribio_outlier": chequeo.alerta_outlier},
    )


@ruteador.post("/chequeos/{ulid}/rechazar", status_code=204)
def rechazar(
    ulid: str,
    cuerpo: RechazoChequeo,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    from app.dominio.chequeo import EstadoChequeo, Transicion
    from app.dominio.chequeo import transicionar as transicionar_chequeo

    chequeo = q.chequeo_por_ulid(s, ulid)
    if chequeo is None:
        raise HTTPException(404, "No existe ese chequeo")

    chequeo.estado = transicionar_chequeo(
        EstadoChequeo(chequeo.estado), Transicion.RECHAZAR, motivo=cuerpo.motivo
    ).value
    chequeo.motivo_rechazo = cuerpo.motivo
    chequeo.validado_por = actor.usuario_id

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="coach",
        accion=bitacora.Accion.CHEQUEO_RECHAZADO,
        entidad="chequeo",
        entidad_id=chequeo.id,
    )


# ---------------------------------------------------------------------------
# Agenda
# ---------------------------------------------------------------------------


def _cita_publica(s: Session, c: Cita) -> CitaPublica:
    alumna = s.get(Alumna, c.alumna_id) if c.alumna_id is not None else None

    return CitaPublica(
        ulid=c.ulid,
        titulo=c.titulo,
        tipo=c.tipo,
        estado=c.estado,
        modalidad=c.modalidad,
        # El ULID viaja: sin él la pantalla no puede volver a abrir la cita en el
        # expediente de quien es, y el selector de alumna salía siempre vacío al editar.
        alumna_ulid=alumna.ulid if alumna else None,
        alumna_nombre=alumna.nombre if alumna else None,
        inicia_en=c.inicia_en,
        termina_en=c.termina_en,
        notas=c.notas,
        motivo_cancelacion=c.motivo_cancelacion,
    )


@ruteador.get("/agenda", response_model=AgendaDeCoach)
def agenda(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
    desde: Annotated[datetime, Query()],
    dias: Annotated[int, Query(ge=1, le=62)] = 7,
) -> AgendaDeCoach:
    """Las consultas y, como marca aparte, los cobros programados de esos días.

    Un cobro no es una cita: no tiene hora, no ocupa hueco y no se puede solapar con nada.
    Pero sí es algo que le toca ese día, así que sale en su semana.
    """
    _ = actor
    hasta = desde + timedelta(days=dias)
    citas = [_cita_publica(s, c) for c in q.citas_entre(s, desde, hasta)]

    alumnas = {a.id: a for a in q.cartera(s)}
    hoy = ahora_utc().date()
    cobros = [
        MarcaDeCobro(
            ulid=c.ulid,
            fecha=c.fecha,
            alumna_ulid=alumnas[c.alumna_id].ulid,
            alumna=alumnas[c.alumna_id].nombre,
            concepto=c.concepto or c.motivo,
            monto=c.monto,
            estado=c.estado,
            vencido=c.estado == "pendiente" and c.fecha < hoy,
        )
        for c in q.cobros_entre(s, desde.date(), hasta.date())
        if c.alumna_id in alumnas
    ]

    return AgendaDeCoach(citas=citas, cobros=cobros)


def _franjas_de(s: Session, alrededor: datetime) -> list[Franja]:
    """La agenda de la semana, para comprobar solape sin traerla completa."""
    vecinas = q.citas_entre(s, alrededor - timedelta(days=1), alrededor + timedelta(days=2))
    return [
        Franja(id=c.id, inicia_en=c.inicia_en, termina_en=c.termina_en, estado=EstadoCita(c.estado))
        for c in vecinas
    ]


def _avisar_de_cita(
    s: Session, actor: Actor, cita: Cita, alumna: Alumna, aviso: Aviso, motivo: str = ""
) -> None:
    """Le avisa a la alumna. Una consulta que se agenda y no se comunica no existe para ella.

    La llave lleva el instante de la cita: mover la misma consulta dos veces manda dos
    avisos, que es justo lo que se quiere, y reintentar el mismo cambio no manda dos.
    """
    usuario = s.get(Usuario, alumna.usuario_id)
    if usuario is None:  # pragma: no cover - defensivo
        return

    coach = s.get(Coach, actor.coach_id)
    cola.encolar(
        s,
        aviso,
        coach_id=actor.coach_id,
        llave=f"cita:{cita.ulid}:{aviso.value}:{cita.inicia_en.isoformat()}",
        para=usuario.email,
        contexto={
            "nombre": alumna.nombre.split(" ")[0],
            "coach": (coach.marca or coach.nombre) if coach else "tu coach",
            "fecha": f"{cita.inicia_en:%d/%m/%Y}",
            "hora_inicio": f"{cita.inicia_en:%H:%M}",
            "hora_fin": f"{cita.termina_en:%H:%M}",
            "modalidad": cita.modalidad,
            "detalle": cita.titulo,
            "motivo": motivo,
        },
        destinatario_id=alumna.usuario_id,
    )


@ruteador.post("/agenda", response_model=CitaPublica, status_code=201)
def agendar_cita(
    cuerpo: CitaNueva,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> CitaPublica:
    # Toda cita es de alguien: la agenda de la coach y el expediente de la alumna son la
    # misma cosa vista desde dos lados, y una cita sin dueña no cabe en el segundo.
    if not cuerpo.alumna_ulid:
        raise HTTPException(422, "Elige de quién es la consulta")
    alumna = q.alumna_por_ulid(s, cuerpo.alumna_ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")
    alumna_id = alumna.id

    # Dos citas no pueden solaparse aunque una sea consulta y la otra bloque de trabajo: el
    # tiempo de la coach es uno solo.
    agendar(
        Franja(id=None, inicia_en=cuerpo.inicia_en, termina_en=cuerpo.termina_en),
        _franjas_de(s, cuerpo.inicia_en),
        ahora=ahora_utc(),
    )

    cita = Cita(
        coach_id=actor.coach_id,
        alumna_id=alumna_id,
        titulo=cuerpo.titulo,
        tipo=cuerpo.tipo,
        modalidad=cuerpo.modalidad,
        inicia_en=cuerpo.inicia_en,
        termina_en=cuerpo.termina_en,
        notas=cuerpo.notas,
    )
    s.add(cita)
    s.flush()
    _avisar_de_cita(s, actor, cita, alumna, Aviso.CITA_AGENDADA)
    return _cita_publica(s, cita)


@ruteador.put("/agenda/{ulid}", response_model=CitaPublica)
def editar_cita(
    ulid: str,
    cuerpo: CitaNueva,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> CitaPublica:
    cita = q.cita_por_ulid(s, ulid)
    if cita is None:
        raise HTTPException(404, "No existe esa cita")

    # `id` va en la franja para que la cita no choque consigo misma al moverse.
    agendar(
        Franja(id=cita.id, inicia_en=cuerpo.inicia_en, termina_en=cuerpo.termina_en),
        _franjas_de(s, cuerpo.inicia_en),
        ahora=ahora_utc(),
        permitir_pasado=True,
    )

    if not cuerpo.alumna_ulid:
        raise HTTPException(422, "Elige de quién es la consulta")
    alumna = q.alumna_por_ulid(s, cuerpo.alumna_ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")

    # Se mira antes de tocar la fila: es lo que decide si esto es un cambio de horario que
    # hay que comunicarle o un ajuste de título que no le importa.
    se_movio = cita.inicia_en != cuerpo.inicia_en or cita.alumna_id != alumna.id

    cita.alumna_id = alumna.id
    cita.titulo = cuerpo.titulo
    cita.tipo = cuerpo.tipo
    cita.modalidad = cuerpo.modalidad
    cita.inicia_en = cuerpo.inicia_en
    cita.termina_en = cuerpo.termina_en
    cita.notas = cuerpo.notas
    s.flush()

    if se_movio:
        _avisar_de_cita(s, actor, cita, alumna, Aviso.CITA_REAGENDADA)
    return _cita_publica(s, cita)


@ruteador.post("/agenda/{ulid}/cancelar", response_model=CitaPublica)
def cancelar_cita(
    ulid: str,
    cuerpo: CancelacionCita,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> CitaPublica:
    cita = q.cita_por_ulid(s, ulid)
    if cita is None:
        raise HTTPException(404, "No existe esa cita")

    cita.estado = transicionar(
        EstadoCita(cita.estado), EstadoCita.CANCELADA, motivo=cuerpo.motivo
    ).value
    cita.motivo_cancelacion = cuerpo.motivo
    cita.cancelada_en = ahora_utc()
    s.flush()

    alumna = s.get(Alumna, cita.alumna_id) if cita.alumna_id else None
    if alumna is not None:
        _avisar_de_cita(s, actor, cita, alumna, Aviso.CITA_CANCELADA, motivo=cuerpo.motivo)
    return _cita_publica(s, cita)


@ruteador.delete("/agenda/{ulid}", status_code=204)
def eliminar_cita(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    cita = q.cita_por_ulid(s, ulid)
    if cita is None:
        raise HTTPException(404, "No existe esa cita")
    s.delete(cita)


# ---------------------------------------------------------------------------
# Marca
# ---------------------------------------------------------------------------


@ruteador.get("/marca", response_model=MarcaPublica)
def ver_marca(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> MarcaPublica:
    coach = s.get(Coach, actor.coach_id)
    if coach is None:  # pragma: no cover - defensivo
        raise ErrorDeDominio(Codigo.SIN_PERMISO)
    return MarcaPublica(
        nombre=coach.nombre,
        marca=coach.marca or coach.nombre,
        color_acento=coach.color_acento,
        tiene_logo=coach.logo_key is not None,
    )


@ruteador.put("/marca", response_model=MarcaPublica)
def editar_marca(
    cuerpo: EdicionDeMarca,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> MarcaPublica:
    """Nombre, nombre comercial y color.

    El color se guarda tal cual y es el unico token que cambia con la marca: negro y gris son
    la estructura y no se tocan.
    """
    coach = s.get(Coach, actor.coach_id)
    if coach is None:  # pragma: no cover - defensivo
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    if not cuerpo.nombre.strip() or not cuerpo.marca.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", cuerpo.color_acento):
        raise HTTPException(422, "El color va en formato #rrggbb")

    coach.nombre = cuerpo.nombre.strip()[:120]
    coach.marca = cuerpo.marca.strip()[:120]
    coach.color_acento = cuerpo.color_acento
    s.flush()

    return MarcaPublica(
        nombre=coach.nombre,
        marca=coach.marca,
        color_acento=coach.color_acento,
        tiene_logo=coach.logo_key is not None,
    )


@ruteador.put("/logo", response_model=MarcaPublica)
async def subir_logo(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
    archivo: Annotated[UploadFile, File()],
) -> MarcaPublica:
    """Sube el logo de la marca.

    Se recorta al centro y se cuadra, no se deforma. Nombre de archivo fijo: subir otro
    reemplaza el anterior en lugar de acumular versiones que nadie va a borrar.
    """
    coach = s.get(Coach, actor.coach_id)
    if coach is None:  # pragma: no cover - defensivo
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    try:
        contenido = imagenes.logo(await archivo.read())
    except imagenes.ImagenInvalida as causa:
        raise HTTPException(422, str(causa)) from causa

    llave = almacenamiento.llave_de_logo(actor.coach_id)
    almacen().guardar(llave, contenido)
    coach.logo_key = llave
    s.flush()

    return MarcaPublica(
        nombre=coach.nombre,
        marca=coach.marca or coach.nombre,
        color_acento=coach.color_acento,
        tiene_logo=True,
    )


# ---------------------------------------------------------------------------
# Expediente de validacion
# ---------------------------------------------------------------------------


def _chequeo_de_validacion(
    c: Chequeo, numero: int, peso: Decimal | None, medidas: dict[str, Decimal]
) -> ChequeoDeValidacion:
    return ChequeoDeValidacion(
        ulid=c.ulid,
        numero=numero,
        fecha=c.fecha,
        estado=c.estado,
        peso_kg=peso,
        porcentaje_grasa=c.porcentaje_grasa,
        medidas=medidas,
        nota_alumna=c.nota_alumna,
        alerta_outlier=c.alerta_outlier,
        varianza_confirmada=c.varianza_confirmada,
        bascula_usada=c.bascula_usada,
        lugar_usado=c.lugar_usado,
        hora_usada=c.hora_usada,
    )


@ruteador.get("/alumnas/{ulid}/validacion", response_model=ExpedienteDeValidacion)
def expediente_de_validacion(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> ExpedienteDeValidacion:
    """Todo lo que la pantalla de validacion necesita, en una llamada.

    Las fotografias **no** viajan aqui: se piden por su propia ruta, que es la que deja
    constancia de que esta coach las abrio y cuando.
    """
    alumna = q.alumna_por_ulid(s, ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")

    # Sin borradores: uno vacío se colaba como «el actual» y la pantalla pedía estimar la
    # grasa de un chequeo sin peso, rechazando cualquier valor que la coach escribiera.
    historia = q.chequeos_enviados(s, alumna.id)
    ids = [c.id for c in historia]
    pesos = q.peso_de_chequeo(s, ids)
    medidas = q.medidas_de(s, ids)

    publicos = [
        _chequeo_de_validacion(c, i + 1, pesos.get(c.id), medidas.get(c.id, {}))
        for i, c in enumerate(historia)
    ]

    # El que toca validar es el ultimo pendiente; si no hay ninguno, el ultimo enviado, para
    # que la pantalla siga sirviendo de consulta despues de validar.
    pendientes = [p for p in publicos if p.estado == "pendiente_evaluacion"]
    actual = pendientes[-1] if pendientes else (publicos[-1] if publicos else None)
    anteriores = [p for p in publicos if actual is None or p.ulid != actual.ulid]

    historial = q.historial_vigente(s, alumna.id)
    if historial is not None:
        bitacora.registrar_acceso(
            s,
            coach_id=actor.coach_id,
            actor_id=actor.usuario_id,
            alumna_id=alumna.id,
            recurso=bitacora.Recurso.EXPEDIENTE,
        )

    return ExpedienteDeValidacion(
        alumna_ulid=alumna.ulid,
        alumna=alumna.nombre,
        estatura_cm=alumna.estatura_cm,
        plan=None,
        actual=actual,
        anteriores=anteriores,
        lesiones=historial.lesiones if historial else None,
        restricciones=historial.restricciones if historial else None,
    )
