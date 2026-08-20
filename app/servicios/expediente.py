"""El expediente de una alumna, empaquetado para que se lo lleve.

Es la salida que la plataforma le promete cuando avisa de una purga o de una baja: hasta
ahora el aviso existía y la descarga no.

Se arma en memoria a propósito. Son unas pocas decenas de imágenes ya recortadas y un PDF de
texto; un expediente de años pesa menos que un video corto, y escribir a disco obligaría a
limpiar temporales que nadie recuerda limpiar.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Pieza:
    """Un archivo dentro del paquete. `ruta` puede llevar carpetas con barras."""

    ruta: str
    contenido: bytes


def empaquetar(piezas: Iterable[Pieza]) -> bytes:
    """Un ZIP con lo que se le pase, en el orden que llegue.

    Las rutas repetidas se descartan: un ZIP admite dos entradas con el mismo nombre pero al
    abrirlo solo se ve una, y es peor entregar un paquete que miente sobre lo que trae.
    """
    bolsa = io.BytesIO()
    vistas: set[str] = set()
    with zipfile.ZipFile(bolsa, "w", zipfile.ZIP_DEFLATED) as zip_:
        for pieza in piezas:
            if pieza.ruta in vistas:
                continue
            vistas.add(pieza.ruta)
            zip_.writestr(pieza.ruta, pieza.contenido)
    return bolsa.getvalue()


def carpeta_de_chequeo(numero: int, fecha: str) -> str:
    """`chequeo-03-2026-04-15`. El número va con cero delante para que ordene solo."""
    return f"chequeo-{numero:02d}-{fecha}"
