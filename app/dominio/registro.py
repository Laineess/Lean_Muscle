"""Registro abierto: en qué punto va una solicitud y qué le falta.

Una solicitud no es una alumna. Nace cuando alguien llega por la liga de la coach, y no
entra a la cartera hasta que ella la acepta: por eso no cuenta contra `limite_alumnas` y
por eso el chequeo no se abre todavía —guardar fotos corporales de una desconocida sería
recoger un dato sensible antes de que exista la relación que lo justifica—.

Módulo puro: decide, no consulta ni escribe.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import a_utc

#: Cuánto vale el código que llega al correo. Corto: es una prueba de que el buzón es suyo.
VIGENCIA_DEL_CODIGO = timedelta(minutes=15)

#: Intentos antes de invalidarlo. Seis dígitos son un millón de combinaciones; cinco tiros
#: dejan margen a un dedazo y no a probar a ciegas.
INTENTOS_DE_CODIGO = 5

#: Lo que hay que esperar para pedir otro código. Sin freno, la liga de la coach sería
#: una forma cómoda de mandarle correo a cualquiera.
ESPERA_ENTRE_CODIGOS = timedelta(seconds=60)

#: Lo que vive una solicitud sin terminar. Pasado eso se borra entera, con su cuenta.
VIDA_DE_SOLICITUD = timedelta(days=7)

#: Cuánto antes de borrarla se le recuerda que la dejó a medias.
AVISO_ANTES_DE_BORRAR = timedelta(days=2)


class Estado(StrEnum):
    SIN_VERIFICAR = "sin_verificar"
    """Se registró y todavía no prueba que el correo es suyo."""
    EN_CURSO = "en_curso"
    """Verificó el correo y está completando lo que le falta."""
    ESPERANDO = "esperando"
    """Terminó su parte. Le toca a la coach."""
    ACEPTADA = "aceptada"
    DESCARTADA = "descartada"


#: Estados que todavía puede abandonar, y por lo tanto se borran al vencer. `ESPERANDO` no
#: está: ella ya hizo lo suyo, y borrarle el expediente por una demora de la coach sería
#: castigarla por algo que no depende de ella.
ABANDONABLES = frozenset({Estado.SIN_VERIFICAR, Estado.EN_CURSO})

#: Ya decididas: no se tocan ni se borran solas.
CERRADAS = frozenset({Estado.ACEPTADA, Estado.DESCARTADA})


class Paso(StrEnum):
    """Dónde va en el recorrido. Lo usa la pantalla para saber qué enseñarle."""

    CORREO = "correo"
    CUESTIONARIO = "cuestionario"
    CITA = "cita"
    COMPROBANTE = "comprobante"
    ESPERA = "espera"
    LISTA = "lista"


def paso_actual(
    *,
    estado: Estado,
    cuestionario_completo: bool,
    tiene_cita: bool,
    comprobante_subido: bool,
) -> Paso:
    """Lo siguiente que le toca hacer.

    El orden importa y es el que se acordó: primero se presenta y contesta, después reserva
    y al final paga. Pedirle el comprobante antes de que sepa a qué hora la van a atender es
    cobrarle por algo que todavía no tiene forma.
    """
    if estado in CERRADAS:
        return Paso.LISTA
    if estado is Estado.SIN_VERIFICAR:
        return Paso.CORREO
    if not cuestionario_completo:
        return Paso.CUESTIONARIO
    if not tiene_cita:
        return Paso.CITA
    if not comprobante_subido:
        return Paso.COMPROBANTE
    return Paso.ESPERA


def termino_su_parte(paso: Paso) -> bool:
    return paso in {Paso.ESPERA, Paso.LISTA}


def codigo_utilizable(vence_en: datetime, intentos: int, ahora: datetime) -> bool:
    """Si el código todavía sirve. Caducado o quemado obliga a pedir otro."""
    return intentos < INTENTOS_DE_CODIGO and a_utc(ahora) < a_utc(vence_en)


def exigir_codigo_utilizable(vence_en: datetime, intentos: int, ahora: datetime) -> None:
    if not codigo_utilizable(vence_en, intentos, ahora):
        raise ErrorDeDominio(Codigo.CODIGO_VENCIDO)


def exigir_espera_entre_codigos(vence_en: datetime, ahora: datetime) -> None:
    """Un código recién mandado no se reemite."""
    emitido_en = a_utc(vence_en) - VIGENCIA_DEL_CODIGO
    if a_utc(ahora) - emitido_en < ESPERA_ENTRE_CODIGOS:
        raise ErrorDeDominio(Codigo.DEMASIADOS_REGISTROS)


def vence_el(creada_en: datetime) -> datetime:
    return a_utc(creada_en) + VIDA_DE_SOLICITUD


def esta_vencida(estado: Estado, creada_en: datetime, ahora: datetime) -> bool:
    """Si toca borrarla. Solo alcanza a las que quedaron a medias."""
    if estado not in ABANDONABLES:
        return False
    return a_utc(ahora) >= vence_el(creada_en)


def toca_recordar(
    estado: Estado, creada_en: datetime, ahora: datetime, ya_enviado: bool
) -> bool:
    """Dos días antes de borrarla, y una sola vez.

    Se avisa aunque falte poco: quien dejó a medias su registro no tiene por qué saber que
    lo que capturó se borra solo, y enterarse cuando ya no está es la peor forma.
    """
    if ya_enviado or estado not in ABANDONABLES:
        return False
    return a_utc(ahora) >= vence_el(creada_en) - AVISO_ANTES_DE_BORRAR


def exigir_abierto(abierto: bool, servicios_de_inscripcion: int) -> None:
    """Las dos condiciones para que la liga funcione.

    El precio no puede ser ambiguo: si la coach tiene dos servicios de inscripción, nadie
    sabe cuál se le cobra, y cobrarle el que no era es peor que no dejarla registrarse.
    """
    if not abierto:
        raise ErrorDeDominio(Codigo.REGISTRO_CERRADO)
    if servicios_de_inscripcion != 1:
        raise ErrorDeDominio(
            Codigo.SIN_PRECIO_DE_INSCRIPCION, servicios=servicios_de_inscripcion
        )
