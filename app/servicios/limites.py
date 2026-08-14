"""Freno a la fuerza bruta en el acceso.

Una contraseña de diez caracteres no sirve de nada si se pueden probar diez mil por minuto.
Aquí se cuentan los intentos fallidos y se corta cuando pasan del límite, por dos vías a la
vez:

- **Por correo**, que es lo que frena a quien ataca una cuenta concreta.
- **Por IP**, que es lo que frena a quien recorre una lista de correos.

El conteo vive en la base y no en memoria porque uvicorn corre varios procesos: un contador
por proceso multiplicaría el límite por el número de procesos.

**El bloqueo no distingue si el correo existe.** Responder distinto a un correo dado de alta
y a uno inventado convierte el propio bloqueo en un directorio de clientas.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.compartido.fechas import ahora_utc
from app.datos.modelos import IntentoDeAcceso

#: Ventana en la que se cuentan los fallos. Corta pero suficiente: quien se equivoca dos
#: veces escribiendo espera un minuto; quien prueba mil contraseñas, no llega a la décima.
VENTANA = timedelta(minutes=15)

#: Fallos por correo antes de cerrar. Cinco deja margen a un dedo torpe.
LIMITE_POR_CORREO = 5

#: Fallos por IP. Más alto porque una casa o un gimnasio comparten salida a internet y
#: varias alumnas pueden equivocarse el mismo día.
LIMITE_POR_IP = 20

#: Cuánto se conservan los intentos. Pasado eso son ruido: el bloqueo ya caducó y el dato
#: solo sirve para ocupar espacio.
RETENCION = timedelta(days=30)


def _contar(s: Session, campo: Any, valor: str, desde: datetime) -> int:
    total = s.scalar(
        select(func.count())
        .select_from(IntentoDeAcceso)
        .where(
            campo == valor,
            IntentoDeAcceso.exitoso.is_(False),
            IntentoDeAcceso.creado_en >= desde,
        )
        .execution_options(sin_alcance=True)
    )
    return int(total or 0)


def bloqueado(s: Session, correo: str, ip: str | None) -> bool:
    """Si este correo o esta IP ya agotaron sus intentos en la ventana."""
    desde = ahora_utc() - VENTANA

    if _contar(s, IntentoDeAcceso.correo, correo, desde) >= LIMITE_POR_CORREO:
        return True
    if ip and _contar(s, IntentoDeAcceso.ip, ip, desde) >= LIMITE_POR_IP:
        return True
    return False


def registrar(s: Session, correo: str, ip: str | None, exitoso: bool) -> None:
    """Deja constancia del intento. Un acierto limpia el contador de ese correo.

    Limpiarlo importa: si no, quien se equivoca cuatro veces y acierta a la quinta se queda
    con el bloqueo a un fallo de distancia durante el resto de la ventana.
    """
    s.add(
        IntentoDeAcceso(
            correo=correo[:180],
            ip=ip[:45] if ip else None,
            exitoso=exitoso,
        )
    )

    if exitoso:
        for fila in s.scalars(
            select(IntentoDeAcceso)
            .where(
                IntentoDeAcceso.correo == correo,
                IntentoDeAcceso.exitoso.is_(False),
                IntentoDeAcceso.creado_en >= ahora_utc() - VENTANA,
            )
            .execution_options(sin_alcance=True)
        ):
            s.delete(fila)


def purgar(s: Session) -> int:
    """Borra los intentos viejos. Lo llama el trabajo de mantenimiento diario."""
    viejos = list(
        s.scalars(
            select(IntentoDeAcceso)
            .where(IntentoDeAcceso.creado_en < ahora_utc() - RETENCION)
            .execution_options(sin_alcance=True)
        )
    )
    for fila in viejos:
        s.delete(fila)
    return len(viejos)
