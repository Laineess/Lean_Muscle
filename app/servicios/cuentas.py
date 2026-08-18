"""Alta de alumnas y cambio de contraseña. Vive en servicios porque el alta toca varias
tablas y tiene que quedar consistente: no puede quedar un usuario sin alumna.
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
from app.datos.modelos import Alumna, Ciclo, Coach, CobroProgramado, Usuario
from app.servicios.seguridad import (
    VIGENCIA_CLAVE_TEMPORAL,
    contrasena_inicial,
    exigir_mayor_de_edad,
    hash_contrasena,
    nueva_clave_temporal,
    verificar_contrasena,
)

#: Deliberadamente permisivo. Validar correos con expresión regular estricta rechaza
#: direcciones válidas; lo que de verdad confirma un correo es que llegue la invitación.
CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")

LONGITUD_MINIMA_CONTRASENA = 8


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
    """Ocho caracteres, un número y un carácter especial: la regla que pidió la clienta.
    El largo pesa más que la variedad, y por eso el freno de fuerza bruta importa igual."""
    if len(clara) < LONGITUD_MINIMA_CONTRASENA:
        raise ErrorDeDominio(Codigo.CONTRASENA_DEBIL, minimo=LONGITUD_MINIMA_CONTRASENA)
    if not any(c.isdigit() for c in clara):
        raise ErrorDeDominio(Codigo.CONTRASENA_DEBIL, minimo=LONGITUD_MINIMA_CONTRASENA)
    # Especial por exclusión: cualquier cosa que no sea letra, número ni espacio. Una lista
    # cerrada de símbolos empuja a que todo el mundo termine el suyo en el mismo signo.
    if not any(not c.isalnum() and not c.isspace() for c in clara):
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
    tarifa_id: int | None,
    nivel_experiencia: str | None,
    emitida_por: int,
) -> AltaHecha:
    """Alta con su ciclo inicial y su clave temporal. Sin datos de salud: que la coach los
    capture por ella viciaría el consentimiento, que la ley exige expreso y personal."""
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

    from app.datos.modelos import Tarifa

    plan = s.get(Tarifa, tarifa_id) if tarifa_id else None

    activas = (
        s.scalar(select(func.count()).select_from(Alumna).where(Alumna.estado == "activa")) or 0
    )
    if activas >= coach.limite_alumnas:
        raise ErrorDeDominio(
            Codigo.LIMITE_DE_ALUMNAS_ALCANZADO, activas=activas, limite=coach.limite_alumnas
        )

    clave = contrasena_inicial()

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
        tarifa_id=tarifa_id,
        nivel_experiencia=nivel_experiencia,
        zona_horaria=coach.zona_horaria,
        cuestionario_completo=False,
        estado="activa",
    )
    s.add(alumna)
    s.flush()

    hoy = ahora_utc().date()
    precio = plan.precio if plan is not None else coach.precio_ciclo
    s.add(
        Ciclo(
            coach_id=coach_id,
            alumna_id=alumna.id,
            numero=1,
            inicia_en=hoy,
            termina_en=hoy + timedelta(days=30),
            estado="pendiente_pago",
            precio=precio,
        )
    )

    # El primer cobro nace con ella: el flujo de pagos cuelga del cobro y no del ciclo, así
    # que sin esta fila veía que debía pagar sin tener contra qué subir su comprobante.
    if precio > 0:
        s.add(
            CobroProgramado(
                coach_id=coach_id,
                alumna_id=alumna.id,
                fecha=hoy,
                motivo="inscripcion",
                concepto=f"Inscripción · {plan.nombre}" if plan is not None else "Inscripción",
                monto=precio,
                estado="pendiente",
            )
        )

    # La misma constancia que un restablecimiento: la contraseña inicial es pública, así que
    # tiene que caducar. Sin esta fila el login no sabría desde cuándo cuenta el plazo.
    _anotar_clave(s, coach_id, alumna.id, emitida_por, clave, "alta de la alumna")

    return AltaHecha(alumna_ulid=alumna.ulid, correo=correo, clave_temporal=clave)


def emitir_clave_temporal(s: Session, alumna: Alumna, emitida_por: int, motivo: str) -> str:
    """Recuperación de acceso: la coach verifica identidad y emite la clave. `motivo`
    documenta cómo lo verificó, que es lo único que distingue entregársela a ella."""
    if not motivo.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)

    clave = contrasena_inicial()
    usuario = s.get(Usuario, alumna.usuario_id)
    if usuario is None:  # pragma: no cover - defensivo
        raise ErrorDeDominio(Codigo.SIN_PERMISO)

    usuario.hash_contrasena = hash_contrasena(clave)
    usuario.debe_cambiar_contrasena = True

    _anotar_clave(s, alumna.coach_id, alumna.id, emitida_por, clave, motivo.strip()[:255])
    return clave


def _anotar_clave(
    s: Session, coach_id: int, alumna_id: int, emitida_por: int, clave: str, motivo: str
) -> None:
    """Deja la constancia con su plazo. Es lo que hace que la clave caduque de verdad."""
    from app.datos.modelos import ClaveTemporal

    s.add(
        ClaveTemporal(
            coach_id=coach_id,
            alumna_id=alumna_id,
            emitida_por=emitida_por,
            hash=hash_contrasena(clave),
            vence_en=ahora_utc() + VIGENCIA_CLAVE_TEMPORAL,
            motivo_verificacion=motivo,
        )
    )


def cambiar_contrasena(s: Session, usuario_id: int, actual: str, nueva: str) -> None:
    """Cambia la contraseña y revoca las demás sesiones: sin eso, la cookie de quien ya
    había entrado sigue viva."""
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
    marca: str,
    correo: str,
    slug: str | None,
    plan: str,
    limite_alumnas: int,
    precio_ciclo: Decimal,
    color_acento: str,
    zona_horaria: str,
) -> tuple[str, str, str]:
    """Crea un inquilino con su usuaria coach: (ulid, correo, clave temporal). Solo lo llama
    el superadmin, sin alcance, porque el inquilino al que atarse todavia no existe."""
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
        marca=(marca.strip() or nombre.strip())[:120],
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
