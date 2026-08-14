"""Entrega de los documentos legales que lee la alumna.

Se sirven desde `docs/` en lugar de duplicarlos en la base: el texto que firma una persona y
el que está en el repositorio tienen que ser el mismo archivo, o tarde o temprano dejan de
serlo.

**Los marcadores sin rellenar se devuelven, no se esconden.** Los documentos traen huecos
—`[RFC_PENDIENTE]`, el domicilio fiscal— y una advertencia de que son plantilla de trabajo.
Un aviso de privacidad con huecos no cumple la LFPDPPP, así que la pantalla tiene que poder
decirlo en lugar de aparentar que está terminado.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2] / "docs"

#: Qué documento es cada cual. La clave es lo que viaja en la URL.
DOCUMENTOS: dict[str, tuple[str, str]] = {
    "privacidad": ("Aviso de Privacidad", "Aviso_de_Privacidad_Alumnos_MyProgressPlan_v2.md"),
    "terminos": ("Términos y Condiciones", "Terminos_y_Condiciones_Alumnos_MyProgressPlan_v2.md"),
}

#: Un hueco por rellenar. En mayúsculas para no confundirlo con un enlace de Markdown.
MARCADOR = re.compile(r"\[([A-Z_]{4,})\]")

VERSION = re.compile(r"Versión\s+([\d.]+)\s+—\s+Última actualización:\s+(.+?)\*?\*?$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class Documento:
    clave: str
    titulo: str
    version: str
    actualizado: str
    contenido: str
    #: Huecos que siguen sin rellenar. Vacío significa que el documento está completo.
    marcadores: tuple[str, ...]

    @property
    def listo_para_publicar(self) -> bool:
        return not self.marcadores


@lru_cache(maxsize=8)
def _crudo(archivo: str) -> str:
    ruta = RAIZ / archivo
    if not ruta.is_file():
        raise FileNotFoundError(f"falta el documento {archivo}")
    return ruta.read_text(encoding="utf-8")


def leer(clave: str, *, coach: str | None = None, titular: str | None = None) -> Documento:
    """Devuelve el documento con lo que sí se puede rellenar ya sustituido.

    El nombre comercial de la coach lo sabe el sistema, así que se pone: dejar
    `[NOMBRE_COMERCIAL_COACH]` a la vista de la alumna sería absurdo. Lo que no sabe —RFC,
    domicilio fiscal, jurisdicción— se queda visible para que se note que falta.
    """
    if clave not in DOCUMENTOS:
        raise KeyError(clave)

    titulo, archivo = DOCUMENTOS[clave]
    texto = _crudo(archivo)

    if coach:
        texto = texto.replace("[NOMBRE_COMERCIAL_COACH]", coach)
        texto = texto.replace("[NOMBRE_COMPLETO_COACH]", coach)
    if titular:
        texto = texto.replace("[NOMBRE_COMPLETO_TITULAR]", titular)

    version, actualizado = "—", "—"
    encontrada = VERSION.search(texto)
    if encontrada:
        version, actualizado = encontrada.group(1), encontrada.group(2).strip().rstrip("*")

    return Documento(
        clave=clave,
        titulo=titulo,
        version=version,
        actualizado=actualizado,
        contenido=texto,
        marcadores=tuple(sorted(set(MARCADOR.findall(texto)))),
    )


#: De qué documento sale cada consentimiento. `datos_salud` y `protocolo_foto` no tienen
#: archivo propio: son secciones del aviso de privacidad, y es su texto el que se acepta.
DOCUMENTO_DE_CONSENTIMIENTO = {
    "terminos": "terminos",
    "privacidad": "privacidad",
    "datos_salud": "privacidad",
    "protocolo_foto": "privacidad",
}


def version_y_hash(consentimiento: str) -> tuple[str, str]:
    """Versión y huella del texto exacto que se aceptó.

    Se calcula sobre el documento sin sustituir el nombre de la coach: si no, dos alumnas de
    coaches distintas tendrían huellas distintas del mismo texto legal.
    """
    clave = DOCUMENTO_DE_CONSENTIMIENTO.get(consentimiento)
    if clave is None:
        raise KeyError(consentimiento)
    documento = leer(clave)
    huella = hashlib.sha256(documento.contenido.encode("utf-8")).hexdigest()
    return documento.version[:20], huella
