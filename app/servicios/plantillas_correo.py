"""Los textos de cada correo, en un solo lugar.

Igual que `app/rutas/traduccion.py` con los errores: el dominio decide **qué** avisar y aquí
se decide **cómo se dice**. Cambiar una redacción no obliga a tocar una regla de negocio.

Cada correo va en HTML y en texto plano. El texto plano no es decorativo: hay clientes que
solo lo muestran, y un correo sin alternativa de texto puntúa peor en los filtros de spam.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.dominio.avisos import Aviso

SITIO = "https://myfittplan.com"


@dataclass(frozen=True, slots=True)
class Plantilla:
    asunto: str
    #: Cuerpo en texto plano. `{}` se rellena con el contexto del aviso.
    texto: str
    #: Llamado a la acción, si lo hay.
    boton: tuple[str, str] | None = None


PLANTILLAS: dict[Aviso, Plantilla] = {
    Aviso.BIENVENIDA: Plantilla(
        asunto="{coach} te dio de alta en MyFittPlan",
        texto=(
            "Hola {nombre}:\n\n"
            "{coach} te dio de alta en MyFittPlan, donde vas a llevar tu seguimiento.\n\n"
            "Entra con este correo y la clave temporal {clave}. Al entrar te pediremos que "
            "la cambies por una tuya.\n\n"
            "La clave vence en 24 horas."
        ),
        boton=("Entrar a mi cuenta", f"{SITIO}/acceso"),
    ),
    Aviso.CLAVE_TEMPORAL: Plantilla(
        asunto="Tu clave temporal de MyFittPlan",
        texto=(
            "Hola {nombre}:\n\n"
            "{coach} generó una clave temporal para que recuperes tu acceso: {clave}\n\n"
            "Vence en 24 horas. Si no la pediste tú, avísale a tu coach de inmediato."
        ),
        boton=("Entrar", f"{SITIO}/acceso"),
    ),
    # Aviso de seguridad, no de cortesía: si no fue ella, es la señal de que alguien entró.
    Aviso.CONTRASENA_CAMBIADA: Plantilla(
        asunto="Cambiaste tu contraseña",
        texto=(
            "Hola {nombre}:\n\n"
            "Tu contraseña de MyFittPlan se cambió el {momento}.\n\n"
            "Si no fuiste tú, escríbele a tu coach ahora mismo: alguien más tiene acceso a "
            "tu cuenta, y ahí está tu historial de salud."
        ),
    ),
    Aviso.CODIGO_DE_REGISTRO: Plantilla(
        asunto="{codigo} es tu código para registrarte",
        texto=(
            "Hola:\n\n"
            "Tu código para completar el registro con {coach} es {codigo}\n\n"
            "Vence en {minutos} minutos. Si no lo pediste tú, ignora este correo: sin el "
            "código nadie puede seguir con ese registro."
        ),
    ),
    Aviso.REGISTRO_SIN_TERMINAR: Plantilla(
        asunto="Te falta poco para entrar con {coach}",
        texto=(
            "Hola {nombre}:\n\n"
            "Dejaste tu registro a medias y te falta {pendiente}.\n\n"
            "Lo que capturaste se borra en {dias} días, y con ello tu cuenta: es tu dato y "
            "no lo guardamos más de lo necesario. Si quieres seguir, retómalo cuando puedas."
        ),
        boton=("Terminar mi registro", f"{SITIO}/acceso"),
    ),
    Aviso.SOLICITUD_ACEPTADA: Plantilla(
        asunto="{coach} te aceptó: ya eres su alumna",
        texto=(
            "Hola {nombre}:\n\n"
            "{coach} revisó tu solicitud y te aceptó.\n\n"
            "Tu plan es {plan}. Tu primera consulta queda en firme: {cita}.\n\n"
            "Lo que sigue es tu primer chequeo: peso, medidas y fotos, en ayunas y al "
            "despertar. De ahí sale tu plan."
        ),
        boton=("Hacer mi chequeo", f"{SITIO}/chequeo"),
    ),
    Aviso.SOLICITUD_DESCARTADA: Plantilla(
        asunto="Sobre tu solicitud con {coach}",
        texto=(
            "Hola {nombre}:\n\n"
            "{coach} no va a poder tomarte como alumna por ahora.\n\n"
            "Lo que dice: {motivo}\n\n"
            "Tu registro y todo lo que capturaste se borran en {dias} días. Si pagaste "
            "algo, escríbele directamente a tu coach."
        ),
    ),
    Aviso.CITA_AGENDADA: Plantilla(
        asunto="Tu consulta con {coach}: {fecha}",
        texto=(
            "Hola {nombre}:\n\n"
            "{coach} agendó tu consulta.\n\n"
            "Cuándo: {fecha}, de {hora_inicio} a {hora_fin}\n"
            "Modalidad: {modalidad}\n"
            "{detalle}\n\n"
            "Te recordamos un día antes."
        ),
        boton=("Ver en mi cuenta", f"{SITIO}/inicio"),
    ),
    Aviso.CITA_CANCELADA: Plantilla(
        asunto="Se canceló tu consulta del {fecha}",
        texto=(
            "Hola {nombre}:\n\n"
            "{coach} canceló la consulta del {fecha} a las {hora_inicio}.\n\n"
            "Motivo: {motivo}\n\n"
            "En cuanto haya nueva fecha te avisamos."
        ),
    ),
    Aviso.CITA_REAGENDADA: Plantilla(
        asunto="Se movió tu consulta: ahora es el {fecha}",
        texto=(
            "Hola {nombre}:\n\n"
            "Tu consulta con {coach} cambió de horario.\n\n"
            "Nueva fecha: {fecha}, de {hora_inicio} a {hora_fin}\n"
            "Modalidad: {modalidad}"
        ),
        boton=("Ver en mi cuenta", f"{SITIO}/inicio"),
    ),
    Aviso.PAGO_VALIDADO: Plantilla(
        asunto="Recibo de tu pago · ciclo {ciclo}",
        texto=(
            "Hola {nombre}:\n\n"
            "{coach} validó tu pago de {monto}. Tu acceso queda activo hasta el {vence}.\n\n"
            "Te adjuntamos el recibo en PDF.\n\n"
            "Tu plan ya está disponible."
        ),
        boton=("Ver mi plan", f"{SITIO}/plan"),
    ),
    Aviso.PAGO_RECHAZADO: Plantilla(
        asunto="Tu comprobante necesita una corrección",
        texto=(
            "Hola {nombre}:\n\n"
            "{coach} revisó tu comprobante y no pudo validarlo.\n\n"
            "Motivo: {motivo}\n\n"
            "Puedes subir uno nuevo desde tu cuenta."
        ),
        boton=("Subir comprobante", f"{SITIO}/inicio"),
    ),
    Aviso.PAGO_VENCIDO: Plantilla(
        asunto="Tu ciclo terminó",
        texto=(
            "Hola {nombre}:\n\n"
            "Tu ciclo con {coach} terminó el {vence} y tu plan quedó en pausa.\n\n"
            "Para reactivarlo, sube tu comprobante del ciclo nuevo."
        ),
        boton=("Reactivar mi plan", f"{SITIO}/inicio"),
    ),
    Aviso.PURGA_PROXIMA: Plantilla(
        asunto="Tus fotos de {mes} se borran en 15 días",
        texto=(
            "Hola {nombre}:\n\n"
            "Como te explicamos al darte de alta, tus fotografías se conservan cuatro meses "
            "y luego se eliminan.\n\n"
            "Las de {mes} se borran el {fecha}. Si quieres conservarlas, descárgalas antes: "
            "después no se pueden recuperar.\n\n"
            "Tus medidas y tu peso no se borran, así que tus gráficas quedan intactas."
        ),
        boton=("Descargar mis fotos", f"{SITIO}/inicio"),
    ),
}


def _html(texto: str, boton: tuple[str, str] | None) -> str:
    """HTML deliberadamente pobre.

    Los clientes de correo no soportan CSS moderno: tablas, estilos en línea y poco más.
    Un correo sobrio llega mejor que uno vistoso, y aquí lo que importa es que llegue.
    """
    parrafos = "".join(
        f'<p style="margin:0 0 16px;line-height:1.6">{p.replace(chr(10), "<br>")}</p>'
        for p in texto.split("\n\n")
        if p.strip()
    )
    accion = ""
    if boton is not None:
        rotulo, enlace = boton
        accion = (
            f'<p style="margin:24px 0 0">'
            f'<a href="{enlace}" style="display:inline-block;background:#111111;color:#ffffff;'
            f'text-decoration:none;padding:12px 20px;border-radius:2px;font-weight:600">'
            f"{rotulo}</a></p>"
        )

    return (
        '<div style="font-family:-apple-system,Segoe UI,sans-serif;font-size:15px;'
        'color:#111111;max-width:520px;margin:0 auto;padding:24px">'
        f"{parrafos}{accion}"
        '<hr style="border:0;border-top:1px solid #e4e4e7;margin:32px 0 16px">'
        '<p style="font-size:12px;color:#767676;margin:0;line-height:1.5">'
        "MyFittPlan · Este correo se envió porque tienes una cuenta activa.<br>"
        f'Dudas de privacidad: <a href="{SITIO}/privacidad" style="color:#767676">'
        "myfittplan.com/privacidad</a></p></div>"
    )


def redactar(aviso: Aviso, contexto: dict[str, Any]) -> tuple[str, str, str]:
    """Devuelve (asunto, texto plano, HTML) ya rellenados.

    Un aviso sin plantilla es un error de programación, no de datos: se descubre aquí y no
    cuando la alumna recibe un correo vacío.
    """
    if aviso not in PLANTILLAS:
        raise KeyError(f"{aviso} no tiene plantilla de correo")

    plantilla = PLANTILLAS[aviso]
    asunto = plantilla.asunto.format(**contexto)
    texto = plantilla.texto.format(**contexto)
    return asunto, texto, _html(texto, plantilla.boton)
