"""Sesion de la peticion y dependencias de rol.

Regla que no se negocia: **el `coach_id` sale siempre de la sesion, nunca del cliente**.
Un `coach_id` que venga en el cuerpo, en la query o en una cabecera se ignora, incluso en
endpoints internos.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine, Iterator
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Cookie, Depends, HTTPException, Request, Response
from fastapi.routing import APIRoute
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
    #: Entró con la contraseña con la que se dio de alta y todavía no la ha cambiado.
    debe_cambiar_contrasena: bool = False

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

        return Actor(
            usuario_id=usuario.id,
            coach_id=usuario.coach_id,
            rol=usuario.rol,
            debe_cambiar_contrasena=usuario.debe_cambiar_contrasena,
        )


def actor_establecido(actor: Annotated[Actor, Depends(actor_actual)]) -> Actor:
    """Actor que ya puso su propia contrasena.

    Toda cuenta nace con una contrasena inicial conocida —la coach la dicta— y con eso basta
    para entrar una vez. Mientras no la cambie, esta guarda cierra el resto de la aplicacion:
    sin ella, una contrasena que conoce cualquiera seria una contrasena permanente.
    """
    if actor.debe_cambiar_contrasena:
        raise _falla(Codigo.CONTRASENA_INICIAL_SIN_CAMBIAR)
    return actor


def datos(
    peticion: Request, actor: Annotated[Actor, Depends(actor_establecido)]
) -> Iterator[Session]:
    """Sesion de base ya atada al inquilino del actor. Es la unica puerta de las rutas.

    Queda anotada en la peticion para que `RutaQueConfirma` la confirme antes de responder.
    """
    with sesion_con_alcance(actor.coach_id) as s:
        peticion.state.sesion = s
        yield s


class RutaQueConfirma(APIRoute):
    """Confirma la sesion antes de mandar la respuesta.

    El cierre de una dependencia con `yield` corre **despues** de responder, asi que el
    commit quedaba fuera de la peticion: quien pedia lo recien creado a vuelta de correo
    recibia un 404 una de cada cuatro veces. Aqui se confirma con la respuesta todavia en
    la mano, y un commit que revienta sale como 500 en lugar de como un «guardado» falso.
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def con_commit(peticion: Request) -> Response:
            respuesta = await original(peticion)
            sesion: Session | None = getattr(peticion.state, "sesion", None)
            if sesion is not None:
                sesion.commit()
            return respuesta

        return con_commit


def solo_coach(actor: Annotated[Actor, Depends(actor_establecido)]) -> Actor:
    if not actor.es_coach:
        raise _falla(Codigo.SIN_PERMISO)
    return actor


def solo_alumna(actor: Annotated[Actor, Depends(actor_establecido)]) -> Actor:
    if not actor.es_alumna:
        raise _falla(Codigo.SIN_PERMISO)
    return actor


def solo_alumna_aceptada(
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> Actor:
    """Alumna de verdad, no una solicitud del registro abierto.

    Mientras la coach no la acepte, la relacion no existe: no hay chequeo que abrir ni plan
    que leer, y sobre todo no se le piden fotografias corporales. Todo lo que necesita el
    recorrido de registro usa `solo_alumna` a secas; lo demas pasa por aqui.
    """
    from app.datos.repos import consultas as q

    alumna = q.alumna_de_usuario(s, actor.usuario_id)
    if alumna is None or alumna.estado == "solicitud":
        raise _falla(Codigo.SOLICITUD_SIN_ACEPTAR)
    return actor


def solo_admin(actor: Annotated[Actor, Depends(actor_establecido)]) -> Actor:
    """Superadmin. **Una coach no lo es aunque sea la unica del sistema.**"""
    if not actor.es_admin:
        raise _falla(Codigo.SIN_PERMISO)
    return actor
