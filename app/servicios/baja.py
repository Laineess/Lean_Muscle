"""Baja de una alumna y borrado de su expediente quince días después.

Dos operaciones separadas a propósito. `dar_de_baja` la saca de la cartera hoy y le deja
acceso de lectura; `borrar_expediente` es lo que corre después, desde el trabajo de purga.

**Lo que se queda es lo que la ley obliga a guardar y el dinero.** La ficha de `alumna` no
se borra: se vacía. Sin ella no habría dónde colgar los consentimientos, la bitácora de
accesos ni los movimientos, que se conservan cinco años; y con ella vacía —sin nombre, sin
correo, sin fecha de nacimiento— ninguno de esos registros identifica ya a nadie. La cuenta
sí se borra entera, que es lo que libera su correo para que pueda volver a registrarse.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compartido.fechas import ahora_utc
from app.datos.modelos import (
    AccesoSensible,
    Alumna,
    AvisoEnviado,
    Chequeo,
    Ciclo,
    Cita,
    ClaveTemporal,
    CobroProgramado,
    Consentimiento,
    Foto,
    FotoDeComida,
    HistorialClinico,
    Medida,
    Mensaje,
    MovimientoFinanciero,
    Notificacion,
    Pago,
    ParametrosCiclo,
    Pesaje,
    Plan,
    RespuestaCuestionario,
    Sesion,
    SolicitudDeRegistro,
    SuscripcionPush,
    Usuario,
)
from app.dominio import baja as dom
from app.servicios import almacenamiento

#: Fecha con la que se sustituye la de nacimiento. No es un dato: es un relleno que respeta
#: el NOT NULL de la columna sin decir nada de nadie.
SIN_FECHA = date(1900, 1, 1)


def adeudo(s: Session, alumna_id: int, hoy: date) -> tuple[Decimal, int]:
    """Lo que debe vencido y en cuántos cobros. Se le enseña a la coach **antes** de la baja.

    Darle de baja no cobra nada: si la deja ir con dos mensualidades sin pagar, esa decisión
    tiene que tomarla mirándolas, no descubrirlas después.
    """
    pendientes = [
        c
        for c in s.scalars(
            select(CobroProgramado).where(
                CobroProgramado.alumna_id == alumna_id,
                CobroProgramado.estado.in_(("pendiente", "en_revision")),
            )
        )
        if c.fecha <= hoy
    ]
    return Decimal(sum((c.monto for c in pendientes), Decimal(0))), len(pendientes)


def dar_de_baja(s: Session, alumna: Alumna, confirmacion: str) -> datetime:
    """La saca de la cartera hoy. Devuelve el día en que se borrará su expediente."""
    dom.exigir_confirmacion(alumna.nombre, confirmacion)

    alumna.estado = dom.EstadoDeAlumna.BAJA.value
    alumna.baja_en = ahora_utc()

    # La cuenta sigue viva a propósito: son quince días para que baje lo suyo. Lo que se
    # corta es la escritura, y eso lo decide la guarda de la sesión, no el estado del
    # usuario.
    for cita in s.scalars(
        select(Cita).where(Cita.alumna_id == alumna.id, Cita.estado != "cancelada")
    ):
        if cita.inicia_en > ahora_utc():
            # Las consultas futuras se borran: es un hueco que otra alumna puede tomar hoy.
            s.delete(cita)

    s.flush()
    return dom.borra_el(alumna.baja_en)


#: Todo lo que cuelga de la alumna y se va con ella. El orden importa: lo que apunta a un
#: chequeo o a un ciclo tiene que morir antes que ellos.
POR_CHEQUEO = (Foto, Medida)
POR_CICLO = (Plan, ParametrosCiclo, Pago)
POR_ALUMNA = (
    Pesaje,
    Cita,
    ClaveTemporal,
    CobroProgramado,
    FotoDeComida,
    HistorialClinico,
    Mensaje,
    RespuestaCuestionario,
    SolicitudDeRegistro,
)
POR_USUARIO = (AvisoEnviado, Notificacion, Sesion, SuscripcionPush)

#: Lo que sobrevive colgado de la ficha vacía, con el motivo por el que la ley lo pide.
SE_CONSERVAN = {
    "consentimiento": "constancia de qué texto aceptó y cuándo; cinco años",
    "acceso_sensible": "bitácora de quién más vio su expediente; cinco años",
    "solicitud_arco": "constancia de que ejerció un derecho y cómo se resolvió",
    "movimiento_financiero": "es la contabilidad de la coach, y ya no lleva su nombre",
}


def borrar_expediente(s: Session, alumna: Alumna) -> None:
    """Borra todo lo suyo y deja la ficha vacía.

    Los archivos se borran antes que las filas: una fila que se va sin su imagen deja el
    archivo en el disco para siempre, y ese disco es el volumen cifrado del VPS.
    """
    usuario_id = alumna.usuario_id
    chequeos = list(s.scalars(select(Chequeo).where(Chequeo.alumna_id == alumna.id)))
    ciclos = list(s.scalars(select(Ciclo).where(Ciclo.alumna_id == alumna.id)))

    for foto in s.scalars(
        select(Foto).where(Foto.chequeo_id.in_([c.id for c in chequeos] or [0]))
    ):
        _borrar_archivo(foto.storage_key)
        if foto.storage_key:
            _borrar_archivo(foto.storage_key.replace(".webp", "-mini.webp"))

    for comida in s.scalars(select(FotoDeComida).where(FotoDeComida.alumna_id == alumna.id)):
        _borrar_archivo(comida.storage_key)

    for cobro in s.scalars(
        select(CobroProgramado).where(CobroProgramado.alumna_id == alumna.id)
    ):
        _borrar_archivo(cobro.comprobante_key)

    for pago in s.scalars(select(Pago).where(Pago.alumna_id == alumna.id)):
        _borrar_archivo(pago.comprobante_key)

    for tabla in POR_CHEQUEO:
        for fila in s.scalars(
            select(tabla).where(tabla.chequeo_id.in_([c.id for c in chequeos] or [0]))
        ):
            s.delete(fila)
    s.flush()

    for tabla_a in POR_ALUMNA:
        for fila in s.scalars(select(tabla_a).where(tabla_a.alumna_id == alumna.id)):
            s.delete(fila)
    s.flush()

    for chequeo in chequeos:
        s.delete(chequeo)
    s.flush()

    for tabla_c in POR_CICLO:
        for fila in s.scalars(
            select(tabla_c).where(tabla_c.ciclo_id.in_([c.id for c in ciclos] or [0]))
        ):
            s.delete(fila)
    s.flush()

    for ciclo in ciclos:
        s.delete(ciclo)
    s.flush()

    if usuario_id is not None:
        for tabla_u, columna in (
            (AvisoEnviado, AvisoEnviado.destinatario_id),
            (Notificacion, Notificacion.destinatario_id),
            (Sesion, Sesion.usuario_id),
            (SuscripcionPush, SuscripcionPush.usuario_id),
        ):
            for fila in s.scalars(select(tabla_u).where(columna == usuario_id)):
                s.delete(fila)

        # Sus propias lecturas se van con ella. La bitácora existe para responder «¿quién
        # más vio mi expediente?», y ella nunca fue «alguien más»; las de la coach se quedan
        # colgadas de la ficha vacía, que es lo que la ley pide conservar cinco años.
        for propia in s.scalars(
            select(AccesoSensible).where(AccesoSensible.actor_id == usuario_id)
        ):
            s.delete(propia)

    _vaciar(s, alumna)
    s.flush()

    # Al final: el correo queda libre en cuanto se va esta fila, y hasta entonces la ficha
    # todavía apuntaba a ella.
    if usuario_id is not None:
        usuario = s.get(Usuario, usuario_id)
        if usuario is not None:
            s.delete(usuario)
    s.flush()


def _vaciar(s: Session, alumna: Alumna) -> None:
    """Deja la ficha sin nada que identifique a nadie.

    Los movimientos de dinero siguen apuntando aquí, así que la coach los lee como «Alumna
    dada de baja» y su contabilidad sigue cuadrando sin conservar un solo dato personal.
    """
    alumna.nombre = dom.NOMBRE_ANONIMO
    alumna.usuario_id = None
    alumna.whatsapp = None
    alumna.fecha_nacimiento = SIN_FECHA
    alumna.sexo = None
    alumna.estatura_cm = None
    alumna.tarifa_id = None
    alumna.nivel_experiencia = None
    alumna.equipo = None
    alumna.estres = None
    alumna.ocupacion = None
    alumna.porcentaje_grasa_objetivo = None
    alumna.bascula_ref = None
    alumna.lugar_ref = None
    alumna.hora_ref = None
    alumna.cuestionario_completo = False
    alumna.estado = dom.EstadoDeAlumna.BORRADA.value
    _ = s


def vencidas(s: Session, ahora: datetime) -> list[Alumna]:
    """Las que ya cumplieron sus quince días. La consulta trae las bajas; el plazo lo decide
    el dominio."""
    return [
        a
        for a in s.scalars(
            select(Alumna).where(Alumna.estado == dom.EstadoDeAlumna.BAJA.value)
        )
        if dom.esta_vencida(a.baja_en, ahora)
    ]


def _borrar_archivo(llave: str | None) -> None:
    """Que el archivo ya no esté no es un error: el objetivo era justo ese."""
    if not llave:
        return
    try:
        almacenamiento.almacen().borrar(llave)
    except Exception:  # pragma: no cover - un archivo ilegible no debe frenar el borrado
        pass


def consentimientos_de(s: Session, alumna_id: int) -> list[Consentimiento]:
    """Se quedan colgados de la ficha vacía; esto existe para poder comprobarlo."""
    return list(
        s.scalars(select(Consentimiento).where(Consentimiento.alumna_id == alumna_id))
    )


def movimientos_de(s: Session, alumna_id: int) -> list[MovimientoFinanciero]:
    return list(
        s.scalars(
            select(MovimientoFinanciero).where(MovimientoFinanciero.alumna_id == alumna_id)
        )
    )
