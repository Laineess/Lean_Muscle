"""Logs de servidor en archivos de texto planos.

Complementa la bitacora de base (que audita quien vio / que cambio que sobre datos
sensibles) con el registro de operacion: toda la actividad HTTP (con IP e ids de
usuario) en `logs/actividad.txt` y todos los errores con su detalle en
`logs/errores.txt`.

No rotan a proposito: la consigna es un unico `actividad.txt` y un unico `errores.txt`
que crecen; quien administra el servidor los vacia cuando quiere. Como lo que se escribe
contiene IP e ids, `logs/` esta en `.gitignore` y nunca llega al repositorio.
"""

from __future__ import annotations

import logging
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_LOGS = RAIZ / "logs"
ARCHIVO_ACTIVIDAD = CARPETA_LOGS / "actividad.txt"
ARCHIVO_ERRORES = CARPETA_LOGS / "errores.txt"

#: Formato compacto y de una sola linea para que un grep no tropiece con saltos de linea.
_FORMATO_LINEA = "%(asctime)s | %(message)s"
#: Rueda el reloj en cada registro para que el timestamp no se rompa con la traza multilinea.
_FORMATO_DETALLE = "%(asctime)s | %(levelname)s | %(message)s"

#: Loggers propios: uno para actividad (INFO) y otro para errores (+ severidades).
registro_actividad = logging.getLogger("myfittplan.actividad")
registro_errores = logging.getLogger("myfittplan.errores")


def configurar_logs_de_archivo() -> None:
    """Ata los archivos `actividad.txt` y `errores.txt` a sus loggers.

    Es idempotente: si ya estan configurados no se vuelven a anadir manejadores (llamarla
    dos veces —p. ej. en local con `--reload`— no duplicaria lineas).
    """
    if registro_actividad.handlers:
        return

    ARCHIVO_ACTIVIDAD.parent.mkdir(parents=True, exist_ok=True)

    # Actividad: solo INFO; los ERROR/WARNING no deben colarse aqui.
    registro_actividad.setLevel(logging.INFO)
    manejador_actividad = logging.FileHandler(ARCHIVO_ACTIVIDAD, encoding="utf-8")
    manejador_actividad.setLevel(logging.INFO)
    manejador_actividad.setFormatter(logging.Formatter(_FORMATO_LINEA))
    manejador_actividad.addFilter(_SoloInfo())
    registro_actividad.addHandler(manejador_actividad)
    registro_actividad.propagate = False

    # Errores: toda severidad sobre WARNING, con detalle completo.
    registro_errores.setLevel(logging.WARNING)
    manejador_errores = logging.FileHandler(ARCHIVO_ERRORES, encoding="utf-8")
    manejador_errores.setLevel(logging.WARNING)
    manejador_errores.setFormatter(logging.Formatter(_FORMATO_DETALLE))
    registro_errores.addHandler(manejador_errores)
    registro_errores.propagate = False


class _SoloInfo(logging.Filter):
    """Deja pasar al archivo de actividad SOLO las lineas de nivel INFO.

    Si el logger estuviera simplemente a nivel INFO, los registros ERROR pasarian tambien
    (INFO y ERROR comparten nivel de corte); este filtro asegura que `actividad.txt` no
    lleve trazas de error encima de las lineas de peticion.
    """

    def filter(self, registro: logging.LogRecord) -> bool:
        return registro.levelno == logging.INFO


def ip_del_cliente(peticion: object) -> str:
    """IP real del cliente.

    Detras de nginx/proxy, `request.client.host` es la del proxy (127.0.0.1). La del visitante
    viaja en `X-Forwarded-For`, con la primera entrada como la mas cercana al cliente.
    """
    cabeceras = getattr(peticion, "headers", None)
    if cabeceras is not None and "x-forwarded-for" in cabeceras:
        primero: str = cabeceras["x-forwarded-for"].split(",")[0].strip()
        if primero:
            return primero
    cliente = getattr(peticion, "client", None)
    if cliente is None:
        return "-"
    return str(cliente.host)


def etiqueta_actor(peticion: object) -> str:
    actor = getattr(getattr(peticion, "state", None), "actor", None)
    if actor is None:
        return "usuario=- coach=- rol=anonimo"
    return (
        f"usuario={actor.usuario_id} coach={actor.coach_id} "
        f"rol={getattr(actor, 'rol', '?')}"
    )


def registrar_actividad(mensaje: str) -> None:
    registro_actividad.info(mensaje)


def registrar_error(mensaje: str, *detalles: object, exc_info: bool = False) -> None:
    """Escribe en `logs/errores.txt`.

    Con `exc_info=True` el formato agrega la traza completa (pila) al detalle del nivel.
    """
    registro_errores.error(mensaje, *detalles, exc_info=exc_info)
