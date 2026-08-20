"""Acceso y cierre de sesión. El token va en una cookie HttpOnly —un XSS no puede leerla— y
en la tabla solo queda su hash. «Recordarme» alarga la cookie; no guarda la contraseña.
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
from app.datos.modelos import Alumna, ClaveTemporal, Coach, Usuario
from app.datos.modelos import Sesion as FilaSesion
from app.dominio.avisos import Aviso as AvisoDominio
from app.rutas.esquemas import ActorPublico, CambioDeContrasena, Credenciales
from app.rutas.sesion import NOMBRE_COOKIE, Actor, RutaQueConfirma, actor_actual
from app.servicios import avisos as cola
from app.servicios import cuentas, limites
from app.servicios.seguridad import (
    clave_temporal_vigente,
    hash_contrasena,
    hash_de_token,
    nuevo_token_de_sesion,
    requiere_rehash,
    verificar_contrasena,
)

ruteador = APIRouter(prefix="/api/auth", tags=["acceso"], route_class=RutaQueConfirma)

#: Sesión corta por defecto; «recordarme» la lleva a 30 días.
VIGENCIA_CORTA = timedelta(hours=12)
VIGENCIA_LARGA = timedelta(days=30)


def _clave_inicial_vigente(s: Session, usuario_id: int) -> bool:
    """Si la contraseña de alta o restablecimiento sigue en plazo. Solo aplica a quien no ha
    puesto la suya; la coach la vuelve a emitir desde la ficha."""
    # Sin alcance a propósito, como el resto del login: todavía no se sabe de qué coach es
    # quien escribe, y esto corre antes de abrir la sesión con inquilino.
    alumna = s.scalars(
        select(Alumna).where(Alumna.usuario_id == usuario_id).execution_options(sin_alcance=True)
    ).first()
    if alumna is None:
        # Una coach o el superadmin: su contraseña no la dicta nadie, así que no caduca.
        return True

    ultima = s.scalars(
        select(ClaveTemporal)
        .where(ClaveTemporal.alumna_id == alumna.id)
        .order_by(ClaveTemporal.vence_en.desc())
        .execution_options(sin_alcance=True)
    ).first()
    if ultima is None:
        # Cuenta anterior a que se llevara constancia. No se le cierra la puerta por eso.
        return True
    return clave_temporal_vigente(ultima.vence_en)


@ruteador.post("/login", response_model=ActorPublico)
def entrar(datos: Credenciales, peticion: Request, respuesta: Response) -> ActorPublico:
    correo = datos.correo.strip().lower()
    ip = peticion.client.host if peticion.client else None

    with Session(motor()) as s:
        # Antes de mirar credenciales, para no gastar un Argon2 por intento: eso es lo que
        # convertiría la fuerza bruta en una forma de tumbar el servidor.
        if limites.bloqueado(s, correo, ip):
            raise ErrorDeDominio(Codigo.DEMASIADOS_INTENTOS)

        # Esta es la única lectura que precede al alcance: todavía no sabemos de qué coach
        # es el usuario. Va contra `usuario`, que no expone datos de otras alumnas.
        usuario = s.scalars(
            select(Usuario).where(Usuario.email == correo).execution_options(sin_alcance=True)
        ).first()

        # Se verifica siempre, exista o no el usuario: comparar contra un hash falso mantiene
        # constante el tiempo de respuesta y no revela qué correos están dados de alta.
        hash_guardado = usuario.hash_contrasena if usuario else hash_contrasena("inexistente")
        correcta = verificar_contrasena(hash_guardado, datos.contrasena)

        if usuario is None or not correcta or usuario.estado != "activo":
            limites.registrar(s, correo, ip, exitoso=False)
            s.commit()
            raise ErrorDeDominio(Codigo.CREDENCIALES_INVALIDAS)

        limites.registrar(s, correo, ip, exitoso=True)

        # La contraseña de alta es pública —la dicta la coach— y por eso caduca: sin esto,
        # quien conociera el correo de una alumna sin estrenar podría tomarle la cuenta.
        if usuario.debe_cambiar_contrasena and not _clave_inicial_vigente(s, usuario.id):
            limites.registrar(s, correo, ip, exitoso=False)
            s.commit()
            raise ErrorDeDominio(Codigo.CLAVE_INICIAL_VENCIDA)

        # Los parámetros de Argon2 suben con el tiempo; al entrar se re-cifra si hace falta.
        if requiere_rehash(usuario.hash_contrasena):
            usuario.hash_contrasena = hash_contrasena(datos.contrasena)

        # Antes del commit: esta sesión conserva `expire_on_commit=True`, así que después
        # tocar `usuario.rol` dispara una recarga sin la exención `sin_alcance` y falla.
        rol = usuario.rol
        coach_id = usuario.coach_id
        usuario_id = usuario.id
        debe_cambiar = usuario.debe_cambiar_contrasena

        crear_sesion(s, coach_id, usuario_id, peticion, respuesta, datos.recordarme)
        usuario.ultimo_acceso_en = ahora_utc()
        s.commit()

    return actor_publico(coach_id, usuario_id, rol, debe_cambiar)


def crear_sesion(
    s: Session,
    coach_id: int,
    usuario_id: int,
    peticion: Request,
    respuesta: Response,
    recordarme: bool = False,
) -> None:
    """Deja la fila de sesión y pone la cookie. Es la única puerta que abre una sesión, y
    por eso la usan tanto el acceso como el registro abierto."""
    token, token_hash = nuevo_token_de_sesion()
    vigencia = VIGENCIA_LARGA if recordarme else VIGENCIA_CORTA

    s.add(
        FilaSesion(
            coach_id=coach_id,
            usuario_id=usuario_id,
            token_hash=token_hash,
            vence_en=ahora_utc() + vigencia,
            ip=peticion.client.host if peticion.client else None,
            user_agent=(peticion.headers.get("user-agent") or "")[:255],
        )
    )

    respuesta.set_cookie(
        NOMBRE_COOKIE,
        token,
        max_age=int(vigencia.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=ajustes().es_produccion,
        path="/",
    )


@ruteador.post("/logout", status_code=204)
def salir(
    actor: Annotated[Actor, Depends(actor_actual)],
    peticion: Request,
    respuesta: Response,
) -> None:
    """Revoca la sesión en la base y no solo en el navegador: borrar la cookie dejaría el
    token vivo para quien lo hubiera copiado."""
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
    """Cambia la contraseña, revoca todas las sesiones y avisa por correo.

    Revocar es la mitad del valor: sin eso, la cookie de quien ya había entrado sigue viva.
    Y el correo es la única señal que tiene la alumna si el cambio no lo hizo ella.
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
    return actor_publico(actor.coach_id, actor.usuario_id, actor.rol, actor.debe_cambiar_contrasena)


def actor_publico(
    coach_id: int, usuario_id: int, rol: str, debe_cambiar: bool = False
) -> ActorPublico:
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
            color_secundario=coach.color_secundario if coach else "#0e3b2b",
            marca=(coach.marca or coach.nombre) if coach else "MyFittPlan",
            debe_cambiar_contrasena=debe_cambiar,
        )
