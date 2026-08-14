"""Borrado de imágenes vencidas. Corre cada media hora.

Dos plazos distintos y ninguno es decorativo:

- **Fotos de comida: 36 horas.** Es lo que hace razonable pedirle a alguien que fotografíe
  lo que come.
- **Fotos de chequeo: cuatro meses.** Es lo que dice el aviso de privacidad.

Hasta ahora el trabajo diario *avisaba* de la purga de chequeos quince días antes y nadie
borraba nada: la fila se quedaba con su `storage_key` y el archivo en disco para siempre.
Una promesa de borrado que no se cumple es peor que no haberla hecho, porque el aviso de
privacidad la pone por escrito.

**La fila no se borra, la imagen sí.** `purgada_en` queda con la fecha: la bitácora tiene
que poder decir que esa foto existió y cuándo dejó de existir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select

from app.compartido.fechas import ahora_utc
from app.config import ajustes
from app.datos.modelos import Foto, FotoDeComida
from app.datos.sin_alcance import sesion_sin_alcance
from app.dominio.fotos_de_comida import VIGENCIA
from app.servicios.almacenamiento import almacen

#: Cuántas se borran por corrida. Un tope evita que una purga atrasada monopolice el disco
#: durante minutos; lo que quede sale en la corrida siguiente, media hora después.
LOTE = 500


@dataclass(frozen=True, slots=True)
class Resultado:
    comidas: int
    chequeos: int

    @property
    def total(self) -> int:
        return self.comidas + self.chequeos


def _borrar(llave: str | None) -> None:
    """Borra el archivo. Que ya no esté no es un error: el objetivo era justo ese."""
    if not llave:
        return
    try:
        almacen().borrar(llave)
    except Exception:  # pragma: no cover - un archivo ilegible no debe frenar la purga
        pass


def correr() -> Resultado:
    ahora = ahora_utc()
    comidas = chequeos = 0

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

    return Resultado(comidas=comidas, chequeos=chequeos)


def main() -> None:  # pragma: no cover - punto de entrada del timer de systemd
    r = correr()
    print(f"purgadas={r.total} comidas={r.comidas} chequeos={r.chequeos}")


if __name__ == "__main__":  # pragma: no cover
    main()
