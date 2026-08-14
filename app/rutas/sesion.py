"""Sesion de la peticion y dependencias de rol.

Regla que no se negocia: **el `coach_id` sale siempre de la sesion, nunca del cliente**.
Un `coach_id` que venga en el cuerpo, en la query o en una cabecera se ignora, incluso en
endpoints internos.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo
from app.compartido.fechas import ahora_utc
from app.datos.alcance import motor, sesion_con_alcance
from app.datos.modelos import Sesion as FilaSesion
from app.datos.modelos import Usuario
from app.rutas.traduccion import respuesta_para
from app.servicios.seguridad import hash_de_token

NOMBRE_COOKIE = "lm_sesion"


@dataclass(frozen=True, slots=True)
class Actor:
    usuario_id: int
    coach_id: int
    rol: str

    @property
    def es_coach(self) -> bool:
        return self.rol == "coach"

    @property
    def es_alumna(self) -> bool:
        return self.rol == "alumna"

    @property
    def es_admin(self) -> bool:
        """Superadmin de la plataforma.

        Su usuario cuelga de un inquilino igual que cualquier otro —el de la propia
        plataforma— para no romper la invariante de que **todo usuario tiene `coach_id`**.
        Lo que lo distingue no es de quien cuelga, sino que sus rutas abren sesion sin
        alcance con motivo por escrito.
        """
        return self.rol == "admin_plataforma"


def _falla(codigo: Codigo) -> HTTPException:
    estado, texto = respuesta_para(codigo)
    return HTTPException(status_code=estado, detail={"codigo": codigo.value, "mensaje": texto})


def actor_actual(
    lm_sesion: Annotated[str | None, Cookie(alias=NOMBRE_COOKIE)] = None,
) -> Actor:
    """Resuelve la sesion. Se consulta sin alcance a proposito: todavia no sabemos cual es."""
    if not lm_sesion:
        raise _falla(Codigo.SESION_EXPIRADA)

    # La busqueda de sesion es la unica lectura que precede al alcance, y por eso va contra
    # una tabla sin datos de alumnas: la fila de sesion no revela nada de otra coach.
    with Session(motor()) as s:
        consulta = (
            select(FilaSesion, Usuario)
            .join(Usuario, Usuario.id == FilaSesion.usuario_id)
            .where(FilaSesion.token_hash == hash_de_token(lm_sesion))
        )
        fila = s.execute(consulta.execution_options(sin_alcance=True)).first()

        if fila is None:
            raise _falla(Codigo.SESION_EXPIRADA)

        sesion, usuario = fila
        if sesion.revocada_en is not None or sesion.vence_en < ahora_utc():
            raise _falla(Codigo.SESION_EXPIRADA)
        if usuario.estado != "activo":
            raise _falla(Codigo.SIN_PERMISO)

        return Actor(usuario_id=usuario.id, coach_id=usuario.coach_id, rol=usuario.rol)


def datos(actor: Annotated[Actor, Depends(actor_actual)]) -> Iterator[Session]:
    """Sesion de base ya atada al inquilino del actor. Es la unica puerta de las rutas."""
    with sesion_con_alcance(actor.coach_id) as s:
        yield s


def solo_coach(actor: Annotated[Actor, Depends(actor_actual)]) -> Actor:
    if not actor.es_coach:
        raise _falla(Codigo.SIN_PERMISO)
    return actor


def solo_alumna(actor: Annotated[Actor, Depends(actor_actual)]) -> Actor:
    if not actor.es_alumna:
        raise _falla(Codigo.SIN_PERMISO)
    return actor


def solo_admin(actor: Annotated[Actor, Depends(actor_actual)]) -> Actor:
    """Superadmin. **Una coach no lo es aunque sea la unica del sistema.**"""
    if not actor.es_admin:
        raise _falla(Codigo.SIN_PERMISO)
    return actor
