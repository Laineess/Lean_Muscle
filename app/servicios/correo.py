"""Envío de correo.

**Detrás de una interfaz a propósito.** Hoy sale por SMTP desde una cuenta de correo; el día
que haya buzón en myprogressplan.com con SPF, DKIM y DMARC, se cambia una clase y nada más.

Advertencia que conviene tener presente y que el diseño no puede resolver solo: el correo
automático enviado desde una cuenta personal a decenas de destinatarios distintos es
exactamente el patrón que los filtros marcan como sospechoso, y el proveedor puede suspender
la cuenta. Por eso:

- el volumen se limita con espaciado y reintento, nunca en ráfaga;
- el correo se reserva para lo que no puede perderse (`app/dominio/avisos.py`);
- todo lo demás sale por notificación dentro de la plataforma.
"""

from __future__ import annotations

import smtplib
import time
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr
from typing import Protocol

from app.config import ajustes


@dataclass(frozen=True, slots=True)
class Adjunto:
    nombre: str
    contenido: bytes
    tipo: str = "application/pdf"


@dataclass(frozen=True, slots=True)
class Correo:
    para: str
    asunto: str
    #: Se envía en las dos formas: HTML para quien lo lee cómodo, texto plano para el resto
    #: y para los filtros, que castigan un correo sin alternativa de texto.
    cuerpo_texto: str
    cuerpo_html: str
    adjuntos: list[Adjunto] = field(default_factory=list)
    responder_a: str | None = None


class Emisor(Protocol):
    """Lo que el resto de la aplicación necesita saber del correo."""

    def enviar(self, correo: Correo) -> None: ...


class EmisorEnMemoria:
    """Guarda en lugar de enviar. Es lo que usan las pruebas y el entorno local.

    Que el emisor por defecto en desarrollo **no** mande correo de verdad es deliberado: un
    `pytest` que dispare mensajes a direcciones reales es un accidente esperando a ocurrir.
    """

    def __init__(self) -> None:
        self.enviados: list[Correo] = []

    def enviar(self, correo: Correo) -> None:
        self.enviados.append(correo)

    def ultimos(self, para: str) -> list[Correo]:
        return [c for c in self.enviados if c.para == para]


class EmisorSmtp:
    """Envío real por SMTP con contraseña de aplicación.

    `espaciado` separa un envío del siguiente. Mandar cincuenta correos en un segundo es la
    forma más rápida de que el proveedor corte la cuenta.
    """

    def __init__(self, espaciado: float = 1.5) -> None:
        self.espaciado = espaciado
        self._ultimo_envio = 0.0

    def enviar(self, correo: Correo) -> None:
        cfg = ajustes()
        if not cfg.smtp_host or not cfg.smtp_usuario:
            raise RuntimeError(
                "Falta configurar SMTP en config.env. En desarrollo usa EmisorEnMemoria."
            )

        espera = self.espaciado - (time.monotonic() - self._ultimo_envio)
        if espera > 0:
            time.sleep(espera)

        mensaje = EmailMessage()
        mensaje["From"] = formataddr(("MyProgressPlan", cfg.smtp_remitente or cfg.smtp_usuario))
        mensaje["To"] = correo.para
        mensaje["Subject"] = correo.asunto
        if correo.responder_a:
            mensaje["Reply-To"] = correo.responder_a

        mensaje.set_content(correo.cuerpo_texto)
        mensaje.add_alternative(correo.cuerpo_html, subtype="html")

        for adjunto in correo.adjuntos:
            tipo, subtipo = adjunto.tipo.split("/", 1)
            mensaje.add_attachment(
                adjunto.contenido, maintype=tipo, subtype=subtipo, filename=adjunto.nombre
            )

        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_puerto, timeout=30) as servidor:
            servidor.starttls()
            servidor.login(cfg.smtp_usuario, cfg.smtp_contrasena_app)
            servidor.send_message(mensaje)

        self._ultimo_envio = time.monotonic()


_emisor: Emisor | None = None


def emisor() -> Emisor:
    """El emisor de la aplicación.

    En producción manda de verdad. Fuera de producción guarda en memoria, salvo que se pida
    lo contrario con `LM_CORREO_REAL=true`: es la única forma de probar el envío en local
    sin declararse en producción, que además marca la cookie de sesión como `secure` y la
    rompe sobre `http://localhost`.
    """
    global _emisor
    if _emisor is None:
        cfg = ajustes()
        real = cfg.es_produccion or cfg.correo_real
        _emisor = EmisorSmtp() if real else EmisorEnMemoria()
    return _emisor


def usar_emisor(nuevo: Emisor) -> None:
    """Sustituye el emisor. Para pruebas y para el trabajador."""
    global _emisor
    _emisor = nuevo
