"""Encolado de avisos: el unico sitio donde se pone una fila en la cola.

**La llave lleva el canal.** `aviso_enviado` tiene UNIQUE (coach_id, llave), asi que un
aviso que sale por correo y por push necesita dos llaves o la segunda revienta la
transaccion. Era el caso de `PAGO_VENCIDO` y `PURGA_PROXIMA`, y tumbaba la corrida diaria
entera de recordatorios.

Encolar no envia: eso lo hace `app/trabajos/emisor_avisos.py`, fuera de la peticion.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.datos.modelos import AvisoEnviado
from app.dominio.avisos import Aviso, Canal, canales_de

#: `aviso_enviado.llave` es VARCHAR(160).
LARGO_LLAVE = 160


def llave_de_canal(llave: str, canal: Canal) -> str:
    """La llave del disparo, distinguida por canal.

    Se recorta por la izquierda si hace falta: lo que identifica el disparo está al final
    (`cita:{ulid}:recordatorio`), así que perder el prefijo es menos malo que perder el
    sufijo, y en la práctica ninguna llave se acerca al límite.
    """
    sufijo = f":{canal.value}"
    return llave[: LARGO_LLAVE - len(sufijo)] + sufijo


def encolar(
    s: Session,
    aviso: Aviso,
    *,
    coach_id: int,
    llave: str,
    para: str,
    contexto: dict[str, object],
    destinatario_id: int | None = None,
    canales: Iterable[Canal] | None = None,
) -> int:
    """Deja el aviso encolado en cada uno de sus canales. Devuelve cuántas filas insertó.

    El destinatario y el contexto se **copian aquí**, no se resuelven al enviar: si la alumna
    cambia de correo entre el alta y el envío, la invitación tiene que llegar a donde se dijo
    que llegaría.

    Un disparo ya encolado no se vuelve a encolar: es lo que hace que dos corridas del trabajo
    diario no manden el mismo recordatorio dos veces.
    """
    elegidos = list(canales) if canales is not None else sorted(canales_de(aviso))
    llaves = {canal: llave_de_canal(llave, canal) for canal in elegidos}
    if not llaves:
        return 0

    # El `coach_id` va explícito, contra la costumbre del resto del código: esta función
    # también corre desde el trabajo diario, que usa una sesión sin alcance para cruzar
    # inquilinos. Sin el filtro, la llave de una coach taparía el aviso de otra.
    ya = set(
        s.scalars(
            select(AvisoEnviado.llave).where(
                AvisoEnviado.coach_id == coach_id,
                AvisoEnviado.llave.in_(list(llaves.values())),
            )
        ).all()
    )

    insertadas = 0
    for canal, llave_canal in llaves.items():
        if llave_canal in ya:
            continue
        s.add(
            AvisoEnviado(
                coach_id=coach_id,
                destinatario_id=destinatario_id,
                destinatario_correo=para,
                tipo=aviso.value,
                llave=llave_canal,
                canal=canal.value,
                contexto=dict(contexto),
            )
        )
        insertadas += 1

    return insertadas
