"""Bitácora: quién vio qué y quién cambió qué.

Son dos registros distintos y conviene no confundirlos:

- **`acceso_sensible`** anota *lecturas*: cada vez que alguien abre una fotografía o un
  historial clínico. Lo exige el Anexo Legal §6, y es lo que permite responder «¿quién vio
  mi expediente?» cuando una alumna lo pregunta.
- **`bitacora`** anota *escrituras* sobre datos sensibles, y es de solo inserción. Retención
  de cinco años. Al ejercerse una cancelación, los datos personales se borran pero el
  movimiento sobrevive con identificador anonimizado.

**Registrar no es opcional ni queda a criterio de quien programe el endpoint**: es parte de
la definición de «terminado». `pruebas/aislamiento/prueba_bitacora.py` lo verifica leyendo
el árbol sintáctico, porque una convención que solo vive en un comentario se olvida.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from app.datos.modelos import AccesoSensible, Bitacora


class Recurso(StrEnum):
    """Qué se leyó. Basta para reconstruir el acceso sin duplicar el dato en la bitácora."""

    FOTO = "foto"
    FOTOS_DE_CHEQUEO = "fotos_de_chequeo"
    HISTORIAL_CLINICO = "historial_clinico"
    PDF_NUTRICION = "pdf_nutricion"
    PDF_RUTINA = "pdf_rutina"
    EXPEDIENTE = "expediente"


class Accion(StrEnum):
    """Qué se cambió. En pasado, porque se registra después del hecho."""

    ALUMNA_DADA_DE_ALTA = "alumna_dada_de_alta"
    ALUMNA_EDITADA = "alumna_editada"
    ALUMNA_DADA_DE_BAJA = "alumna_dada_de_baja"
    CLAVE_TEMPORAL_EMITIDA = "clave_temporal_emitida"
    CONTRASENA_CAMBIADA = "contrasena_cambiada"
    GRASA_ESTIMADA = "grasa_estimada"
    CHEQUEO_ENVIADO = "chequeo_enviado"
    CHEQUEO_VALIDADO = "chequeo_validado"
    CHEQUEO_RECHAZADO = "chequeo_rechazado"
    PLAN_GUARDADO = "plan_guardado"
    PLAN_PUBLICADO = "plan_publicado"
    HISTORIAL_ACTUALIZADO = "historial_actualizado"
    FOTO_SUBIDA = "foto_subida"
    FOTO_ELIMINADA = "foto_eliminada"
    COMPROBANTE_SUBIDO = "comprobante_subido"
    CONSENTIMIENTO_REVOCADO = "consentimiento_revocado"
    ANUNCIO_ENVIADO = "anuncio_enviado"
    ARCO_RECIBIDA = "arco_recibida"
    ARCO_RESPONDIDA = "arco_respondida"
    ARCO_RESUELTA = "arco_resuelta"
    CITA_RESERVADA = "cita_reservada"
    SOLICITUD_ACEPTADA = "solicitud_aceptada"
    SOLICITUD_DESCARTADA = "solicitud_descartada"


def registrar_acceso(
    s: Session,
    *,
    coach_id: int,
    actor_id: int,
    alumna_id: int,
    recurso: Recurso,
) -> None:
    """Deja constancia de una lectura de datos sensibles.

    Se llama **antes** de devolver el dato, no después: si la respuesta falla a medio camino
    el registro ya existe, y es preferible una lectura anotada de más que una sin anotar.
    """
    s.add(
        AccesoSensible(
            coach_id=coach_id,
            actor_id=actor_id,
            alumna_id=alumna_id,
            recurso=recurso.value,
        )
    )


def registrar(
    s: Session,
    *,
    coach_id: int,
    actor_id: int | None,
    actor_tipo: str,
    accion: Accion,
    entidad: str,
    entidad_id: int | None = None,
    detalle: dict[str, Any] | None = None,
) -> None:
    """Deja constancia de una escritura sobre datos sensibles.

    `detalle` guarda **qué cambió, no el dato en sí**. Copiar aquí el peso o el historial
    clínico duplicaría el dato sensible en una tabla que se conserva cinco años y que
    sobrevive a la cancelación: sería exactamente lo contrario de minimizar datos.
    """
    s.add(
        Bitacora(
            coach_id=coach_id,
            actor_tipo=actor_tipo,
            actor_id=actor_id,
            accion=accion.value,
            entidad=entidad,
            entidad_id=entidad_id,
            detalle=detalle,
        )
    )


def campos_cambiados(antes: dict[str, Any], despues: dict[str, Any]) -> list[str]:
    """Nombres de los campos que cambiaron. Es lo que va en `detalle`.

    Los nombres bastan para auditar: dicen qué se tocó sin arrastrar el valor a un registro
    de larga retención.
    """
    return sorted(k for k in despues if antes.get(k) != despues[k])
