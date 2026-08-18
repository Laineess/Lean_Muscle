"""Borrado de lo que vence. Corre cada media hora.

Tres plazos y ninguno es decorativo:

- **Fotos de comida: 36 horas.** Es lo que hace razonable pedirle a alguien que fotografíe
  lo que come.
- **Fotos de chequeo: cuatro meses.** Es lo que dice el aviso de privacidad.
- **Avisos de la coach: en cuanto los leen, o a los 7 días.** Son frases de ánimo; guardarlas
  para siempre sería archivar lo que nació para durar un día.

Con las fotos **la fila no se borra, la imagen sí**: `purgada_en` queda con la fecha, porque
la bitácora tiene que poder decir que esa foto existió. Con los avisos se borra todo: no hay
nada de qué dejar constancia.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.compartido.fechas import ahora_utc
from app.config import ajustes
from app.datos.modelos import Anuncio, AvisoEnviado, Foto, FotoDeComida, Notificacion
from app.datos.sin_alcance import sesion_sin_alcance
from app.dominio.fotos_de_comida import VIGENCIA
from app.servicios.almacenamiento import almacen

#: Cuántas se borran por corrida. Un tope evita que una purga atrasada monopolice el disco
#: durante minutos; lo que quede sale en la corrida siguiente, media hora después.
LOTE = 500

#: Techo de un aviso de la coach. Si a la semana sigue sin abrirse, ya no se va a abrir.
VIDA_DEL_AVISO = timedelta(days=7)

#: Cuánto se guarda la cola una vez despachada. Su única función es no mandar dos veces lo
#: mismo, y toda llave lleva dentro el identificador del hecho que la disparó: pasado el
#: plazo no hay nada que repetir, y sí un correo de alguien que quizá ya se dio de baja.
RETENCION_DE_LA_COLA = timedelta(days=90)


@dataclass(frozen=True, slots=True)
class Resultado:
    comidas: int
    chequeos: int
    avisos: int

    @property
    def total(self) -> int:
        return self.comidas + self.chequeos + self.avisos


def _borrar(llave: str | None) -> None:
    """Borra el archivo. Que ya no esté no es un error: el objetivo era justo ese."""
    if not llave:
        return
    try:
        almacen().borrar(llave)
    except Exception:  # pragma: no cover - un archivo ilegible no debe frenar la purga
        pass


def _avisos_gastados(s: Session, ahora: datetime) -> int:
    """Borra los avisos que ya cumplieron: los leyeron todas, o pasó la semana.

    Se borra el anuncio entero, no fila por fila. Si sobrevivieran las copias leídas, la
    coach seguiría viendo el aviso en su historial como si le quedara algo por hacer.
    """
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
        consulta = select(Foto).where(
            Foto.purgada_en.is_(None),
            Foto.storage_key.is_not(None),
            Foto.tomada_en <= limite_chequeos,
        )
        # La de línea base se conserva si la alumna lo pidió: es la única foto que tiene
        # sentido guardar más allá del plazo, y solo con su permiso.
        if ajustes().conservar_foto_linea_base:
            consulta = consulta.where(Foto.es_linea_base.is_(False))

        for vieja in s.scalars(consulta.limit(LOTE)).all():
            llave = vieja.storage_key
            _borrar(llave)
            if llave:
                _borrar(llave.replace(".webp", "-mini.webp"))
            vieja.storage_key = None
            vieja.purgada_en = ahora
            chequeos += 1

        avisos = _avisos_gastados(s, ahora) + _cola_despachada(s, ahora)

    return Resultado(comidas=comidas, chequeos=chequeos, avisos=avisos)


def main() -> None:  # pragma: no cover - punto de entrada del timer de systemd
    r = correr()
    print(f"purgadas={r.total} comidas={r.comidas} chequeos={r.chequeos} avisos={r.avisos}")


if __name__ == "__main__":  # pragma: no cover
    main()
