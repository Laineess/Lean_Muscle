"""Entrega de archivos guardados. Un solo sitio para las fotos y el logo.

**En producción no los sirve Python.** La aplicación comprueba el permiso, anota el acceso y
responde con `X-Accel-Redirect`; nginx entrega el archivo desde una `location internal;`.
Servir imágenes desde los trabajadores los satura con media docena de alumnas activas.

Fuera de producción no hay nginx, así que esa cabecera no la interpreta nadie: la respuesta
sale con 200 y **cuerpo vacío**, y el navegador pinta una imagen rota. Por eso en local se
envían los bytes. La comprobación de permisos es la misma en los dos casos; lo único que
cambia es quién mueve los bytes.
"""

from __future__ import annotations

from fastapi import HTTPException, Response

from app.config import ajustes
from app.servicios.almacenamiento import almacen

#: Dato sensible: privado y corto, para que no se quede en cachés intermedias.
CACHE = "private, max-age=300"


def servir(llave: str, tipo: str = "image/webp") -> Response:
    """Entrega el archivo. En producción delega en nginx; en local lo lee y lo manda."""
    if ajustes().es_produccion:
        return Response(
            status_code=200,
            headers={
                "X-Accel-Redirect": almacen().ruta_interna(llave),
                "Content-Type": tipo,
                "Cache-Control": CACHE,
            },
        )

    try:
        contenido = almacen().leer(llave)
    except FileNotFoundError as causa:
        # La fila existe y el archivo no: pasa al restaurar una base sin su volumen de datos.
        raise HTTPException(404, "El archivo ya no está en el disco") from causa

    return Response(content=contenido, media_type=tipo, headers={"Cache-Control": CACHE})
