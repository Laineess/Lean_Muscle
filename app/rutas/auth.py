"""Acceso y cierre de sesión.

El token viaja en una cookie **HttpOnly**: JavaScript no lo lee ni lo escribe, así que un
XSS no puede robarla. En la tabla se guarda solo su hash, para que un volcado de la base no
permita suplantar sesiones.

«Recordarme» alarga la vigencia de la cookie. **No guarda la contraseña en ninguna parte**;
el frontend solo recuerda el correo, en el navegador, para no reescribirlo.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.config import ajustes
from app.datos.alcance import motor, sesion_con_alcance
from app.datos.modelos import Alumna, Coach, Usuario
from app.datos.modelos import Sesion as FilaSesion
from app.dominio.avisos import Aviso as AvisoDominio
from app.rutas.esquemas import ActorPublico, CambioDeContrasena, Credenciales
from app.rutas.sesion import NOMBRE_COOKIE, Actor, actor_actual
from app.servicios import avisos as cola
from app.servicios import cuentas
from app.servicios.seguridad import (
    hash_contrasena,
    hash_de_token,
    nuevo_token_de_sesion,
    requiere_rehash,
    verificar_contrasena,
)

ruteador = APIRouter(prefix="/api/auth", tags=["acceso"])

#: Sesión corta por defecto; «recordarme» la lleva a 30 días.
VIGENCIA_CORTA = timedelta(hours=12)
VIGENCIA_LARGA = timedelta(days=30)


@ruteador.post("/login", response_model=ActorPublico)
def entrar(datos: Credenciales, peticion: Request, respuesta: Response) -> ActorPublico:
    with Session(motor()) as s:
        # Esta es la única lectura que precede al alcance: todavía no sabemos de qué coach
        # es el usuario. Va contra `usuario`, que no expone datos de otras alumnas.
        usuario = s.scalars(
            select(Usuario)
            .where(Usuario.email == datos.correo.strip().lower())
            .execution_options(sin_alcance=True)
        ).first()

        # Se verifica siempre, exista o no el usuario: comparar contra un hash falso mantiene
        # constante el tiempo de respuesta y no revela qué correos están dados de alta.
        hash_guardado = usuario.hash_contrasena if usuario else hash_contrasena("inexistente")
        correcta = verificar_contrasena(hash_guardado, datos.contrasena)

        if usuario is None or not correcta or usuario.estado != "activo":
            raise ErrorDeDominio(Codigo.CREDENCIALES_INVALIDAS)

        # Los parámetros de Argon2 suben con el tiempo; al entrar se re-cifra si hace falta.
        if requiere_rehash(usuario.hash_contrasena):
            usuario.hash_contrasena = hash_contrasena(datos.contrasena)

        token, token_hash = nuevo_token_de_sesion()
        vigencia = VIGENCIA_LARGA if datos.recordarme else VIGENCIA_CORTA

        s.add(
            FilaSesion(
                coach_id=usuario.coach_id,
                usuario_id=usuario.id,
                token_hash=token_hash,
                vence_en=ahora_utc() + vigencia,
                ip=peticion.client.host if peticion.client else None,
                user_agent=(peticion.headers.get("user-agent") or "")[:255],
            )
        )
        usuario.ultimo_acceso_en = ahora_utc()
        s.commit()

        rol = usuario.rol
        coach_id = usuario.coach_id
        usuario_id = usuario.id

    respuesta.set_cookie(
        NOMBRE_COOKIE,
        token,
        max_age=int(vigencia.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=ajustes().es_produccion,
        path="/",
    )

    return _actor_publico(coach_id, usuario_id, rol)


@ruteador.post("/logout", status_code=204)
def salir(
    actor: Annotated[Actor, Depends(actor_actual)],
    peticion: Request,
    respuesta: Response,
) -> None:
    """Revoca la sesión en la base, no solo en el navegador.

    Borrar la cookie sin revocar dejaría el token vivo: quien lo hubiera copiado seguiría
    dentro.
    """
    token = peticion.cookies.get(NOMBRE_COOKIE)
    if token:
        with sesion_con_alcance(actor.coach_id) as s:
            fila = s.scalars(
                select(FilaSesion).where(FilaSesion.token_hash == hash_de_token(token))
            ).first()
            if fila is not None:
                fila.revocada_en = ahora_utc()

    respuesta.delete_cookie(NOMBRE_COOKIE, path="/")


@ruteador.post("/contrasena", status_code=204)
def cambiar_contrasena(
    cuerpo: CambioDeContrasena,
    actor: Annotated[Actor, Depends(actor_actual)],
    peticion: Request,
    respuesta: Response,
) -> None:
    """Cambia la contraseña, **revoca todas las sesiones** y avisa por correo.

    Revocar es la mitad del valor: si alguien más había entrado, cambiar la contraseña sin
    cerrar sus sesiones no lo saca, porque su cookie sigue viva. Se cierra también la de
    quien hace el cambio, y por eso el frontend lo manda de vuelta al acceso.

    El correo tampoco es cortesía: si el cambio no lo hizo ella, es la única señal de que
    alguien tiene acceso a su expediente.
    """
    with sesion_con_alcance(actor.coach_id) as s:
        cuentas.cambiar_contrasena(s, actor.usuario_id, cuerpo.actual, cuerpo.nueva)

        usuario = s.get(Usuario, actor.usuario_id)
        if usuario is not None:
            cola.encolar(
                s,
                AvisoDominio.CONTRASENA_CAMBIADA,
                coach_id=actor.coach_id,
                llave=f"usuario:{usuario.id}:contrasena:{ahora_utc().isoformat()}",
                para=usuario.email,
                contexto={
                    "nombre": usuario.email.split("@")[0],
                    "momento": ahora_utc().strftime("%d/%m/%Y a las %H:%M UTC"),
                },
                destinatario_id=usuario.id,
            )

    _ = peticion
    respuesta.delete_cookie(NOMBRE_COOKIE, path="/")


@ruteador.get("/yo", response_model=ActorPublico)
def yo(actor: Annotated[Actor, Depends(actor_actual)]) -> ActorPublico:
    """Quién soy. El frontend la llama al arrancar para saber si hay sesión viva."""
    return _actor_publico(actor.coach_id, actor.usuario_id, actor.rol)


def _actor_publico(coach_id: int, usuario_id: int, rol: str) -> ActorPublico:
    with sesion_con_alcance(coach_id) as s:
        coach = s.get(Coach, coach_id)
        nombre = coach.nombre if coach else ""

        if rol == "alumna":
            alumna = s.scalars(select(Alumna).where(Alumna.usuario_id == usuario_id)).first()
            if alumna is not None:
                nombre = alumna.nombre

        usuario = s.get(Usuario, usuario_id)

        return ActorPublico(
            rol=rol,
            nombre=nombre,
            correo=usuario.email if usuario else "",
            color_acento=coach.color_acento if coach else "#c9a227",
            marca=coach.nombre if coach else "MyProgressPlan",
        )
