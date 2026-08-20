"""Borrado de lo que vence. Corre cada media hora.

Tres plazos y ninguno es decorativo:

- **Fotos de comida: 36 horas.** Es lo que hace razonable pedirle a alguien que fotografíe
  lo que come.
- **Fotos de chequeo: cuatro meses**, salvo la primera y la última de cada ángulo, que se
  quedan. Sin esas dos no hay comparativa: el antes desaparece antes que el después, y a los
  cuatro meses la alumna se queda mirando su progreso contra un hueco.
- **Avisos de la coach: en cuanto los leen, o a los 7 días.** Son frases de ánimo; guardarlas
  para siempre sería archivar lo que nació para durar un día.
- **Registros a medias: 7 días.** Quien empezó y no terminó no dejó una cuenta: dejó nombre,
  correo y fecha de nacimiento. Se borra todo, con recordatorio dos días antes.
- **Expedientes de bajas: 15 días.** La alumna tuvo ese plazo para descargar lo suyo. Se
  borra todo menos la ficha vacía, que sostiene los consentimientos y los movimientos.
- **Imágenes de comprobantes: 12 meses.** Es lo que más pesa por alumna después de las fotos.
  Aquí también se borra la imagen y no la fila: el monto, la fecha y lo que leyó el OCR son
  la contabilidad, y esa no se purga.

Con las fotos **la fila no se borra, la imagen sí**: `purgada_en` queda con la fecha, porque
la bitácora tiene que poder decir que esa foto existió. Con los avisos se borra todo: no hay
nada de qué dejar constancia.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import Exists, delete, exists, select
from sqlalchemy.orm import Session, aliased

from app.compartido.fechas import ahora_utc
from app.config import ajustes
from app.datos.modelos import (
    Anuncio,
    AvisoEnviado,
    Chequeo,
    CobroProgramado,
    Foto,
    FotoDeComida,
    Notificacion,
)
from app.datos.sin_alcance import sesion_sin_alcance
from app.dominio.fotos_de_comida import VIGENCIA
from app.servicios import baja, registro
from app.servicios.almacenamiento import almacen

#: Cuántas se borran por corrida. Un tope evita que una purga atrasada monopolice el disco
#: durante minutos; lo que quede sale en la corrida siguiente, media hora después.
LOTE = 500

#: Techo de un aviso de la coach. Si a la semana sigue sin abrirse, ya no se va a abrir.
VIDA_DEL_AVISO = timedelta(days=7)

#: La cola solo evita repetir envíos, y cada llave lleva su hecho dentro: pasado el plazo
#: no hay nada que repetir, y sí correos de gente que quizá ya se dio de baja.
RETENCION_DE_LA_COLA = timedelta(days=90)


@dataclass(frozen=True, slots=True)
class Resultado:
    comidas: int
    chequeos: int
    avisos: int
    solicitudes: int = 0
    comprobantes: int = 0
    expedientes: int = 0

    @property
    def total(self) -> int:
        return (
            self.comidas
            + self.chequeos
            + self.avisos
            + self.solicitudes
            + self.comprobantes
            + self.expedientes
        )


def _borrar(llave: str | None) -> None:
    """Borra el archivo. Que ya no esté no es un error: el objetivo era justo ese."""
    if not llave:
        return
    try:
        almacen().borrar(llave)
    except Exception:  # pragma: no cover - un archivo ilegible no debe frenar la purga
        pass


def _hay_una_mas_nueva() -> Exists:
    """Verdadero si esta foto ya no es la última de su ángulo.

    La última no se marca en la fila porque deja de serlo sola: en cuanto entra un chequeo
    nuevo, la de antes pasa a ser una más. Se resuelve preguntando si existe otra posterior,
    que siempre da la respuesta de hoy y no la del día que se guardó.
    """
    otra = aliased(Foto)
    suyo = aliased(Chequeo)
    return exists(
        select(otra.id)
        .join(suyo, otra.chequeo_id == suyo.id)
        .where(
            suyo.alumna_id == Chequeo.alumna_id,
            otra.angulo == Foto.angulo,
            otra.storage_key.is_not(None),
            otra.tomada_en > Foto.tomada_en,
        )
    )


def _avisos_gastados(s: Session, ahora: datetime) -> int:
    """Los que ya cumplieron: los leyeron todas, o pasó la semana. Se borra el anuncio
    entero, o la coach lo seguiría viendo en su historial."""
    sin_leer = select(Notificacion.anuncio_id).where(
        Notificacion.anuncio_id.is_not(None), Notificacion.leida_en.is_(None)
    )
    gastados = list(
        s.scalars(
            select(Anuncio.id)
            .where(Anuncio.id.not_in(sin_leer) | (Anuncio.enviado_en <= ahora - VIDA_DEL_AVISO))
            .limit(LOTE)
        ).all()
    )
    if not gastados:
        return 0

    s.execute(delete(Notificacion).where(Notificacion.anuncio_id.in_(gastados)))
    s.execute(delete(Anuncio).where(Anuncio.id.in_(gastados)))
    return len(gastados)


def _cola_despachada(s: Session, ahora: datetime) -> int:
    """Tira lo que ya salió y lleva tiempo fuera. La cola no era un archivo histórico."""
    viejas = list(
        s.scalars(
            select(AvisoEnviado.id)
            .where(
                AvisoEnviado.enviado_en.is_not(None),
                AvisoEnviado.enviado_en <= ahora - RETENCION_DE_LA_COLA,
            )
            .limit(LOTE)
        ).all()
    )
    if viejas:
        s.execute(delete(AvisoEnviado).where(AvisoEnviado.id.in_(viejas)))
    return len(viejas)


def _registros_vencidos(s: Session, ahora: datetime) -> int:
    """Borra los registros que quedaron a medias o descartados, con cuenta y todo."""
    borradas = 0
    for solicitud in registro.borrables(s, ahora)[:LOTE]:
        registro.borrar(s, solicitud)
        borradas += 1
    return borradas


def _comprobantes_vencidos(s: Session, ahora: datetime) -> int:
    """Borra la imagen y deja la constancia de que existió.

    Se purgan aunque nadie los haya revisado: al año, un comprobante sin mirar no se va a
    mirar, y lo que sostiene el cobro es el monto de la fila, no la foto de la pantalla.
    """
    limite = ahora - timedelta(days=ajustes().retencion_comprobantes_meses * 30)
    vencidos = s.scalars(
        select(CobroProgramado)
        .where(
            CobroProgramado.comprobante_key.is_not(None),
            CobroProgramado.subido_en.is_not(None),
            CobroProgramado.subido_en <= limite,
        )
        .limit(LOTE)
    ).all()

    for cobro in vencidos:
        _borrar(cobro.comprobante_key)
        cobro.comprobante_key = None
        cobro.comprobante_purgado_en = ahora
    return len(vencidos)


def _expedientes_de_baja(s: Session, ahora: datetime) -> int:
    """Borra lo de quien se dio de baja hace más de quince días.

    Se cuenta desde la baja y no desde la última corrida: el plazo lo fija la fecha que se
    le prometió a la alumna, no la puntualidad del servidor.
    """
    borradas = 0
    for alumna in baja.vencidas(s, ahora)[:LOTE]:
        baja.borrar_expediente(s, alumna)
        borradas += 1
    return borradas


def correr() -> Resultado:
    ahora = ahora_utc()
    comidas = chequeos = avisos = 0

    # Cruza inquilinos a propósito: el plazo es el mismo para todas y recorrer coach por
    # coach multiplicaría las consultas sin cambiar el resultado.
    with sesion_sin_alcance("purga de imágenes vencidas, cruza inquilinos") as s:
        vencidas = s.scalars(
            select(FotoDeComida)
            .where(
                FotoDeComida.purgada_en.is_(None),
                FotoDeComida.subida_en <= ahora - VIGENCIA,
            )
            .limit(LOTE)
        ).all()

        for foto in vencidas:
            _borrar(foto.storage_key)
            foto.storage_key = None
            foto.purgada_en = ahora
            comidas += 1

        limite_chequeos = ahora - timedelta(days=ajustes().retencion_fotos_meses * 30)
        consulta = (
            select(Foto)
            .join(Chequeo, Foto.chequeo_id == Chequeo.id)
            .where(
                Foto.purgada_en.is_(None),
                Foto.storage_key.is_not(None),
                Foto.tomada_en <= limite_chequeos,
                Foto.es_linea_base.is_(False),
                _hay_una_mas_nueva(),
            )
        )

        for vieja in s.scalars(consulta.limit(LOTE)).all():
            llave = vieja.storage_key
            _borrar(llave)
            if llave:
                _borrar(llave.replace(".webp", "-mini.webp"))
            vieja.storage_key = None
            vieja.purgada_en = ahora
            chequeos += 1

        avisos = _avisos_gastados(s, ahora) + _cola_despachada(s, ahora)
        solicitudes = _registros_vencidos(s, ahora)
        comprobantes = _comprobantes_vencidos(s, ahora)
        expedientes = _expedientes_de_baja(s, ahora)

    return Resultado(
        comidas=comidas,
        chequeos=chequeos,
        avisos=avisos,
        solicitudes=solicitudes,
        comprobantes=comprobantes,
        expedientes=expedientes,
    )


def main() -> None:  # pragma: no cover - punto de entrada del timer de systemd
    r = correr()
    print(
        f"purgadas={r.total} comidas={r.comidas} chequeos={r.chequeos} "
        f"avisos={r.avisos} solicitudes={r.solicitudes} comprobantes={r.comprobantes} "
        f"expedientes={r.expedientes}"
    )


if __name__ == "__main__":  # pragma: no cover
    main()
