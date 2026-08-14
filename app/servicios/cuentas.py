"""Alta de alumnas y cambio de contraseña.

Vive en servicios y no en rutas porque el alta toca varias tablas y tiene que quedar
consistente: usuario, alumna, ciclo, consentimientos pendientes y correo de invitación. Si
algo falla a mitad, no puede quedar un usuario sin alumna.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc, edad_en
from app.datos.modelos import Alumna, Ciclo, Coach, Usuario
from app.servicios.seguridad import (
    VIGENCIA_CLAVE_TEMPORAL,
    exigir_mayor_de_edad,
    hash_contrasena,
    nueva_clave_temporal,
    verificar_contrasena,
)

#: Deliberadamente permisivo. Validar correos con expresión regular estricta rechaza
#: direcciones válidas; lo que de verdad confirma un correo es que llegue la invitación.
CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")

LONGITUD_MINIMA_CONTRASENA = 10


@dataclass(frozen=True, slots=True)
class AltaHecha:
    alumna_ulid: str
    correo: str
    #: Se devuelve una sola vez, para mostrarla a la coach si el correo no llega.
    clave_temporal: str


def normalizar_correo(correo: str) -> str:
    limpio = correo.strip().lower()
    if not CORREO.match(limpio):
        raise ErrorDeDominio(Codigo.CORREO_INVALIDO, correo=limpio)
    return limpio


def validar_contrasena(clara: str) -> None:
    """Longitud sobre complejidad.

    Exigir símbolos y mayúsculas produce contraseñas cortas y predecibles anotadas en un
    papel. Diez caracteres con letras y números es un mínimo razonable que la gente sí usa.
    """
    if len(clara) < LONGITUD_MINIMA_CONTRASENA:
        raise ErrorDeDominio(Codigo.CONTRASENA_DEBIL, minimo=LONGITUD_MINIMA_CONTRASENA)
    if not (any(c.isalpha() for c in clara) and any(c.isdigit() for c in clara)):
        raise ErrorDeDominio(Codigo.CONTRASENA_DEBIL, minimo=LONGITUD_MINIMA_CONTRASENA)


def dar_de_alta(
    s: Session,
    *,
    coach_id: int,
    nombre: str,
    correo: str,
    whatsapp: str | None,
    fecha_nacimiento: date,
    estatura_cm: int | None,
    objetivo: str | None,
    nivel_experiencia: str | None,
    precio_ciclo: Decimal | None = None,
) -> AltaHecha:
    """Da de alta una alumna con su ciclo inicial y su clave temporal.

    **No captura datos de salud.** El historial clínico y los consentimientos los llena la
    propia alumna al entrar: que la coach los capture por ella viciaría el consentimiento,
    que la ley exige expreso y personal para datos sensibles.
    """
    correo = normalizar_correo(correo)

    if not nombre.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)

    # Solo mayores de 18: sus fotografías corporales exigirían consentimiento de quien
    # ejerce la patria potestad, y ese flujo no existe (Anexo Legal, §9).
    exigir_mayor_de_edad(edad_en(fecha_nacimiento, ahora_utc().date()))

    # El correo es único en toda la plataforma, no por inquilino: si no, una alumna no podría
    # distinguir con qué coach entra.
    ya_existe = s.scalars(
        select(Usuario).where(Usuario.email == correo).execution_options(sin_alcance=True)
    ).first()
    if ya_existe is not None:
        raise ErrorDeDominio(Codigo.CORREO_YA_REGISTRADO, correo=correo)

    coach = s.get(Coach, coach_id)
    if coach is None:  # pragma: no cover - defensivo
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    activas = (
        s.scalar(select(func.count()).select_from(Alumna).where(Alumna.estado == "activa")) or 0
    )
    if activas >= coach.limite_alumnas:
        raise ErrorDeDominio(
            Codigo.LIMITE_DE_ALUMNAS_ALCANZADO, activas=activas, limite=coach.limite_alumnas
        )

    clave = nueva_clave_temporal()

    usuario = Usuario(
        coach_id=coach_id,
        rol="alumna",
        email=correo,
        hash_contrasena=hash_contrasena(clave),
        estado="activo",
        # Entra con la temporal y se le obliga a cambiarla: una clave que la coach conoce no
        # es una contraseña.
        debe_cambiar_contrasena=True,
    )
    s.add(usuario)
    s.flush()

    alumna = Alumna(
        coach_id=coach_id,
        usuario_id=usuario.id,
        nombre=nombre.strip(),
        whatsapp=whatsapp,
        fecha_nacimiento=fecha_nacimiento,
        estatura_cm=estatura_cm,
        objetivo=objetivo,
        nivel_experiencia=nivel_experiencia,
        zona_horaria=coach.zona_horaria,
        cuestionario_completo=False,
        estado="activa",
    )
    s.add(alumna)
    s.flush()

    hoy = ahora_utc().date()
    s.add(
        Ciclo(
            coach_id=coach_id,
            alumna_id=alumna.id,
            numero=1,
            inicia_en=hoy,
            termina_en=hoy + timedelta(days=30),
            estado="pendiente_pago",
            precio=precio_ciclo if precio_ciclo is not None else coach.precio_ciclo,
        )
    )

    return AltaHecha(alumna_ulid=alumna.ulid, correo=correo, clave_temporal=clave)


def emitir_clave_temporal(s: Session, alumna: Alumna, emitida_por: int, motivo: str) -> str:
    """Recuperación de acceso del MVP: la coach verifica identidad y emite la clave.

    `motivo` documenta **cómo** verificó que era ella. No es burocracia: sin ese registro,
    entregar una clave por WhatsApp es indistinguible de entregársela a quien se hizo pasar
    por la alumna.
    """
    from app.datos.modelos import ClaveTemporal

    if not motivo.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)

    clave = nueva_clave_temporal()
    usuario = s.get(Usuario, alumna.usuario_id)
    if usuario is None:  # pragma: no cover - defensivo
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    usuario.hash_contrasena = hash_contrasena(clave)
    usuario.debe_cambiar_contrasena = True

    s.add(
        ClaveTemporal(
            coach_id=alumna.coach_id,
            alumna_id=alumna.id,
            emitida_por=emitida_por,
            hash=hash_contrasena(clave),
            vence_en=ahora_utc() + VIGENCIA_CLAVE_TEMPORAL,
            motivo_verificacion=motivo.strip()[:255],
        )
    )
    return clave


def cambiar_contrasena(s: Session, usuario_id: int, actual: str, nueva: str) -> None:
    """Cambia la contraseña y **revoca las demás sesiones**.

    Si alguien más había entrado, cambiar la contraseña sin cerrar sus sesiones no lo saca:
    su cookie sigue viva. Cerrarlas todas es la mitad del valor de este flujo.
    """
    from app.datos.modelos import Sesion

    usuario = s.get(Usuario, usuario_id)
    if usuario is None:  # pragma: no cover - defensivo
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    if not verificar_contrasena(usuario.hash_contrasena, actual):
        raise ErrorDeDominio(Codigo.CONTRASENA_ACTUAL_INCORRECTA)

    validar_contrasena(nueva)

    usuario.hash_contrasena = hash_contrasena(nueva)
    usuario.debe_cambiar_contrasena = False

    for sesion in s.scalars(select(Sesion).where(Sesion.usuario_id == usuario_id)):
        if sesion.revocada_en is None:
            sesion.revocada_en = ahora_utc()


def dar_de_alta_coach(
    s: Session,
    *,
    nombre: str,
    correo: str,
    slug: str | None,
    plan: str,
    limite_alumnas: int,
    precio_ciclo: Decimal,
    color_acento: str,
    zona_horaria: str,
) -> tuple[str, str, str]:
    """Crea un inquilino nuevo con su usuaria coach. Devuelve (ulid, correo, clave temporal).

    Solo lo llama el superadmin, con una sesion sin alcance: aqui se esta creando el
    inquilino, asi que todavia no hay inquilino al que atarse.

    El `slug` se deriva del nombre si no viene. Sirve para el subdominio y para la marca, y
    es unico en toda la plataforma.
    """
    from app.datos.modelos import Coach as FilaCoach

    correo = normalizar_correo(correo)
    if not nombre.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)

    ya = s.scalars(
        select(Usuario).where(Usuario.email == correo).execution_options(sin_alcance=True)
    ).first()
    if ya is not None:
        raise ErrorDeDominio(Codigo.CORREO_YA_REGISTRADO, correo=correo)

    candidato = _slug_de(slug or nombre)
    tomado = s.scalars(select(FilaCoach).where(FilaCoach.slug == candidato)).first()
    if tomado is not None:
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO, slug=candidato)

    coach = FilaCoach(
        nombre=nombre.strip(),
        slug=candidato,
        email=correo,
        plan=plan,
        limite_alumnas=limite_alumnas,
        precio_ciclo=precio_ciclo,
        color_acento=color_acento,
        zona_horaria=zona_horaria,
        estado="activa",
    )
    s.add(coach)
    s.flush()

    clave = nueva_clave_temporal()
    s.add(
        Usuario(
            coach_id=coach.id,
            rol="coach",
            email=correo,
            hash_contrasena=hash_contrasena(clave),
            estado="activo",
            # Igual que con las alumnas: una clave que otra persona conoce no es contrasena.
            debe_cambiar_contrasena=True,
        )
    )
    return coach.ulid, correo, clave


def _slug_de(texto: str) -> str:
    """Minusculas, sin tildes y con guiones. Va en la URL y en la marca."""
    import re
    import unicodedata

    plano = unicodedata.normalize("NFKD", texto)
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    plano = re.sub(r"[^a-zA-Z0-9]+", "-", plano).strip("-").lower()
    return plano[:60] or "coach"
