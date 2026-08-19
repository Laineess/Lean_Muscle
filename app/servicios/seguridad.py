"""Contrasenas, tokens de sesion y claves temporales.

Nada de esto se inventa a mano: Argon2 para contrasenas, `secrets` para todo lo aleatorio
y SHA-256 para guardar el token de sesion (lo que viaja en la cookie nunca se persiste tal
cual, para que un volcado de la tabla no permita suplantar sesiones).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.config import ajustes

_hasher = PasswordHasher()

#: Vigencia de la clave temporal que emite la coach cuando una alumna pierde el acceso.
VIGENCIA_CLAVE_TEMPORAL = timedelta(hours=24)


def hash_contrasena(clara: str) -> str:
    return _hasher.hash(clara)


def verificar_contrasena(hash_guardado: str, clara: str) -> bool:
    try:
        return _hasher.verify(hash_guardado, clara)
    except VerifyMismatchError:
        return False


def requiere_rehash(hash_guardado: str) -> bool:
    """Los parametros de Argon2 suben con el tiempo; al iniciar sesion se re-cifra."""
    return _hasher.check_needs_rehash(hash_guardado)


def nuevo_token_de_sesion() -> tuple[str, str]:
    """Devuelve (token_para_la_cookie, hash_para_la_tabla)."""
    token = secrets.token_urlsafe(48)
    return token, hash_de_token(token)


def hash_de_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def comparar_hash(a: str, b: str) -> bool:
    """Comparacion en tiempo constante, para no filtrar informacion por el tiempo."""
    return hmac.compare_digest(a, b)


def contrasena_inicial() -> str:
    """Con la que nace toda cuenta. La dicta la coach, así que solo sirve para entrar una
    vez: la sesión no abre nada hasta que se cambie, y caduca a las 24 horas."""
    clave = ajustes().contrasena_inicial
    # Una variable de entorno vacía daría de alta cuentas sin contraseña.
    if len(clave) < 8:
        raise ErrorDeDominio(Codigo.CONTRASENA_DEBIL)
    return clave


def nueva_clave_temporal() -> str:
    """Formato legible para dictarla por WhatsApp: 8 caracteres sin ambiguos (0/O, 1/I/L)."""
    alfabeto = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    bruto = "".join(secrets.choice(alfabeto) for _ in range(8))
    return f"{bruto[:4]}-{bruto[4:]}"


def codigo_de_verificacion() -> str:
    """Seis digitos para confirmar que el correo es suyo. Se guarda su hash, no el codigo."""
    return f"{secrets.randbelow(1_000_000):06d}"


def exigir_mayor_de_edad(edad: int) -> None:
    """El MVP no admite menores: sus fotos corporales exigirian consentimiento de quien
    ejerce la patria potestad, y ese flujo no existe (Anexo Legal, seccion 9)."""
    if edad < 18:
        raise ErrorDeDominio(Codigo.MENOR_DE_EDAD, edad=edad)


def clave_temporal_vigente(vence_en: object) -> bool:
    from datetime import datetime

    if not isinstance(vence_en, datetime):
        return False
    return ahora_utc() < vence_en
