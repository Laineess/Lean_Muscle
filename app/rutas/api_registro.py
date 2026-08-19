"""Registro abierto: la liga pública de cada coach y el recorrido de quien llega por ella.

Tres de estas rutas son las únicas de la aplicación que responden **sin sesión**. Por eso
resuelven el inquilino desde el `slug` de la liga y no de un cuerpo: un `coach_id` que
venga del cliente se ignora aquí igual que en todas partes.

Lo demás del recorrido —presentación, cuestionario, huecos, cita y comprobante— reusa los
endpoints que ya existen para la alumna. Lo que la distingue mientras tanto es su estado:
`solicitud` la deja fuera de la cartera, del límite y del chequeo.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc, edad_en, en_zona
from app.config import ajustes
from app.datos.alcance import motor, sesion_con_alcance
from app.datos.modelos import (
    Alumna,
    Cita,
    Coach,
    CobroProgramado,
    SolicitudDeRegistro,
    Tarifa,
    Usuario,
)
from app.datos.repos import consultas as q
from app.dominio import registro as dom
from app.dominio.avisos import Aviso
from app.rutas import archivos
from app.rutas.api_comprobantes import validar as validar_comprobante
from app.rutas.auth import actor_publico, crear_sesion
from app.rutas.esquemas import (
    AceptacionDeSolicitud,
    ActorPublico,
    CodigoDeRegistro,
    CorreoDeRegistro,
    DescarteDeSolicitud,
    EstadoDeSolicitud,
    InterruptorDeRegistro,
    LigaDeRegistro,
    RegistroAceptado,
    RegistroDeCoach,
    RegistroNuevo,
    SolicitudEnBandeja,
)
from app.rutas.sesion import Actor, RutaQueConfirma, datos, solo_alumna, solo_coach
from app.servicios import avisos as cola
from app.servicios import bitacora, limites, registro

ruteador = APIRouter(prefix="/api", tags=["registro abierto"], route_class=RutaQueConfirma)


def _coach_de_la_liga(s: Session, slug: str) -> Coach:
    coach = registro.coach_por_slug(s, slug)
    if coach is None:
        # 404 y no 403: una liga que no existe y una apagada tienen que verse igual desde
        # fuera, o la propia respuesta sirve para descubrir qué coaches hay dadas de alta.
        raise HTTPException(404, "Esa liga no existe")
    return coach


def _solicitud_por_correo(s: Session, coach_id: int, correo: str) -> SolicitudDeRegistro:
    """La solicitud de ese correo dentro de esta coach.

    El correo es único en toda la plataforma, así que la búsqueda cruza inquilinos; después
    se comprueba que sea de esta coach, porque una alumna de otra no existe para esta liga.
    """
    usuario = s.scalars(
        select(Usuario)
        .where(Usuario.email == correo.strip().lower())
        .execution_options(sin_alcance=True)
    ).first()
    if usuario is None or usuario.coach_id != coach_id:
        raise HTTPException(404, "No hay ningún registro con ese correo")

    alumna = s.scalars(
        select(Alumna)
        .where(Alumna.usuario_id == usuario.id)
        .execution_options(sin_alcance=True)
    ).first()
    if alumna is None:
        raise HTTPException(404, "No hay ningún registro con ese correo")

    solicitud = s.scalars(
        select(SolicitudDeRegistro)
        .where(SolicitudDeRegistro.alumna_id == alumna.id)
        .execution_options(sin_alcance=True)
    ).first()
    if solicitud is None:
        raise HTTPException(404, "No hay ningún registro con ese correo")
    return solicitud


# ---------------------------------------------------------------------------
# Sin sesión: la liga pública
# ---------------------------------------------------------------------------


@ruteador.get("/registro/{slug}", response_model=LigaDeRegistro)
def ver_liga(slug: str) -> LigaDeRegistro:
    """Lo que ve quien abre la liga. Sin sesión: es la puerta de entrada."""
    with Session(motor()) as s:
        coach = _coach_de_la_liga(s, slug)
        coach_id, marca, nombre, color = (
            coach.id,
            coach.marca or coach.nombre,
            coach.nombre,
            coach.color_acento,
        )
        tiene_logo = coach.logo_key is not None
        abierto = coach.registro_abierto

    with sesion_con_alcance(coach_id) as s:
        servicios = registro.servicios_de_inscripcion(s)
        precio = servicios[0].precio if len(servicios) == 1 else None
        concepto = servicios[0].nombre if len(servicios) == 1 else None

    motivo = None
    if not abierto:
        motivo = "Tu coach todavía no abrió su registro en línea."
    elif len(servicios) != 1:
        motivo = "Falta definir el precio de inscripción."

    return LigaDeRegistro(
        coach=nombre,
        marca=marca,
        color_acento=color,
        tiene_logo=tiene_logo,
        abierta=motivo is None,
        motivo=motivo,
        precio_inscripcion=precio,
        concepto_inscripcion=concepto,
    )


@ruteador.get("/registro/{slug}/logo")
def logo_de_la_liga(slug: str) -> Response:
    """El logo de la coach en su página de registro.

    Va sin sesión porque quien la abre todavía no tiene ninguna, y una marca comercial no es
    un dato de nadie: es lo que la coach reparte por WhatsApp.
    """
    with Session(motor()) as s:
        coach = _coach_de_la_liga(s, slug)
        llave = coach.logo_key

    if not llave:
        raise HTTPException(404, "Esta marca no tiene logo")
    return archivos.servir(llave)


@ruteador.post("/registro/{slug}", response_model=RegistroAceptado, status_code=201)
def registrarse(slug: str, cuerpo: RegistroNuevo, peticion: Request) -> RegistroAceptado:
    """Crea la solicitud y manda el código al correo.

    Si el correo no sale, la petición entera se deshace: más vale que vuelva a intentarlo
    que dejarle una cuenta a medias que nadie puede verificar.
    """
    if not (cuerpo.acepta_terminos and cuerpo.acepta_privacidad):
        raise HTTPException(422, "Hay que aceptar los términos y el aviso de privacidad")

    ip = peticion.client.host if peticion.client else None

    with Session(motor()) as s:
        coach = _coach_de_la_liga(s, slug)
        coach_id = coach.id
        marca = coach.marca or coach.nombre
        if limites.registros_agotados(s, ip):
            raise ErrorDeDominio(Codigo.DEMASIADOS_REGISTROS)

    with sesion_con_alcance(coach_id) as s:
        alta = registro.crear(
            s,
            coach=s.get(Coach, coach_id),  # type: ignore[arg-type]
            nombre=cuerpo.nombre,
            correo=cuerpo.correo,
            contrasena=cuerpo.contrasena,
            fecha_nacimiento=cuerpo.fecha_nacimiento,
            whatsapp=cuerpo.whatsapp,
            ip=ip,
            user_agent=peticion.headers.get("user-agent") or "",
        )
        # Dentro de la transacción a propósito: si el correo revienta, no queda solicitud.
        registro.mandar_codigo(marca, alta.correo, alta.codigo)

    return RegistroAceptado(
        correo=alta.correo,
        # En local el emisor es de mentira y el código no llega a ningún buzón; sin esto no
        # se puede recorrer la pantalla siguiente.
        codigo=None if ajustes().es_produccion else alta.codigo,
    )


@ruteador.post("/registro/{slug}/codigo", response_model=ActorPublico)
def verificar_codigo(
    slug: str, cuerpo: CodigoDeRegistro, peticion: Request, respuesta: Response
) -> ActorPublico:
    """Confirma el correo y la deja dentro: a partir de aquí el recorrido va con sesión."""
    with Session(motor()) as s:
        coach_id = _coach_de_la_liga(s, slug).id

    with sesion_con_alcance(coach_id) as s:
        solicitud = _solicitud_por_correo(s, coach_id, cuerpo.correo)
        registro.verificar(s, solicitud, cuerpo.codigo)
        alumna = s.get(Alumna, solicitud.alumna_id)
        if alumna is None or alumna.usuario_id is None:  # pragma: no cover - defensivo
            raise ErrorDeDominio(Codigo.SIN_PERMISO)
        usuario_id = alumna.usuario_id
        crear_sesion(s, coach_id, usuario_id, peticion, respuesta)

    return actor_publico(coach_id, usuario_id, "alumna")


@ruteador.post("/registro/{slug}/codigo/reenviar", status_code=204)
def reenviar_codigo(slug: str, cuerpo: CorreoDeRegistro) -> None:
    with Session(motor()) as s:
        coach = _coach_de_la_liga(s, slug)
        coach_id, marca = coach.id, coach.marca or coach.nombre

    with sesion_con_alcance(coach_id) as s:
        solicitud = _solicitud_por_correo(s, coach_id, cuerpo.correo)
        dom.exigir_espera_entre_codigos(solicitud.codigo_vence_en, ahora_utc())
        codigo = registro.reemitir_codigo(s, solicitud)
        registro.mandar_codigo(marca, cuerpo.correo.strip().lower(), codigo)


# ---------------------------------------------------------------------------
# Con sesión: dónde va su registro
# ---------------------------------------------------------------------------


def _avisar_a_la_coach(s: Session, coach_id: int, alumna: Alumna) -> None:
    """Termino su parte: sin esto la coach se entera al abrir la bandeja por casualidad."""
    usuario = q.usuario_de_coach(s)
    if usuario is None:  # pragma: no cover - defensivo
        return

    cola.encolar(
        s,
        Aviso.SOLICITUD_RECIBIDA,
        coach_id=coach_id,
        llave=f"solicitud:{alumna.ulid}:recibida",
        para=usuario.email,
        contexto={"alumna": alumna.nombre},
        destinatario_id=usuario.id,
    )


@ruteador.get("/mi/solicitud", response_model=EstadoDeSolicitud)
def mi_solicitud(
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> EstadoDeSolicitud:
    """En qué punto va. Una alumna ya aceptada recibe `esSolicitud: false` y no un 404:
    la pantalla la llama antes de saber cuál de las dos es."""
    alumna = q.alumna_de_usuario(s, actor.usuario_id)
    if alumna is None:
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    coach = s.get(Coach, actor.coach_id)
    nombre_coach = (coach.marca or coach.nombre) if coach else ""

    # Una solicitud ya decidida deja de serlo: la fila se queda hasta la purga, pero la
    # alumna aceptada tiene que salir de la pantalla de espera y entrar a su panel.
    solicitud = registro.solicitud_de_alumna(s, alumna.id)
    if solicitud is None or dom.Estado(solicitud.estado) in dom.CERRADAS:
        return EstadoDeSolicitud(
            es_solicitud=False,
            estado=solicitud.estado if solicitud is not None else "",
            paso=dom.Paso.LISTA.value,
            coach=nombre_coach,
            cuestionario_completo=alumna.cuestionario_completo,
            tiene_cita=False,
            comprobante_subido=False,
        )

    cita = s.scalars(
        select(Cita)
        .where(Cita.alumna_id == alumna.id, Cita.estado != "cancelada")
        .order_by(Cita.inicia_en)
    ).first()
    # Rechazado cuenta como no subido: la coach lo devolvió y le toca mandar otro. El
    # archivo se conserva —es la prueba de lo que mandó—, así que mirar la llave mentiría.
    comprobante = s.scalars(
        select(CobroProgramado).where(
            CobroProgramado.alumna_id == alumna.id,
            CobroProgramado.motivo == "inscripcion",
            CobroProgramado.estado.in_(("en_revision", "pagado")),
        )
    ).first()

    paso = dom.paso_actual(
        estado=dom.Estado(solicitud.estado),
        cuestionario_completo=alumna.cuestionario_completo,
        tiene_cita=cita is not None,
        comprobante_subido=comprobante is not None,
    )
    if registro.marcar_si_termino(s, solicitud, paso):
        _avisar_a_la_coach(s, actor.coach_id, alumna)

    return EstadoDeSolicitud(
        es_solicitud=True,
        estado=solicitud.estado,
        paso=paso.value,
        coach=nombre_coach,
        cuestionario_completo=alumna.cuestionario_completo,
        tiene_cita=cita is not None,
        comprobante_subido=comprobante is not None,
        vence_en=dom.vence_el(solicitud.creado_en),
        cita_inicia_en=cita.inicia_en if cita else None,
    )


# ---------------------------------------------------------------------------
# La coach enciende y apaga su liga
# ---------------------------------------------------------------------------


@ruteador.get("/coach/registro", response_model=RegistroDeCoach)
def ver_registro(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> RegistroDeCoach:
    coach = s.get(Coach, actor.coach_id)
    if coach is None:  # pragma: no cover - defensivo
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    servicios = registro.servicios_de_inscripcion(s)
    pendientes = len(
        list(
            s.scalars(
                select(SolicitudDeRegistro).where(
                    SolicitudDeRegistro.estado == dom.Estado.ESPERANDO.value
                )
            )
        )
    )

    motivo = None
    if len(servicios) == 0:
        motivo = "Agrega un precio con motivo «inscripción» en Planes y precios."
    elif len(servicios) > 1:
        motivo = f"Tienes {len(servicios)} precios de inscripción y solo puede haber uno."

    return RegistroDeCoach(
        abierto=coach.registro_abierto,
        liga=f"/r/{coach.slug}",
        puede_encenderse=motivo is None,
        motivo=motivo,
        servicios_de_inscripcion=len(servicios),
        precio_inscripcion=servicios[0].precio if len(servicios) == 1 else None,
        solicitudes_pendientes=pendientes,
    )


@ruteador.put("/coach/registro", response_model=RegistroDeCoach)
def guardar_registro(
    cuerpo: InterruptorDeRegistro,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> RegistroDeCoach:
    coach = s.get(Coach, actor.coach_id)
    if coach is None:  # pragma: no cover - defensivo
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    if cuerpo.abierto:
        # Se comprueba al encender y no solo al registrarse: enterarse de que el precio
        # está mal por una alumna que no pudo registrarse es enterarse tarde.
        dom.exigir_abierto(True, len(registro.servicios_de_inscripcion(s)))

    coach.registro_abierto = cuerpo.abierto
    s.flush()
    return ver_registro(actor, s)


# ---------------------------------------------------------------------------
# La bandeja de la coach
# ---------------------------------------------------------------------------


def _fila_de_bandeja(s: Session, solicitud: SolicitudDeRegistro) -> SolicitudEnBandeja | None:
    alumna = s.get(Alumna, solicitud.alumna_id)
    if alumna is None:  # pragma: no cover - defensivo
        return None

    usuario = s.get(Usuario, alumna.usuario_id)
    tarifa = s.get(Tarifa, alumna.tarifa_id) if alumna.tarifa_id else None

    cita = s.scalars(
        select(Cita)
        .where(Cita.alumna_id == alumna.id, Cita.estado != "cancelada")
        .order_by(Cita.inicia_en)
    ).first()
    cobro = s.scalars(
        select(CobroProgramado).where(
            CobroProgramado.alumna_id == alumna.id, CobroProgramado.motivo == "inscripcion"
        )
    ).first()

    leido = (cobro.ocr or {}).get("monto") if cobro else None
    paso = dom.paso_actual(
        estado=dom.Estado(solicitud.estado),
        cuestionario_completo=alumna.cuestionario_completo,
        tiene_cita=cita is not None,
        comprobante_subido=cobro is not None and cobro.estado in ("en_revision", "pagado"),
    )

    return SolicitudEnBandeja(
        ulid=solicitud.ulid,
        alumna_ulid=alumna.ulid,
        nombre=alumna.nombre,
        correo=usuario.email if usuario else "",
        whatsapp=alumna.whatsapp,
        edad=edad_en(alumna.fecha_nacimiento, ahora_utc().date()),
        estado=solicitud.estado,
        paso=paso.value,
        registrada_en=solicitud.creado_en,
        borra_en=dom.borra_el(
            dom.Estado(solicitud.estado), solicitud.creado_en, solicitud.decidida_en
        ),
        cuestionario_completo=alumna.cuestionario_completo,
        plan_pedido=tarifa.nombre if tarifa else None,
        plan_pedido_ulid=tarifa.ulid if tarifa else None,
        precio_plan=tarifa.precio if tarifa else None,
        cita_inicia_en=cita.inicia_en if cita else None,
        cita_modalidad=cita.modalidad if cita else None,
        cobro_ulid=cobro.ulid if cobro else None,
        monto_inscripcion=cobro.monto if cobro else None,
        estado_del_pago=cobro.estado if cobro else None,
        monto_leido=Decimal(str(leido)) if leido not in (None, "") else None,
        motivo_descarte=solicitud.motivo_descarte,
    )


@ruteador.get("/coach/solicitudes", response_model=list[SolicitudEnBandeja])
def bandeja(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> list[SolicitudEnBandeja]:
    """Quién llegó por su liga y todavía no está decidido.

    Trae también las que van a medias: saber que hay tres empezadas y una lista es parte de
    decidir, y sin eso la coach solo ve las que ya terminaron.
    """
    _ = actor
    filas = [_fila_de_bandeja(s, x) for x in registro.esperando(s)]
    return [f for f in filas if f is not None]


@ruteador.post("/coach/solicitudes/{ulid}/aceptar", response_model=SolicitudEnBandeja)
def aceptar_solicitud(
    ulid: str,
    cuerpo: AceptacionDeSolicitud,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> SolicitudEnBandeja:
    """La acepta: confirma su cita, abre su ciclo y le deja el chequeo disponible."""
    solicitud = registro.por_ulid(s, ulid)
    if solicitud is None:
        raise HTTPException(404, "No existe esa solicitud")

    alumna = s.get(Alumna, solicitud.alumna_id)
    if alumna is None:  # pragma: no cover - defensivo
        raise HTTPException(404, "No existe esa solicitud")
    if not alumna.cuestionario_completo:
        raise HTTPException(409, "Todavía no contesta su cuestionario")

    tarifa = None
    if cuerpo.tarifa_ulid:
        tarifa = s.scalars(select(Tarifa).where(Tarifa.ulid == cuerpo.tarifa_ulid)).first()
        if tarifa is None or not tarifa.activa:
            raise HTTPException(422, "Ese plan ya no está disponible")
    elif alumna.tarifa_id:
        tarifa = s.get(Tarifa, alumna.tarifa_id)

    registro.aceptar(s, solicitud, alumna, tarifa)

    # La cita queda en firme: hasta ahora estaba agendada por ella, no confirmada por nadie.
    cita = s.scalars(
        select(Cita)
        .where(Cita.alumna_id == alumna.id, Cita.estado == "agendada")
        .order_by(Cita.inicia_en)
    ).first()
    if cita is not None:
        cita.estado = "confirmada"

    cobro = s.scalars(
        select(CobroProgramado).where(
            CobroProgramado.alumna_id == alumna.id,
            CobroProgramado.motivo == "inscripcion",
        )
    ).first()
    if cuerpo.validar_pago and cobro is not None and cobro.estado != "pagado":
        # La misma puerta que la bandeja de comprobantes: registra el ingreso, salda el
        # cobro y le avisa. Duplicar eso aquí es como se descuadra la contabilidad.
        validar_comprobante(cobro.ulid, actor, s)

    _avisar_de_la_decision(s, actor, alumna, Aviso.SOLICITUD_ACEPTADA, tarifa, cita)

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="coach",
        accion=bitacora.Accion.SOLICITUD_ACEPTADA,
        entidad="alumna",
        entidad_id=alumna.id,
        detalle={"campos_cambiados": "estado,tarifa_id"},
    )

    fila = _fila_de_bandeja(s, solicitud)
    if fila is None:  # pragma: no cover - defensivo
        raise HTTPException(404, "No existe esa solicitud")
    return fila


@ruteador.post("/coach/solicitudes/{ulid}/descartar", response_model=SolicitudEnBandeja)
def descartar_solicitud(
    ulid: str,
    cuerpo: DescarteDeSolicitud,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> SolicitudEnBandeja:
    """La descarta con su motivo. Pierde el acceso hoy y su expediente se borra a los 7 días."""
    solicitud = registro.por_ulid(s, ulid)
    if solicitud is None:
        raise HTTPException(404, "No existe esa solicitud")

    alumna = s.get(Alumna, solicitud.alumna_id)
    if alumna is None:  # pragma: no cover - defensivo
        raise HTTPException(404, "No existe esa solicitud")

    registro.descartar(s, solicitud, alumna, cuerpo.motivo)
    _avisar_de_la_decision(
        s, actor, alumna, Aviso.SOLICITUD_DESCARTADA, None, None, cuerpo.motivo.strip()
    )

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="coach",
        accion=bitacora.Accion.SOLICITUD_DESCARTADA,
        entidad="alumna",
        entidad_id=alumna.id,
        detalle={"campos_cambiados": "estado"},
    )

    fila = _fila_de_bandeja(s, solicitud)
    if fila is None:  # pragma: no cover - defensivo
        raise HTTPException(404, "No existe esa solicitud")
    return fila


def _avisar_de_la_decision(
    s: Session,
    actor: Actor,
    alumna: Alumna,
    aviso: Aviso,
    tarifa: Tarifa | None,
    cita: Cita | None,
    motivo: str = "",
) -> None:
    usuario = s.get(Usuario, alumna.usuario_id)
    coach = s.get(Coach, actor.coach_id)
    if usuario is None or coach is None:  # pragma: no cover - defensivo
        return

    cuando = "la que acuerden"
    if cita is not None:
        local = en_zona(cita.inicia_en, alumna.zona_horaria)
        cuando = f"{local:%d/%m/%Y} a las {local:%H:%M}"

    cola.encolar(
        s,
        aviso,
        coach_id=actor.coach_id,
        llave=f"solicitud:{alumna.ulid}:{aviso.value}",
        para=usuario.email,
        contexto={
            "nombre": alumna.nombre.split(" ")[0],
            "coach": coach.marca or coach.nombre,
            "plan": tarifa.nombre if tarifa is not None else "el que acuerden",
            "cita": cuando,
            "motivo": motivo,
            "dias": dom.GRACIA_TRAS_DESCARTAR.days,
        },
        destinatario_id=usuario.id,
    )
