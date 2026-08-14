"""Almacenamiento de archivos sensibles.

Detrás de una interfaz para poder mudar a S3 después sin tocar el dominio.

**La llave lleva el inquilino en el prefijo** (`coach/{id}/alumna/{id}/…`). Es la capa 4 del
aislamiento: antes de servir un archivo, el servidor comprueba que el prefijo coincide con
el `coach_id` de la sesión. Sin eso, adivinar una ruta bastaría para leer la foto de otra.

Los archivos viven **fuera de la raíz web**, en un volumen cifrado, y se entregan con
`X-Accel-Redirect`: nginx los manda con su eficiencia y Python nunca los carga en memoria.
Servir fotos desde la aplicación satura los trabajadores con media docena de alumnas.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from app.config import ajustes

#: Solo lo que compone una llave legítima. Cualquier otra cosa —`..`, barras invertidas,
#: caracteres de control— se rechaza antes de tocar el disco.
LLAVE_VALIDA = re.compile(r"^[a-zA-Z0-9/_.-]+$")


class LlaveInvalida(ValueError):
    """La llave no tiene la forma esperada. Casi siempre es un intento de salir del directorio."""


def llave_de_foto(coach_id: int, alumna_id: int, chequeo_id: int, angulo: str) -> str:
    return f"coach/{coach_id}/alumna/{alumna_id}/chequeo/{chequeo_id}/{angulo}.webp"


def llave_de_miniatura(coach_id: int, alumna_id: int, chequeo_id: int, angulo: str) -> str:
    return f"coach/{coach_id}/alumna/{alumna_id}/chequeo/{chequeo_id}/{angulo}-mini.webp"


def llave_de_logo(coach_id: int) -> str:
    """El logo de la marca. Nombre fijo: cambiarlo reemplaza el anterior."""
    return f"coach/{coach_id}/marca/logo.webp"


def llave_de_comprobante(coach_id: int, alumna_id: int, pago_id: int, extension: str) -> str:
    return f"coach/{coach_id}/alumna/{alumna_id}/pago/{pago_id}/comprobante.{extension}"


def pertenece_a(llave: str, coach_id: int) -> bool:
    """Si la llave es de este inquilino. Se comprueba **antes** de servir cualquier archivo."""
    return llave.startswith(f"coach/{coach_id}/")


def validar(llave: str) -> str:
    if not llave or not LLAVE_VALIDA.match(llave) or ".." in llave or llave.startswith("/"):
        raise LlaveInvalida(f"llave inválida: {llave!r}")
    return llave


class Almacen(Protocol):
    def guardar(self, llave: str, contenido: bytes) -> None: ...
    def leer(self, llave: str) -> bytes: ...
    def borrar(self, llave: str) -> None: ...
    def existe(self, llave: str) -> bool: ...
    def ruta_interna(self, llave: str) -> str: ...


class AlmacenEnDisco:
    """Disco del VPS. Sin Docker no vale la pena montar MinIO para esto."""

    def __init__(self, raiz: Path | None = None) -> None:
        self.raiz = raiz or ajustes().ruta_datos

    def _ruta(self, llave: str) -> Path:
        validar(llave)
        destino = (self.raiz / llave).resolve()
        # Segunda barrera, después de `validar`: aunque la expresión regular dejara pasar
        # algo, el archivo tiene que quedar dentro de la raíz.
        if not destino.is_relative_to(self.raiz.resolve()):
            raise LlaveInvalida(f"la llave sale del directorio: {llave!r}")
        return destino

    def guardar(self, llave: str, contenido: bytes) -> None:
        destino = self._ruta(llave)
        destino.parent.mkdir(parents=True, exist_ok=True)
        # Escritura atómica: si el proceso muere a media escritura, no queda un archivo
        # truncado que parezca válido.
        temporal = destino.with_suffix(destino.suffix + ".parcial")
        temporal.write_bytes(contenido)
        temporal.replace(destino)

    def leer(self, llave: str) -> bytes:
        return self._ruta(llave).read_bytes()

    def borrar(self, llave: str) -> None:
        destino = self._ruta(llave)
        destino.unlink(missing_ok=True)

    def existe(self, llave: str) -> bool:
        return self._ruta(llave).is_file()

    def ruta_interna(self, llave: str) -> str:
        """Ruta que entiende nginx para `X-Accel-Redirect`.

        Apunta a una `location internal;`, así que un navegador no puede pedirla
        directamente: solo la sirve nginx cuando la aplicación lo autoriza.
        """
        validar(llave)
        return f"{ajustes().nginx_prefijo_interno}/{llave}"


class AlmacenEnMemoria:
    """Para pruebas. No toca el disco."""

    def __init__(self) -> None:
        self.archivos: dict[str, bytes] = {}

    def guardar(self, llave: str, contenido: bytes) -> None:
        self.archivos[validar(llave)] = contenido

    def leer(self, llave: str) -> bytes:
        return self.archivos[validar(llave)]

    def borrar(self, llave: str) -> None:
        self.archivos.pop(validar(llave), None)

    def existe(self, llave: str) -> bool:
        return validar(llave) in self.archivos

    def ruta_interna(self, llave: str) -> str:
        return f"/memoria/{validar(llave)}"


_almacen: Almacen | None = None


def almacen() -> Almacen:
    global _almacen
    if _almacen is None:
        _almacen = AlmacenEnDisco()
    return _almacen


def usar_almacen(nuevo: Almacen) -> None:
    global _almacen
    _almacen = nuevo
