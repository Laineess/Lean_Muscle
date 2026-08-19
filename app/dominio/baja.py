"""Baja de una alumna: qué pasa el día que se da, y qué pasa quince días después.

La baja no es un borrado inmediato ni un borrado que nunca llega. Son dos momentos:

- **Hoy** sale de la cartera y se le corta el servicio. Deja de ser alumna de su coach.
- **A los quince días** se borra todo lo suyo: fotos, medidas, historial, mensajes y la
  cuenta con su correo. En medio conserva acceso de solo lectura para bajar lo que quiera
  llevarse, porque es suyo y la plataforma no es la dueña.

Lo único que sobrevive es el dinero, anonimizado, y las constancias que la ley obliga a
guardar cinco años. Un movimiento sin nombre sigue cuadrando la contabilidad de la coach y
ya no identifica a nadie.

Módulo puro: decide, no consulta ni escribe.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import a_utc

#: Lo que conserva el acceso después de la baja. Quince días es lo que promete el aviso de
#: privacidad y lo que da tiempo a descargar un expediente sin prisa.
GRACIA_DE_LECTURA = timedelta(days=15)

#: Con lo que se queda la ficha una vez borrada. No es un nombre: es lo que la coach lee en
#: sus movimientos de hace dos años, y lo que hace que ya no identifiquen a nadie.
NOMBRE_ANONIMO = "Alumna dada de baja"


class EstadoDeAlumna(StrEnum):
    ACTIVA = "activa"
    PAUSA = "pausa"
    #: Se dio de baja: fuera de la cartera, con acceso de solo lectura mientras dure.
    BAJA = "baja"
    #: Pasaron los quince días y ya no queda nada suyo. La ficha vacía sostiene las
    #: constancias legales y los movimientos de dinero.
    BORRADA = "borrada"
    SOLICITUD = "solicitud"
    DESCARTADA = "descartada"


#: Las que la coach ve como suyas. Todo lo demás vive en otra pantalla o ya no existe.
EN_CARTERA = frozenset({EstadoDeAlumna.ACTIVA, EstadoDeAlumna.PAUSA})


def borra_el(baja_en: datetime) -> datetime:
    return a_utc(baja_en) + GRACIA_DE_LECTURA


def esta_vencida(baja_en: datetime | None, ahora: datetime) -> bool:
    """Si ya toca borrarla del todo."""
    return baja_en is not None and a_utc(ahora) >= borra_el(baja_en)


def puede_leer_lo_suyo(estado: str, baja_en: datetime | None, ahora: datetime) -> bool:
    """Si todavía puede entrar a descargar su expediente.

    Solo durante la gracia. Pasada, la cuenta se cierra aunque el trabajo de purga no haya
    corrido: el plazo lo fija la fecha de la baja, no la puntualidad del servidor.
    """
    if estado != EstadoDeAlumna.BAJA.value:
        return False
    return not esta_vencida(baja_en, ahora)


def exigir_confirmacion(nombre: str, escrito: str) -> None:
    """La baja no tiene deshacer, así que se teclea el nombre.

    Se comparan sin acentos ni mayúsculas: el objetivo es que se detenga a leer a quién está
    dando de baja, no ganarle un pulso a la ortografía.
    """
    if _plano(escrito) != _plano(nombre):
        raise ErrorDeDominio(Codigo.CONFIRMACION_NO_COINCIDE)


def _plano(texto: str) -> str:
    import unicodedata

    sin_tildes = unicodedata.normalize("NFKD", texto.strip().casefold())
    return " ".join("".join(c for c in sin_tildes if not unicodedata.combining(c)).split())
