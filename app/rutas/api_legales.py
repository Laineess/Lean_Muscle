"""Aviso de Privacidad y Términos y Condiciones.

**Sin sesión a propósito.** Quien todavía no ha entrado tiene que poder leer el aviso de
privacidad: la LFPDPPP exige que sea accesible antes de entregar ningún dato, y un documento
que solo se ve tras iniciar sesión no cumple eso.

El texto sale de `app/legales/`, el mismo archivo que se revisa y se versiona. Duplicarlo en
la base garantizaría que un día dejaran de coincidir.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.rutas.esquemas import DocumentoLegal
from app.rutas.sesion import RutaQueConfirma
from app.servicios import legales

ruteador = APIRouter(prefix="/api/legales", tags=["legales"], route_class=RutaQueConfirma)


@ruteador.get("/{clave}", response_model=DocumentoLegal)
def documento(clave: str, coach: str | None = None) -> DocumentoLegal:
    """El documento en Markdown, con los marcadores que aún faltan.

    `coach` rellena el nombre comercial. Va por parámetro y no desde la sesión porque esta
    ruta se lee sin haber entrado; si no viene, el hueco queda a la vista.
    """
    try:
        doc = legales.leer(clave, coach=coach, titular="MyFittPlan")
    except KeyError as causa:
        raise HTTPException(404, "No existe ese documento") from causa
    except FileNotFoundError as causa:  # pragma: no cover - despliegue incompleto
        raise HTTPException(500, "El documento no está en el servidor") from causa

    return DocumentoLegal(
        clave=doc.clave,
        titulo=doc.titulo,
        version=doc.version,
        actualizado=doc.actualizado,
        contenido=doc.contenido,
        marcadores=list(doc.marcadores),
    )
