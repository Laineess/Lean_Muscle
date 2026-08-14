"""Trabajador que envía los avisos encolados.

Corre aparte de la petición: si el servidor de correo tarda o falla, nadie se queda mirando
una pantalla congelada, y un alta no se pierde porque el correo no salió.

Reintenta con tope. Un aviso que falla cinco veces se marca y se deja de intentar: seguir
reintentando contra un correo inexistente solo quema reputación de envío.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from app.compartido.fechas import ahora_utc
from app.datos.modelos import AvisoEnviado
from app.datos.sin_alcance import sesion_sin_alcance
from app.dominio.avisos import Aviso, lleva_adjunto
from app.servicios.correo import Adjunto, Correo, emisor
from app.servicios.plantillas_correo import redactar

MAX_INTENTOS = 5
#: Cuántos se toman por corrida. Con espaciado de 1.5 s, un lote de 40 tarda un minuto.
LOTE = 40


@dataclass(frozen=True, slots=True)
class Resultado:
    enviados: int
    fallidos: int
    agotados: int


def _adjuntos_de(aviso: Aviso, contexto: dict[str, object]) -> list[Adjunto]:
    """Genera el PDF que acompaña al aviso, si lleva uno.

    Se genera al enviar y no al encolar: un recibo pesa, y guardarlo en la cola multiplicaría
    el tamaño de la tabla por nada.
    """
    if not lleva_adjunto(aviso):
        return []

    from decimal import Decimal

    from app.servicios import pdf

    if aviso is Aviso.PAGO_VALIDADO:
        from datetime import date

        def _fecha(clave: str) -> date:
            return date.fromisoformat(str(contexto[clave]))

        documento = pdf.recibo(
            folio=str(contexto["folio"]),
            alumna=str(contexto["alumna"]),
            coach=str(contexto["coach"]),
            ciclo=int(str(contexto["ciclo"])),
            monto=Decimal(str(contexto["monto_numero"])),
            metodo=str(contexto["metodo"]),
            pagado_el=_fecha("pagado_el"),
            vigencia_inicia=_fecha("vigencia_inicia"),
            vigencia_termina=_fecha("vigencia_termina"),
        )
        return [Adjunto(nombre=documento.nombre, contenido=documento.contenido)]

    return []


def enviar_pendientes(lote: int = LOTE) -> Resultado:
    enviados = fallidos = agotados = 0

    with sesion_sin_alcance("envío de avisos encolados; cruza inquilinos") as s:
        pendientes = list(
            s.scalars(
                select(AvisoEnviado)
                .where(
                    AvisoEnviado.enviado_en.is_(None),
                    AvisoEnviado.intentos < MAX_INTENTOS,
                    AvisoEnviado.canal == "correo",
                )
                .order_by(AvisoEnviado.creado_en)
                .limit(lote)
            ).all()
        )

        for fila in pendientes:
            fila.intentos += 1
            try:
                aviso = Aviso(fila.tipo)
                asunto, texto, html = redactar(aviso, dict(fila.contexto))
                emisor().enviar(
                    Correo(
                        para=fila.destinatario_correo,
                        asunto=asunto,
                        cuerpo_texto=texto,
                        cuerpo_html=html,
                        adjuntos=_adjuntos_de(aviso, dict(fila.contexto)),
                    )
                )
                fila.enviado_en = ahora_utc()
                fila.error = None
                enviados += 1
            except Exception as causa:
                fila.error = f"{type(causa).__name__}: {causa}"[:500]
                fallidos += 1
                if fila.intentos >= MAX_INTENTOS:
                    agotados += 1

    return Resultado(enviados=enviados, fallidos=fallidos, agotados=agotados)


def enviar_push_pendientes(lote: int = LOTE) -> Resultado:
    """Envía los avisos encolados en el canal push.

    Va aparte del correo porque falla distinto: aquí un fallo no es «el servidor tardó», es
    **«ese navegador ya no existe»**. Cuando el servicio responde 404 o 410 se borra la
    suscripción en lugar de reintentarla; insistir contra un teléfono que se formateó no la
    va a revivir.

    Un destinatario sin suscripciones no es un error: nunca activó las notificaciones. El
    aviso se marca como enviado para que no se quede reintentando eternamente.
    """
    from app.datos.modelos import SuscripcionPush
    from app.servicios import push

    enviados = fallidos = agotados = 0

    with sesion_sin_alcance("envío de notificaciones push; cruza inquilinos") as s:
        pendientes = list(
            s.scalars(
                select(AvisoEnviado)
                .where(
                    AvisoEnviado.enviado_en.is_(None),
                    AvisoEnviado.intentos < MAX_INTENTOS,
                    AvisoEnviado.canal == "push",
                )
                .order_by(AvisoEnviado.creado_en)
                .limit(lote)
            ).all()
        )

        for fila in pendientes:
            fila.intentos += 1

            if fila.destinatario_id is None:
                fila.error = "aviso push sin destinatario"
                fila.enviado_en = ahora_utc()
                continue

            suscripciones = list(
                s.scalars(
                    select(SuscripcionPush).where(
                        SuscripcionPush.usuario_id == fila.destinatario_id
                    )
                ).all()
            )
            if not suscripciones:
                # No activó las notificaciones. No hay nada que reintentar.
                fila.enviado_en = ahora_utc()
                fila.error = "sin suscripciones"
                continue

            try:
                notificacion = push.redactar(Aviso(fila.tipo), dict(fila.contexto))
            except (KeyError, IndexError) as causa:
                fila.error = f"{type(causa).__name__}: {causa}"[:500]
                fallidos += 1
                if fila.intentos >= MAX_INTENTOS:
                    agotados += 1
                continue

            alguna = False
            for suscripcion in suscripciones:
                resultado = push.emisor().enviar(
                    push.Suscripcion(
                        endpoint=suscripcion.endpoint,
                        p256dh=suscripcion.p256dh,
                        auth=suscripcion.auth,
                    ),
                    notificacion,
                )
                if resultado.entregada:
                    suscripcion.ultimo_envio_en = ahora_utc()
                    suscripcion.fallos = 0
                    alguna = True
                elif resultado.caducada:
                    s.delete(suscripcion)
                else:
                    suscripcion.fallos += 1

            if alguna:
                fila.enviado_en = ahora_utc()
                fila.error = None
                enviados += 1
            else:
                fila.error = "ninguna suscripción aceptó el envío"
                fallidos += 1
                if fila.intentos >= MAX_INTENTOS:
                    agotados += 1

    return Resultado(enviados=enviados, fallidos=fallidos, agotados=agotados)


def main() -> None:  # pragma: no cover - punto de entrada del timer de systemd
    r = enviar_pendientes()
    p = enviar_push_pendientes()
    print(f"correo: enviados={r.enviados} fallidos={r.fallidos} agotados={r.agotados}")
    print(f"push:   enviados={p.enviados} fallidos={p.fallidos} agotados={p.agotados}")


if __name__ == "__main__":  # pragma: no cover
    main()
