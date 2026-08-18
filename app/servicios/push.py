"""Notificaciones push con Web Push y VAPID.

Es el canal principal del día a día del método: no depende de correo ni de dominio de
correo, y no tiene el problema de reputación que tiene enviar desde una cuenta personal.

**Una suscripción caducada se borra, no se reintenta.** Cuando el navegador responde 404 o
410, esa suscripción murió —desinstaló la app, limpió datos, cambió de teléfono— y seguir
insistiendo solo gasta llamadas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from app.config import ajustes

#: Códigos con los que el servicio de push dice «esta suscripción ya no existe».
MUERTAS = frozenset({404, 410})

#: Tope del cuerpo. El estándar permite 4 KB; pasarse hace que el envío falle entero.
BYTES_MAXIMOS = 3800


@dataclass(frozen=True, slots=True)
class Suscripcion:
    endpoint: str
    p256dh: str
    auth: str

    def como_dict(self) -> dict[str, object]:
        return {"endpoint": self.endpoint, "keys": {"p256dh": self.p256dh, "auth": self.auth}}


@dataclass(frozen=True, slots=True)
class Notificacion:
    titulo: str
    cuerpo: str
    #: A dónde lleva el toque. Relativa: el service worker la resuelve contra su origen.
    ruta: str = "/inicio"
    etiqueta: str | None = None

    def como_json(self) -> str:
        payload = {
            "titulo": self.titulo,
            # Se recorta aquí y no en el destino: un payload de más falla el envío completo.
            "cuerpo": self.cuerpo[:300],
            "ruta": self.ruta,
        }
        if self.etiqueta:
            # Etiqueta igual reemplaza la anterior en la bandeja del teléfono. Evita cinco
            # avisos apilados de lo mismo.
            payload["etiqueta"] = self.etiqueta
        crudo = json.dumps(payload, ensure_ascii=False)
        return crudo[:BYTES_MAXIMOS]


@dataclass(frozen=True, slots=True)
class Resultado:
    entregada: bool
    #: True cuando la suscripción murió y hay que borrarla.
    caducada: bool
    error: str | None = None


class Emisor(Protocol):
    def enviar(self, suscripcion: Suscripcion, notificacion: Notificacion) -> Resultado: ...


class EmisorEnMemoria:
    """Guarda en lugar de enviar. Es el de desarrollo y el de las pruebas."""

    def __init__(self) -> None:
        self.enviadas: list[tuple[Suscripcion, Notificacion]] = []

    def enviar(self, suscripcion: Suscripcion, notificacion: Notificacion) -> Resultado:
        self.enviadas.append((suscripcion, notificacion))
        return Resultado(entregada=True, caducada=False)


class EmisorWebPush:
    """Envío real con `pywebpush`."""

    def enviar(self, suscripcion: Suscripcion, notificacion: Notificacion) -> Resultado:
        cfg = ajustes()
        if not cfg.vapid_privada:
            return Resultado(False, False, "Falta LM_VAPID_PRIVADA en la configuración")

        try:
            from pywebpush import WebPushException, webpush

            webpush(
                subscription_info=suscripcion.como_dict(),
                data=notificacion.como_json(),
                vapid_private_key=cfg.vapid_privada,
                vapid_claims={"sub": cfg.vapid_contacto or "mailto:soporte@myfittplan.com"},
                timeout=10,
            )
            return Resultado(entregada=True, caducada=False)

        except WebPushException as causa:
            codigo = getattr(causa.response, "status_code", None)
            if codigo in MUERTAS:
                return Resultado(False, True, f"suscripción caducada ({codigo})")
            return Resultado(False, False, f"{codigo}: {causa}"[:300])

        except Exception as causa:
            return Resultado(False, False, f"{type(causa).__name__}: {causa}"[:300])


_emisor: Emisor | None = None


def emisor() -> Emisor:
    """En cualquier entorno que no sea producción, en memoria: un `pytest` que dispare
    notificaciones a teléfonos reales es un accidente esperando a ocurrir."""
    global _emisor
    if _emisor is None:
        _emisor = EmisorWebPush() if ajustes().es_produccion else EmisorEnMemoria()
    return _emisor


def usar_emisor(nuevo: Emisor) -> None:
    global _emisor
    _emisor = nuevo


# ---------------------------------------------------------------------------
# Textos
# ---------------------------------------------------------------------------

from app.dominio.avisos import Aviso  # noqa: E402

#: Título y cuerpo de cada aviso que sale por push. `{}` se rellena con el contexto.
#:
#: Son cortos a propósito: en la pantalla de bloqueo de un teléfono caben dos líneas, y lo
#: que no cabe se corta a media palabra.
TEXTOS: dict[Aviso, tuple[str, str, str]] = {
    Aviso.RECORDATORIO_CHEQUEO: (
        "Tu chequeo de este mes",
        "Hazlo mañana al despertar, en ayunas.",
        "/chequeo",
    ),
    Aviso.CHEQUEO_RECIBIDO: ("Chequeo enviado", "{coach} lo revisará pronto.", "/inicio"),
    Aviso.CHEQUEO_VALIDADO: (
        "{coach} revisó tu chequeo",
        "Ya puedes leer su feedback.",
        "/evolucion",
    ),
    Aviso.CHEQUEO_RECHAZADO: (
        "Hay que repetir una toma",
        "{coach} te dejó el motivo.",
        "/chequeo",
    ),
    Aviso.INACTIVIDAD: ("¿Todo bien?", "Llevas unos días sin entrar.", "/inicio"),
    Aviso.PLAN_PUBLICADO: ("Tu plan nuevo está listo", "Ábrelo cuando quieras.", "/plan"),
    Aviso.CITA_AGENDADA: ("Consulta agendada", "{fecha} a las {hora_inicio}.", "/inicio"),
    Aviso.CITA_RECORDATORIO: ("Mañana tienes consulta", "A las {hora_inicio}.", "/inicio"),
    Aviso.CITA_CANCELADA: ("Se canceló tu consulta", "{motivo}", "/inicio"),
    Aviso.CITA_REAGENDADA: ("Cambió tu consulta", "Ahora es el {fecha}.", "/inicio"),
    Aviso.PAGO_PROXIMO: ("Tu ciclo termina pronto", "Vence el {vence}.", "/inicio"),
    Aviso.PAGO_RECIBIDO: ("Comprobante recibido", "{coach} lo va a validar.", "/inicio"),
    Aviso.PAGO_VALIDADO: ("Pago validado", "Tu plan ya está disponible.", "/plan"),
    Aviso.PAGO_RECHAZADO: ("Tu comprobante necesita corrección", "{motivo}", "/inicio"),
    Aviso.PAGO_VENCIDO: ("Tu ciclo terminó", "Tu plan quedó en pausa.", "/inicio"),
    # El único que no trae texto propio: lo escribe la coach y llega tal cual.
    Aviso.MENSAJE_DE_COACH: ("{titulo}", "{cuerpo}", "/avisos"),
    Aviso.PURGA_PROXIMA: (
        "Tus fotos se borran en 15 días",
        "Descárgalas si quieres conservarlas.",
        "/cuenta",
    ),
}


def redactar(aviso: Aviso, contexto: dict[str, object]) -> Notificacion:
    """Un aviso que sale por push sin texto es un error de programación, no de datos."""
    if aviso not in TEXTOS:
        raise KeyError(f"{aviso} no tiene texto de notificación")
    titulo, cuerpo, ruta = TEXTOS[aviso]
    return Notificacion(
        titulo=titulo.format(**contexto),
        cuerpo=cuerpo.format(**contexto),
        ruta=ruta,
        # Dos avisos del mismo tipo se pisan en la bandeja del teléfono, que es lo que se
        # quiere en un recordatorio y lo contrario de lo que se quiere en dos frases
        # distintas de la coach. Por eso el contexto puede traer la suya.
        etiqueta=str(contexto.get("etiqueta") or aviso.value),
    )
