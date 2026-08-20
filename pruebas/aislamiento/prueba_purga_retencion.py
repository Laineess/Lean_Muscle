"""La purga respeta la primera y la última foto de cada ángulo.

Sin esas dos no hay comparativa: el «antes» vence antes que el «después», y a los cuatro
meses la alumna abre su evolución y le falta justo la mitad que da sentido a la otra.

Corre contra MySQL porque la decisión de qué se borra la toma una consulta con un `EXISTS`
correlacionado, no el código de Python: probarla con objetos en memoria comprobaría otra cosa.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.compartido.fechas import ahora_utc
from app.config import ajustes
from app.datos.alcance import motor
from app.datos.base import Base
from app.datos.modelos import Alumna, Chequeo, Ciclo, Coach, Foto, Usuario
from app.datos.sin_alcance import sesion_sin_alcance
from app.servicios.seguridad import hash_contrasena
from app.trabajos import purga

FECHA = date(2026, 1, 15)
ANGULOS = ("frontal", "perfil", "espalda")
CHEQUEOS = 5


#: Un mes más allá del plazo, para que la más reciente de la serie también esté vencida.
#: Si alguna cayera dentro del plazo sobreviviría por nueva y no por ser la última, que es
#: justo lo que estas pruebas tienen que distinguir.
def _vencida(atras: int) -> datetime:
    plazo = timedelta(days=ajustes().retencion_fotos_meses * 30)
    return ahora_utc() - plazo - timedelta(days=30 + atras * 30)


@dataclass(frozen=True, slots=True)
class Vista:
    """Lo que interesa de una foto, ya fuera de la sesión."""

    angulo: str
    es_linea_base: bool
    tiene_imagen: bool
    purgada: bool
    tomada_en: datetime


def _alumna(s: Session, etiqueta: str) -> tuple[int, int, int]:
    coach = Coach(nombre=f"Coach {etiqueta}", slug=etiqueta, email=f"{etiqueta}@ejemplo.mx")
    s.add(coach)
    s.flush()

    usuario = Usuario(
        coach_id=coach.id,
        rol="alumna",
        email=f"alumna-{etiqueta}@ejemplo.mx",
        hash_contrasena=hash_contrasena("x"),
    )
    s.add(usuario)
    s.flush()

    alumna = Alumna(
        coach_id=coach.id,
        usuario_id=usuario.id,
        nombre=f"Alumna de {etiqueta}",
        fecha_nacimiento=date(1994, 3, 22),
        estatura_cm=165,
    )
    s.add(alumna)
    s.flush()

    ciclo = Ciclo(
        coach_id=coach.id,
        alumna_id=alumna.id,
        numero=1,
        inicia_en=FECHA,
        termina_en=FECHA + timedelta(days=30),
        precio=Decimal("1200.00"),
    )
    s.add(ciclo)
    s.flush()
    return int(coach.id), int(alumna.id), int(ciclo.id)


def _chequeo(
    s: Session, ids: tuple[int, int, int], i: int, tomada: datetime, angulos: tuple[str, ...]
) -> None:
    coach_id, alumna_id, ciclo_id = ids
    chequeo = Chequeo(
        coach_id=coach_id,
        alumna_id=alumna_id,
        ciclo_id=ciclo_id,
        fecha=FECHA + timedelta(days=i * 30),
        estado="validado",
    )
    s.add(chequeo)
    s.flush()
    for angulo in angulos:
        s.add(
            Foto(
                coach_id=coach_id,
                chequeo_id=chequeo.id,
                angulo=angulo,
                storage_key=f"coach/{coach_id}/{chequeo.id}-{angulo}.webp",
                # La primera de cada ángulo se marca al subirla, como en producción.
                es_linea_base=i == 0,
                tomada_en=tomada,
                subida_en=tomada,
            )
        )


@pytest.fixture(scope="module")
def tras_la_purga() -> Iterator[tuple[list[Vista], list[Vista]]]:
    """Dos alumnas de dos coaches: una con cinco chequeos vencidos y otra con uno solo."""
    try:
        maquina = motor()
        with maquina.connect():
            pass
    except OperationalError as exc:  # pragma: no cover - depende del entorno
        pytest.skip(f"sin MySQL disponible: {exc}")

    Base.metadata.drop_all(maquina)
    Base.metadata.create_all(maquina)

    with Session(maquina) as s:
        serie = _alumna(s, "serie")
        for i in range(CHEQUEOS):
            _chequeo(s, serie, i, _vencida(CHEQUEOS - 1 - i), ANGULOS)

        sola = _alumna(s, "sola")
        _chequeo(s, sola, 0, _vencida(0), ("frontal",))
        s.commit()
        coach_serie, coach_sola = serie[0], sola[0]

    purga.correr()

    # Se lee a datos planos y se cierra: dejar la sesión abierta mientras corre el `drop_all`
    # del cierre traba la base contra sus propios candados de metadatos.
    with sesion_sin_alcance("lectura de prueba, cruza inquilinos") as s:
        vistas: dict[int, list[Vista]] = {coach_serie: [], coach_sola: []}
        for f in s.scalars(select(Foto).order_by(Foto.tomada_en)).all():
            vistas[f.coach_id].append(
                Vista(
                    angulo=f.angulo,
                    es_linea_base=f.es_linea_base,
                    tiene_imagen=f.storage_key is not None,
                    purgada=f.purgada_en is not None,
                    tomada_en=f.tomada_en or ahora_utc(),
                )
            )

    yield vistas[coach_serie], vistas[coach_sola]
    Base.metadata.drop_all(maquina)


def _por_angulo(fotos: list[Vista], angulo: str) -> list[Vista]:
    return sorted((f for f in fotos if f.angulo == angulo), key=lambda f: f.tomada_en)


class TestLaPrimeraYLaUltimaSobreviven:
    def test_de_quince_imagenes_quedan_seis(
        self, tras_la_purga: tuple[list[Vista], list[Vista]]
    ) -> None:
        serie, _ = tras_la_purga
        assert len(serie) == CHEQUEOS * len(ANGULOS)
        assert sum(1 for f in serie if f.tiene_imagen) == 2 * len(ANGULOS)

    def test_la_primera_de_cada_angulo_conserva_su_imagen(
        self, tras_la_purga: tuple[list[Vista], list[Vista]]
    ) -> None:
        serie, _ = tras_la_purga
        primeras = [f for f in serie if f.es_linea_base]
        assert len(primeras) == len(ANGULOS)
        assert all(f.tiene_imagen and not f.purgada for f in primeras)

    def test_la_ultima_de_cada_angulo_conserva_su_imagen(
        self, tras_la_purga: tuple[list[Vista], list[Vista]]
    ) -> None:
        serie, _ = tras_la_purga
        for angulo in ANGULOS:
            ultima = _por_angulo(serie, angulo)[-1]
            assert ultima.tiene_imagen and not ultima.purgada

    def test_las_de_en_medio_se_borran_y_dejan_constancia(
        self, tras_la_purga: tuple[list[Vista], list[Vista]]
    ) -> None:
        serie, _ = tras_la_purga
        for angulo in ANGULOS:
            enmedio = _por_angulo(serie, angulo)[1:-1]
            assert len(enmedio) == CHEQUEOS - 2
            for f in enmedio:
                # La fila sobrevive a la imagen: la bitácora tiene que decir que existió.
                assert not f.tiene_imagen
                assert f.purgada

    def test_con_un_solo_chequeo_no_se_borra_nada(
        self, tras_la_purga: tuple[list[Vista], list[Vista]]
    ) -> None:
        """Su única foto es a la vez la primera y la última: no hay «de en medio»."""
        _, sola = tras_la_purga
        assert len(sola) == 1
        assert sola[0].tiene_imagen and not sola[0].purgada
