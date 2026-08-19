"""Qué se avisa, a quién y cuándo, todo en un sitio: para ver de un vistazo cuántos mensajes
recibe una alumna y no llenarle la bandeja sin darse cuenta.

Un aviso ya enviado no se repite: el emisor guarda el sello de cada disparo y estas
funciones lo reciben. Módulo puro: decide, no envía.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

from app.compartido.fechas import a_utc


class Aviso(StrEnum):
    """Cada valor es una plantilla de correo y de notificación."""

    # --- Alta y acceso ---
    BIENVENIDA = "bienvenida"
    """Invitación de alta con clave temporal. Va por correo sí o sí: sin esto no puede entrar."""
    CLAVE_TEMPORAL = "clave_temporal"
    CONTRASENA_CAMBIADA = "contrasena_cambiada"
    """Aviso de seguridad. Si no fue ella, es la señal de que alguien entró a su cuenta."""
    CODIGO_DE_REGISTRO = "codigo_de_registro"
    """Los seis dígitos del registro abierto. **No se encola**: quien lo espera está mirando
    la pantalla, y la cola sale cada cinco minutos."""
    REGISTRO_SIN_TERMINAR = "registro_sin_terminar"
    """Dejó su registro a medias y se borra en dos días."""
    SOLICITUD_RECIBIDA = "solicitud_recibida"
    """Va **a la coach**: alguien terminó su registro y le toca decidir."""
    SOLICITUD_ACEPTADA = "solicitud_aceptada"
    SOLICITUD_DESCARTADA = "solicitud_descartada"

    # --- Chequeo ---
    RECORDATORIO_CHEQUEO = "recordatorio_chequeo"
    CHEQUEO_RECIBIDO = "chequeo_recibido"
    CHEQUEO_LISTO = "chequeo_listo"
    """Va **a la coach**: hay un chequeo esperando su validación."""
    CHEQUEO_VALIDADO = "chequeo_validado"
    CHEQUEO_RECHAZADO = "chequeo_rechazado"
    INACTIVIDAD = "inactividad"

    # --- Plan ---
    PLAN_PUBLICADO = "plan_publicado"

    # --- Citas ---
    CITA_AGENDADA = "cita_agendada"
    CITA_RECORDATORIO = "cita_recordatorio"
    CITA_CANCELADA = "cita_cancelada"
    CITA_REAGENDADA = "cita_reagendada"
    CONSULTA_RESERVADA = "consulta_reservada"
    """Va **a la coach**: la alumna tomó un hueco de su horario y ella no lo agendó."""

    # --- Dinero ---
    PAGO_PROXIMO = "pago_proximo"
    PAGO_RECIBIDO = "pago_recibido"
    """Acuse de que subió el comprobante. No es el ticket: todavía no se valida."""
    PAGO_VALIDADO = "pago_validado"
    """Lleva el ticket en PDF adjunto."""
    PAGO_RECHAZADO = "pago_rechazado"
    PAGO_VENCIDO = "pago_vencido"

    # --- De la coach ---
    MENSAJE_DE_COACH = "mensaje_de_coach"
    """Lo escribe ella: título y cuerpo. El único aviso cuyo texto no está en el código."""

    # --- Privacidad ---
    PURGA_PROXIMA = "purga_proxima"
    """Quince días antes de borrar sus fotos, con enlace de descarga."""
    BAJA_CONFIRMADA = "baja_confirmada"
    """Su coach la dio de baja. Lleva su expediente adjunto: lo que capturó es suyo."""


class Canal(StrEnum):
    PUSH = "push"
    CORREO = "correo"


#: Por qué canal sale cada aviso. El correo se reserva para lo que no puede perderse
#: —acceso, dinero, privacidad—; mandar por correo cada movimiento del método sería la forma
#: más rápida de que aprenda a ignorarnos.
CANALES: dict[Aviso, frozenset[Canal]] = {
    Aviso.BIENVENIDA: frozenset({Canal.CORREO}),
    Aviso.CLAVE_TEMPORAL: frozenset({Canal.CORREO}),
    Aviso.CONTRASENA_CAMBIADA: frozenset({Canal.CORREO}),
    # Los dos del registro van por correo y solo por correo: todavía no instaló nada donde
    # pudiera llegarle una notificación.
    Aviso.CODIGO_DE_REGISTRO: frozenset({Canal.CORREO}),
    Aviso.REGISTRO_SIN_TERMINAR: frozenset({Canal.CORREO}),
    # A la coach, dentro de la plataforma: es trabajo suyo, no algo que pueda perderse.
    Aviso.SOLICITUD_RECIBIDA: frozenset({Canal.PUSH}),
    Aviso.CHEQUEO_LISTO: frozenset({Canal.PUSH}),
    # A la alumna, y por correo: que la acepten o no decide si tiene servicio.
    Aviso.SOLICITUD_ACEPTADA: frozenset({Canal.PUSH, Canal.CORREO}),
    Aviso.SOLICITUD_DESCARTADA: frozenset({Canal.CORREO}),
    Aviso.RECORDATORIO_CHEQUEO: frozenset({Canal.PUSH}),
    Aviso.CHEQUEO_RECIBIDO: frozenset({Canal.PUSH}),
    Aviso.CHEQUEO_VALIDADO: frozenset({Canal.PUSH}),
    Aviso.CHEQUEO_RECHAZADO: frozenset({Canal.PUSH}),
    Aviso.INACTIVIDAD: frozenset({Canal.PUSH}),
    Aviso.PLAN_PUBLICADO: frozenset({Canal.PUSH}),
    Aviso.CITA_AGENDADA: frozenset({Canal.PUSH, Canal.CORREO}),
    Aviso.CITA_RECORDATORIO: frozenset({Canal.PUSH}),
    Aviso.CITA_CANCELADA: frozenset({Canal.PUSH, Canal.CORREO}),
    Aviso.CITA_REAGENDADA: frozenset({Canal.PUSH, Canal.CORREO}),
    # A la coach, y solo por push: es su agenda, no es dinero ni acceso.
    Aviso.CONSULTA_RESERVADA: frozenset({Canal.PUSH}),
    Aviso.PAGO_PROXIMO: frozenset({Canal.PUSH}),
    Aviso.PAGO_RECIBIDO: frozenset({Canal.PUSH}),
    Aviso.PAGO_VALIDADO: frozenset({Canal.PUSH, Canal.CORREO}),
    Aviso.PAGO_RECHAZADO: frozenset({Canal.PUSH, Canal.CORREO}),
    Aviso.PAGO_VENCIDO: frozenset({Canal.PUSH, Canal.CORREO}),
    # Una frase de ánimo por correo es correo basura. Push y la propia app, nada más.
    Aviso.MENSAJE_DE_COACH: frozenset({Canal.PUSH}),
    Aviso.PURGA_PROXIMA: frozenset({Canal.PUSH, Canal.CORREO}),
    # Por correo sí o sí: es lo único que le queda cuando su cuenta se cierre.
    Aviso.BAJA_CONFIRMADA: frozenset({Canal.CORREO}),
}

#: Avisos que llevan un PDF adjunto.
CON_ADJUNTO: frozenset[Aviso] = frozenset({Aviso.PAGO_VALIDADO, Aviso.BAJA_CONFIRMADA})

#: Anticipación de cada recordatorio.
ANTICIPACION_CITA = timedelta(days=1)
ANTICIPACION_PAGO = timedelta(days=3)
ANTICIPACION_PURGA = timedelta(days=15)
DIAS_INACTIVIDAD = 3


def canales_de(aviso: Aviso) -> frozenset[Canal]:
    return CANALES[aviso]


def lleva_adjunto(aviso: Aviso) -> bool:
    return aviso in CON_ADJUNTO


@dataclass(frozen=True, slots=True)
class Pendiente:
    """Un aviso listo para enviarse."""

    aviso: Aviso
    canales: frozenset[Canal]
    #: Para no repetirlo: el emisor guarda esta llave y no vuelve a disparar el mismo.
    llave: str


def _pendiente(aviso: Aviso, llave: str) -> Pendiente:
    return Pendiente(aviso=aviso, canales=canales_de(aviso), llave=llave)


def toca_recordar_cita(
    inicia_en: datetime, ahora: datetime, ya_enviado: bool, cita_id: str
) -> Pendiente | None:
    if ya_enviado:
        return None
    falta = a_utc(inicia_en) - a_utc(ahora)
    # La ventana tiene piso: recordar una cita que ya pasó no le sirve a nadie.
    if not (timedelta(0) <= falta <= ANTICIPACION_CITA):
        return None
    return _pendiente(Aviso.CITA_RECORDATORIO, f"cita:{cita_id}:recordatorio")


def toca_recordar_pago(
    termina_en: date, hoy: date, pagado: bool, ciclo_id: str
) -> Pendiente | None:
    """Solo se avisa a quien todavía no paga. Cobrarle a quien ya pagó es la forma más rápida
    de que deje de leer los correos."""
    if pagado:
        return None
    falta = termina_en - hoy
    if not (timedelta(0) <= falta <= ANTICIPACION_PAGO):
        return None
    return _pendiente(Aviso.PAGO_PROXIMO, f"ciclo:{ciclo_id}:proximo")


def toca_avisar_vencido(
    termina_en: date, hoy: date, pagado: bool, ciclo_id: str
) -> Pendiente | None:
    if pagado or hoy <= termina_en:
        return None
    return _pendiente(Aviso.PAGO_VENCIDO, f"ciclo:{ciclo_id}:vencido")


def toca_avisar_purga(
    tomada_en: date, hoy: date, retencion_meses: int, foto_id: str
) -> Pendiente | None:
    """Quince días antes de borrar la foto, con enlace de descarga. Aviso de Privacidad §8:
    lo que se lleva es suyo y sale del sistema."""
    dias_retencion = retencion_meses * 30
    borra_el = tomada_en + timedelta(days=dias_retencion)
    falta = borra_el - hoy
    if not (timedelta(0) <= falta <= ANTICIPACION_PURGA):
        return None
    return _pendiente(Aviso.PURGA_PROXIMA, f"foto:{foto_id}:purga")


def toca_avisar_inactividad(
    ultimo_acceso: date | None, hoy: date, ya_enviado: bool, alumna_id: str
) -> Pendiente | None:
    if ya_enviado:
        return None
    if ultimo_acceso is not None and (hoy - ultimo_acceso).days < DIAS_INACTIVIDAD:
        return None
    # La llave lleva la fecha: si vuelve a inactivarse el mes que entra, se avisa otra vez.
    return _pendiente(Aviso.INACTIVIDAD, f"alumna:{alumna_id}:inactividad:{hoy.isoformat()}")
