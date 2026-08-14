"""Procesamiento de las fotografías de chequeo.

**El recorte sin rostro es el punto entero de este módulo.** La zona de cabeza y cuello se
elimina antes de guardar nada, y el archivo original se descarta. En ningún momento persiste
una imagen identificable, ni siquiera un segundo mientras se procesa.

Las métricas de calidad son las que la coach no tiene que juzgar a ojo: nitidez y luminancia.
La postura y la vestimenta las revisa ella, y este módulo no finge lo contrario.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

#: Fracción superior de la imagen que se recorta. La guía de la cámara encuadra del cuello
#: para abajo, así que el 18 % de arriba es cabeza y cuello con margen de error.
FRACCION_CABEZA = 0.18

#: Lado máximo tras reescalar. 1600 px basta para distinguir textura cutánea, que es el
#: criterio del documento de requerimientos, y pesa una fracción del original.
LADO_MAXIMO = 1600

CALIDAD_WEBP = 82

#: Umbrales de rechazo automático. Salen de medir fotos reales: por debajo, la coach no puede
#: evaluar composición corporal aunque quiera.
UMBRAL_NITIDEZ = Decimal("40")
UMBRAL_LUMINANCIA_MINIMA = Decimal("55")
UMBRAL_LUMINANCIA_MAXIMA = Decimal("215")

#: Tope de entrada. nginx corta antes, pero el servidor no confía en que lo haya hecho.
BYTES_MAXIMOS = 12 * 1024 * 1024


class ImagenInvalida(ValueError):
    """El archivo no es una imagen utilizable. No es error de negocio: es entrada corrupta."""


@dataclass(frozen=True, slots=True)
class Procesada:
    """El resultado. `contenido` ya viene recortado: no existe versión con rostro."""

    contenido: bytes
    ancho: int
    alto: int
    bytes: int
    nitidez: Decimal
    luminancia: Decimal
    #: `aprobada` o `rechazada`. La coach puede revisarla igual; esto solo prefiltra.
    estado_auto: str
    motivo_rechazo: str | None
    #: Del EXIF original, si lo traía. En el MVP solo advierte, no bloquea.
    tomada_en: datetime | None


def _nitidez(gris) -> Decimal:  # type: ignore[no-untyped-def]
    """Varianza del laplaciano.

    Es la medida clásica de enfoque: una imagen borrosa tiene pocos cambios bruscos entre
    píxeles vecinos, así que la varianza de su segunda derivada cae.
    """
    import numpy as np

    # Laplaciano 3×3 aplicado a mano; evita depender de OpenCV, que en un VPS sin Docker
    # arrastra media distribución.
    a = gris.astype(np.float32)
    centro = a[1:-1, 1:-1]
    laplaciano = a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:] - 4 * centro
    return Decimal(str(round(float(laplaciano.var()), 3)))


def _luminancia(gris) -> Decimal:  # type: ignore[no-untyped-def]
    return Decimal(str(round(float(gris.mean()), 2)))


def _fecha_exif(imagen) -> datetime | None:  # type: ignore[no-untyped-def]
    """Cuándo se tomó, si la cámara lo dejó anotado.

    Solo se lee la fecha. **El resto del EXIF se descarta**, geolocalización incluida: una
    foto corporal con las coordenadas de su casa es un dato mucho más peligroso que la foto.
    """
    try:
        exif = imagen.getexif()
        bruto = exif.get(306) or exif.get(36867)  # DateTime / DateTimeOriginal
        if not bruto:
            return None
        return datetime.strptime(str(bruto), "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def procesar(original: bytes) -> Procesada:
    """Recorta, reescala, convierte a WebP y mide calidad.

    El resultado sustituye al original, que el llamador debe descartar sin guardarlo.
    """
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

    # Endereza según la orientación del EXIF antes de recortar: si no, en una foto tomada de
    # lado el recorte se llevaría un costado en lugar de la cabeza.
    imagen: Image.Image = ImageOps.exif_transpose(abierta) or abierta
    imagen = imagen.convert("RGB")

    ancho, alto = imagen.size
    if ancho < 200 or alto < 200:
        raise ImagenInvalida("la imagen es demasiado pequeña")

    # --- Recorte sin rostro. Esto ocurre antes que nada más. ---
    desde_y = int(alto * FRACCION_CABEZA)
    imagen = imagen.crop((0, desde_y, ancho, alto))

    # --- Reescalado ---
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
    # `exif` no se copia: el WebP nace sin metadatos.
    imagen.save(salida, format="WEBP", quality=CALIDAD_WEBP, method=4)
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
    import io as _io

    from PIL import Image

    imagen = Image.open(_io.BytesIO(contenido))
    imagen.thumbnail((lado, lado), Image.Resampling.LANCZOS)
    salida = _io.BytesIO()
    imagen.save(salida, format="WEBP", quality=75, method=4)
    return salida.getvalue()
