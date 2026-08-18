"""Procesamiento de imágenes.

El recorte de cabeza y cuello ocurre antes de guardar nada: nunca persiste una imagen
identificable. Nitidez y luminancia solo prefiltran; la postura la juzga la coach.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

#: Cabeza y cuello, con margen: la guía de la cámara encuadra del cuello para abajo.
FRACCION_CABEZA = 0.18

#: Basta para distinguir textura cutánea, que es lo que la coach mira.
LADO_MAXIMO = 1600

#: Es la única imagen que alguien examina de cerca; aquí no se aprieta más.
CALIDAD_WEBP = 80

#: Máximo esfuerzo del codificador: 250 ms más por foto, un 5 % menos de peso, misma calidad.
ESFUERZO = 6

#: Umbrales de rechazo automático, medidos sobre fotos reales.
UMBRAL_NITIDEZ = Decimal("40")
UMBRAL_LUMINANCIA_MINIMA = Decimal("55")
UMBRAL_LUMINANCIA_MAXIMA = Decimal("215")

#: nginx corta antes, pero el servidor no confía en que lo haya hecho.
BYTES_MAXIMOS = 12 * 1024 * 1024


class ImagenInvalida(ValueError):
    """Entrada corrupta, no error de negocio."""


@dataclass(frozen=True, slots=True)
class Procesada:
    """`contenido` ya viene recortado: no existe versión con rostro."""

    contenido: bytes
    ancho: int
    alto: int
    bytes: int
    nitidez: Decimal
    luminancia: Decimal
    #: `aprobada` o `rechazada`; solo prefiltra.
    estado_auto: str
    motivo_rechazo: str | None
    tomada_en: datetime | None


def _nitidez(gris) -> Decimal:  # type: ignore[no-untyped-def]
    """Varianza del laplaciano: la medida clásica de enfoque."""
    import numpy as np

    # A mano, para no arrastrar OpenCV a un VPS sin Docker.
    a = gris.astype(np.float32)
    centro = a[1:-1, 1:-1]
    laplaciano = a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:] - 4 * centro
    return Decimal(str(round(float(laplaciano.var()), 3)))


def _luminancia(gris) -> Decimal:  # type: ignore[no-untyped-def]
    return Decimal(str(round(float(gris.mean()), 2)))


def _fecha_exif(imagen) -> datetime | None:  # type: ignore[no-untyped-def]
    """Solo la fecha. El resto del EXIF se descarta, empezando por la geolocalización."""
    try:
        exif = imagen.getexif()
        bruto = exif.get(306) or exif.get(36867)  # DateTime / DateTimeOriginal
        if not bruto:
            return None
        return datetime.strptime(str(bruto), "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def procesar(original: bytes) -> Procesada:
    """Recorta, reescala, convierte a WebP y mide calidad. El original se descarta."""
    import numpy as np
    from PIL import Image, ImageOps

    if not original:
        raise ImagenInvalida("archivo vacío")
    if len(original) > BYTES_MAXIMOS:
        raise ImagenInvalida(f"la imagen pesa más de {BYTES_MAXIMOS // 1024 // 1024} MB")

    try:
        abierta = Image.open(io.BytesIO(original))
        abierta.load()
    except Exception as causa:
        raise ImagenInvalida("no se pudo leer la imagen") from causa

    tomada_en = _fecha_exif(abierta)

    # Enderezar va antes de recortar: en una foto tomada de lado, el recorte se llevaría un
    # costado en lugar de la cabeza.
    imagen: Image.Image = ImageOps.exif_transpose(abierta) or abierta
    imagen = imagen.convert("RGB")

    ancho, alto = imagen.size
    if ancho < 200 or alto < 200:
        raise ImagenInvalida("la imagen es demasiado pequeña")

    imagen = imagen.crop((0, int(alto * FRACCION_CABEZA), ancho, alto))
    imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.Resampling.LANCZOS)

    gris = np.asarray(imagen.convert("L"))
    nitidez = _nitidez(gris)
    luminancia = _luminancia(gris)

    motivo: str | None = None
    if nitidez < UMBRAL_NITIDEZ:
        motivo = "La foto salió borrosa. Apoya el teléfono o pide que te la tomen."
    elif luminancia < UMBRAL_LUMINANCIA_MINIMA:
        motivo = "Falta luz. Ponte de frente a una ventana, sin la luz a tus espaldas."
    elif luminancia > UMBRAL_LUMINANCIA_MAXIMA:
        motivo = "Hay demasiada luz y se pierde el contorno. Aléjate un poco de la ventana."

    salida = io.BytesIO()
    # Sin copiar `exif`: el WebP nace sin metadatos.
    imagen.save(salida, format="WEBP", quality=CALIDAD_WEBP, method=ESFUERZO)
    contenido = salida.getvalue()

    return Procesada(
        contenido=contenido,
        ancho=imagen.width,
        alto=imagen.height,
        bytes=len(contenido),
        nitidez=nitidez,
        luminancia=luminancia,
        estado_auto="rechazada" if motivo else "aprobada",
        motivo_rechazo=motivo,
        tomada_en=tomada_en,
    )


def miniatura(contenido: bytes, lado: int = 320) -> bytes:
    """Versión chica para la galería. Ya viene recortada: nunca toca el original."""
    from PIL import Image

    imagen = Image.open(io.BytesIO(contenido))
    imagen.thumbnail((lado, lado), Image.Resampling.LANCZOS)
    salida = io.BytesIO()
    imagen.save(salida, format="WEBP", quality=75, method=ESFUERZO)
    return salida.getvalue()


#: Se ve a 24 px en la barra y a 96 en los ajustes.
LADO_LOGO = 256


def logo(original: bytes) -> bytes:
    """El logo de la marca, cuadrado. No pasa por `procesar`: aquí no se recorta nada."""
    from PIL import Image, ImageOps

    if not original:
        raise ImagenInvalida("archivo vacío")
    if len(original) > BYTES_MAXIMOS:
        raise ImagenInvalida("el logo pesa demasiado")

    try:
        imagen = Image.open(io.BytesIO(original))
        imagen.load()
    except Exception as causa:
        raise ImagenInvalida("no se pudo leer la imagen") from causa

    # `fit` recorta al centro; un logo estirado se ve peor que uno con los bordes cortados.
    cuadrado = ImageOps.fit(imagen.convert("RGB"), (LADO_LOGO, LADO_LOGO), Image.Resampling.LANCZOS)

    # Colores planos pesan 5× menos sin pérdida; una foto pesa 7× más. Se prueban los dos y
    # gana el más chico: a 256 px el doble encode no se nota.
    sin_perdida = io.BytesIO()
    cuadrado.save(sin_perdida, format="WEBP", lossless=True, method=ESFUERZO)
    con_perdida = io.BytesIO()
    cuadrado.save(con_perdida, format="WEBP", quality=88, method=ESFUERZO)
    return min(sin_perdida.getvalue(), con_perdida.getvalue(), key=len)


#: Más chica y más apretada que un chequeo: aquí solo se mira el plato, y vive 36 horas.
LADO_COMIDA = 1024
CALIDAD_COMIDA = 74


def comida(original: bytes) -> bytes:
    """Foto de un plato. Reencodar borra el EXIF, que trae dónde se tomó."""
    from PIL import Image, ImageOps

    if not original:
        raise ImagenInvalida("archivo vacío")
    if len(original) > BYTES_MAXIMOS:
        raise ImagenInvalida(f"la imagen pesa más de {BYTES_MAXIMOS // 1024 // 1024} MB")

    try:
        abierta = Image.open(io.BytesIO(original))
        abierta.load()
    except Exception as causa:
        raise ImagenInvalida("no se pudo leer la imagen") from causa

    # Enderezar antes de descartar los metadatos, que es de donde sale la orientación.
    imagen: Image.Image = ImageOps.exif_transpose(abierta) or abierta
    imagen = imagen.convert("RGB")
    imagen.thumbnail((LADO_COMIDA, LADO_COMIDA), Image.Resampling.LANCZOS)

    salida = io.BytesIO()
    imagen.save(salida, format="WEBP", quality=CALIDAD_COMIDA, method=ESFUERZO)
    return salida.getvalue()
