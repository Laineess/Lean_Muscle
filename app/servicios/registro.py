"""Registro abierto: alta de una solicitud y su código de correo.

Una solicitud crea desde el primer paso su fila de `alumna`, con `estado='solicitud'`. Se
hace así y no con una tabla paralela porque de la alumna cuelgan el cuestionario, la cita y
el cobro de inscripción, y duplicar esas tres para el registro sería mantener dos veces lo
mismo. Lo que la deja fuera de la cartera y del límite es el estado, no el sitio donde vive.

Lo que se borra al abandonarla vive todo aquí: si un día se guarda algo más de una
solicitante, tiene que sumarse a `borrar` o quedará huérfano cuando la purga pase.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc, edad_en
from app.datos.modelos import (
    AccesoSensible,
    Alumna,
    AvisoEnviado,
    Cita,
    Coach,
    CobroProgramado,
    Consentimiento,
    HistorialClinico,
    Notificacion,
    RespuestaCuestionario,
    Servicio,
    Sesion,
    SolicitudArco,
    SolicitudDeRegistro,
    SuscripcionPush,
    Usuario,
)
from app.dominio import registro as dom
from app.dominio.avisos import Aviso
from app.servicios import almacenamiento, cuentas, legales
from app.servicios.correo import Correo, emisor
from app.servicios.plantillas_correo import redactar
from app.servicios.seguridad import (
    codigo_de_verificacion,
    comparar_hash,
    hash_contrasena,
    hash_de_token,
)

#: Los dos que se aceptan al registrarse. Los de salud y fotografía van en el cuestionario,
#: donde de verdad se entregan esos datos.
CONSENTIMIENTOS_DE_ALTA = ("terminos", "privacidad")


@dataclass(frozen=True, slots=True)
class SolicitudNueva:
    solicitud_ulid: str
    correo: str
    #: Se devuelve solo para poder enseñarlo en local, donde el correo no sale de verdad.
    codigo: str


def coach_por_slug(s: Session, slug: str) -> Coach | None:
    """Resuelve el inquilino desde la liga pública.

    Es la única lectura que precede al alcance, igual que en el acceso: todavía no se sabe
    de qué coach es quien escribe. Va contra `coach`, que no expone datos de ninguna alumna.
    """
    return s.scalars(
        select(Coach)
        .where(Coach.slug == slug.strip().lower(), Coach.estado == "activa")
        .execution_options(sin_alcance=True)
    ).first()


def servicios_de_inscripcion(s: Session) -> list[Servicio]:
    return list(
        s.scalars(
            select(Servicio).where(Servicio.motivo == "inscripcion", Servicio.activo.is_(True))
        ).all()
    )


def precio_de_inscripcion(s: Session) -> Servicio:
    """El único servicio de inscripción. Cero o dos es un error de configuración, no un caso
    de negocio: se corta aquí para no cobrarle a alguien un importe que nadie eligió."""
    encontrados = servicios_de_inscripcion(s)
    if len(encontrados) != 1:
        raise ErrorDeDominio(Codigo.SIN_PRECIO_DE_INSCRIPCION, servicios=len(encontrados))
    return encontrados[0]


def _emitir_codigo(solicitud: SolicitudDeRegistro) -> str:
    codigo = codigo_de_verificacion()
    solicitud.codigo_hash = hash_de_token(codigo)
    solicitud.codigo_vence_en = ahora_utc() + dom.VIGENCIA_DEL_CODIGO
    solicitud.intentos = 0
    return codigo


def crear(
    s: Session,
    *,
    coach: Coach,
    nombre: str,
    correo: str,
    contrasena: str,
    fecha_nacimiento: date,
    whatsapp: str | None,
    ip: str | None,
    user_agent: str,
) -> SolicitudNueva:
    """Da de alta la solicitud entera: cuenta, alumna, consentimientos y cobro."""
    dom.exigir_abierto(coach.registro_abierto, len(servicios_de_inscripcion(s)))
    inscripcion = precio_de_inscripcion(s)

    correo = cuentas.normalizar_correo(correo)
    if not nombre.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)
    cuentas.validar_contrasena(contrasena)

    from app.servicios.seguridad import exigir_mayor_de_edad

    exigir_mayor_de_edad(edad_en(fecha_nacimiento, ahora_utc().date()))

    # El correo es único en toda la plataforma, así que la búsqueda previa tiene que cruzar
    # inquilinos o el INSERT choca contra el UNIQUE en lugar de dar un mensaje decente.
    ya_existe = s.scalars(
        select(Usuario).where(Usuario.email == correo).execution_options(sin_alcance=True)
    ).first()
    if ya_existe is not None:
        raise ErrorDeDominio(Codigo.CORREO_YA_REGISTRADO, correo=correo)

    usuario = Usuario(
        coach_id=coach.id,
        rol="alumna",
        email=correo,
        # La escribe ella y nadie más la conoce, así que no hay nada que obligarla a cambiar.
        hash_contrasena=hash_contrasena(contrasena),
        estado="activo",
        debe_cambiar_contrasena=False,
    )
    s.add(usuario)
    s.flush()

    alumna = Alumna(
        coach_id=coach.id,
        usuario_id=usuario.id,
        nombre=nombre.strip()[:120],
        whatsapp=whatsapp,
        fecha_nacimiento=fecha_nacimiento,
        zona_horaria=coach.zona_horaria,
        cuestionario_completo=False,
        estado="solicitud",
    )
    s.add(alumna)
    s.flush()

    # Aquí ya entregó nombre, correo y fecha de nacimiento: el consentimiento va antes del
    # dato, no después.
    for tipo in CONSENTIMIENTOS_DE_ALTA:
        version, huella = legales.version_y_hash(tipo)
        s.add(
            Consentimiento(
                coach_id=coach.id,
                alumna_id=alumna.id,
                tipo=tipo,
                version_texto=version,
                texto_hash=huella,
                aceptado_en=ahora_utc(),
                ip=ip,
                user_agent=user_agent[:255],
            )
        )

    # El cobro nace con la solicitud para que tenga contra qué subir su comprobante. El
    # precio se copia: subirlo después no reescribe lo que se le dijo que costaba.
    s.add(
        CobroProgramado(
            coach_id=coach.id,
            alumna_id=alumna.id,
            fecha=ahora_utc().date(),
            motivo="inscripcion",
            concepto=inscripcion.nombre,
            monto=Decimal(inscripcion.precio),
            estado="pendiente",
        )
    )

    solicitud = SolicitudDeRegistro(
        coach_id=coach.id,
        alumna_id=alumna.id,
        estado=dom.Estado.SIN_VERIFICAR.value,
        codigo_hash="",
        codigo_vence_en=ahora_utc(),
        ip=ip,
    )
    codigo = _emitir_codigo(solicitud)
    s.add(solicitud)
    s.flush()

    return SolicitudNueva(solicitud_ulid=solicitud.ulid, correo=correo, codigo=codigo)


def reemitir_codigo(s: Session, solicitud: SolicitudDeRegistro) -> str:
    if solicitud.estado != dom.Estado.SIN_VERIFICAR.value:
        raise ErrorDeDominio(Codigo.SOLICITUD_YA_DECIDIDA)
    codigo = _emitir_codigo(solicitud)
    s.flush()
    return codigo


def verificar(s: Session, solicitud: SolicitudDeRegistro, codigo: str) -> None:
    """Confirma que el correo es suyo. Un intento fallido cuenta y se guarda."""
    if solicitud.estado != dom.Estado.SIN_VERIFICAR.value:
        raise ErrorDeDominio(Codigo.SOLICITUD_YA_DECIDIDA)

    dom.exigir_codigo_utilizable(solicitud.codigo_vence_en, solicitud.intentos, ahora_utc())

    if not comparar_hash(solicitud.codigo_hash, hash_de_token(codigo.strip())):
        solicitud.intentos += 1
        s.flush()
        raise ErrorDeDominio(Codigo.CODIGO_INCORRECTO)

    solicitud.estado = dom.Estado.EN_CURSO.value
    s.flush()


def mandar_codigo(marca: str, correo: str, codigo: str) -> None:
    """Manda el código en el momento, sin pasar por la cola.

    La cola sale cada cinco minutos y quien espera un código de seis dígitos está mirando la
    pantalla. Si el correo falla, la petición entera se deshace y no queda una solicitud
    que nadie puede verificar.
    """
    asunto, texto, html = redactar(
        Aviso.CODIGO_DE_REGISTRO,
        {
            "coach": marca,
            "codigo": codigo,
            "minutos": int(dom.VIGENCIA_DEL_CODIGO.total_seconds() // 60),
        },
    )
    emisor().enviar(Correo(para=correo, asunto=asunto, cuerpo_texto=texto, cuerpo_html=html))


def solicitud_de_alumna(s: Session, alumna_id: int) -> SolicitudDeRegistro | None:
    return s.scalars(
        select(SolicitudDeRegistro).where(SolicitudDeRegistro.alumna_id == alumna_id)
    ).first()


def marcar_si_termino(s: Session, solicitud: SolicitudDeRegistro, paso: dom.Paso) -> None:
    """Pasa a «esperando» en cuanto termina su parte: es lo que la mueve a la bandeja."""
    if paso is dom.Paso.ESPERA and solicitud.estado == dom.Estado.EN_CURSO.value:
        solicitud.estado = dom.Estado.ESPERANDO.value
        s.flush()


#: Todo lo que puede colgar de una solicitante y se va con ella. La lista está completa a
#: propósito: `prueba_registro_borrado` compara contra las llaves foráneas de la base y
#: falla si aparece una tabla nueva que nadie contempló aquí.
POR_ALUMNA = (
    AccesoSensible,
    Cita,
    CobroProgramado,
    Consentimiento,
    HistorialClinico,
    RespuestaCuestionario,
    SolicitudArco,
)

POR_USUARIO = (AvisoEnviado, Notificacion, Sesion, SuscripcionPush)


def borrar(s: Session, solicitud: SolicitudDeRegistro) -> None:
    """Borra la solicitud y todo lo que la solicitante alcanzó a dejar, cuenta incluida.

    Se hace a mano y no con `ON DELETE CASCADE` por dos razones: el comprobante no está en
    la base —es un archivo en disco, y una fila borrada sin su archivo deja la imagen ahí
    para siempre— y el orden importa, porque nadie declaró estas relaciones en el ORM y
    SQLAlchemy borra en el que se le ocurra.
    """
    alumna_id = solicitud.alumna_id
    alumna = s.get(Alumna, alumna_id)
    usuario_id = alumna.usuario_id if alumna is not None else None

    for cobro in s.scalars(
        select(CobroProgramado).where(CobroProgramado.alumna_id == alumna_id)
    ):
        if cobro.comprobante_key:
            almacenamiento.almacen().borrar(cobro.comprobante_key)

    for tabla in POR_ALUMNA:
        for fila in s.scalars(select(tabla).where(tabla.alumna_id == alumna_id)):
            s.delete(fila)

    if usuario_id is not None:
        for tabla_u, columna in (
            (AvisoEnviado, AvisoEnviado.destinatario_id),
            (Notificacion, Notificacion.destinatario_id),
            (Sesion, Sesion.usuario_id),
            (SuscripcionPush, SuscripcionPush.usuario_id),
        ):
            for fila in s.scalars(select(tabla_u).where(columna == usuario_id)):
                s.delete(fila)

    # Cada flush va aparte y en este orden: la solicitud apunta a la alumna y la alumna al
    # usuario, así que se borran de la punta hacia la raíz.
    s.delete(solicitud)
    s.flush()

    if alumna is not None:
        s.delete(alumna)
    s.flush()

    if usuario_id is not None:
        usuario = s.get(Usuario, usuario_id)
        if usuario is not None:
            s.delete(usuario)
    s.flush()


def abandonadas(s: Session, ahora: datetime) -> list[SolicitudDeRegistro]:
    """Las que ya vencieron. La consulta trae las abandonables y el dominio decide."""
    candidatas = s.scalars(
        select(SolicitudDeRegistro).where(
            SolicitudDeRegistro.estado.in_([e.value for e in dom.ABANDONABLES])
        )
    )
    return [
        x for x in candidatas if dom.esta_vencida(dom.Estado(x.estado), x.creado_en, ahora)
    ]
