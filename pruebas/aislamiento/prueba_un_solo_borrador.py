"""Abrir el chequeo dos veces a la vez no crea dos borradores.

No es un caso rebuscado: el doble montaje de React en desarrollo lanza el POST de apertura
dos veces en cada carga de la pantalla. Con dos borradores del mismo ciclo —y la misma
fecha— cada petición podía quedarse con uno distinto: la alumna guardaba sus medidas en uno,
subía las fotos al otro, y al enviar el servidor miraba el que estaba vacío. En pantalla se
veía todo completo y el error decía que faltaba todo menos las fotos.

Corre contra MySQL porque lo que se prueba es el candado de fila, que en memoria no existe.
"""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.compartido.fechas import ahora_utc, dia_calendario
from app.datos.alcance import motor, sesion_con_alcance
from app.datos.base import Base
from app.datos.modelos import Alumna, Chequeo, Ciclo, Cita, Coach, Consentimiento, Usuario
from app.dominio.agenda import EstadoCita, Modalidad, TipoCita
from app.rutas import api_chequeo
from app.rutas.sesion import Actor
from app.servicios.seguridad import hash_contrasena


@pytest.fixture
def alumna_lista() -> Iterator[Actor]:
    try:
        maquina = motor()
        with maquina.connect():
            pass
    except OperationalError as exc:  # pragma: no cover - depende del entorno
        pytest.skip(f"sin MySQL disponible: {exc}")

    Base.metadata.drop_all(maquina)
    Base.metadata.create_all(maquina)

    with Session(maquina) as s:
        coach = Coach(nombre="Mariana", slug="m", email="m@ejemplo.mx")
        s.add(coach)
        s.flush()
        usuario = Usuario(
            coach_id=coach.id,
            rol="alumna",
            email="a@ejemplo.mx",
            hash_contrasena=hash_contrasena("x"),
        )
        s.add(usuario)
        s.flush()
        alumna = Alumna(
            coach_id=coach.id,
            usuario_id=usuario.id,
            nombre="Carlos",
            fecha_nacimiento=date(1994, 3, 22),
            estatura_cm=178,
            cuestionario_completo=True,
            estado="activa",
        )
        s.add(alumna)
        s.flush()

        hoy = dia_calendario(ahora_utc(), alumna.zona_horaria)
        s.add(
            Ciclo(
                coach_id=coach.id,
                alumna_id=alumna.id,
                numero=1,
                inicia_en=hoy,
                termina_en=hoy + timedelta(days=30),
                precio=Decimal(0),
            )
        )
        ahora = ahora_utc()
        # Sin consulta del ciclo el chequeo ni siquiera abre.
        s.add(
            Cita(
                coach_id=coach.id,
                alumna_id=alumna.id,
                titulo="Consulta",
                tipo=TipoCita.CONSULTA.value,
                modalidad=Modalidad.PRESENCIAL.value,
                estado=EstadoCita.CONFIRMADA.value,
                inicia_en=ahora,
                termina_en=ahora + timedelta(minutes=60),
            )
        )
        s.add(
            Consentimiento(
                coach_id=coach.id,
                alumna_id=alumna.id,
                tipo="protocolo_foto",
                version_texto="1",
                texto_hash="x" * 64,
                aceptado_en=ahora,
            )
        )
        actor = Actor(usuario_id=int(usuario.id), coach_id=int(coach.id), rol="alumna")
        s.commit()

    yield actor
    Base.metadata.drop_all(maquina)


def _abrir(actor: Actor) -> str:
    with sesion_con_alcance(actor.coach_id) as s:
        return api_chequeo.abrir_chequeo(actor, s).ulid


def _cuantos(actor: Actor) -> int:
    with sesion_con_alcance(actor.coach_id) as s:
        return s.scalars(select(func.count()).select_from(Chequeo)).one()


class TestAbrirDosVeces:
    def test_seguidas_devuelven_el_mismo(self, alumna_lista: Actor) -> None:
        assert _abrir(alumna_lista) == _abrir(alumna_lista)
        assert _cuantos(alumna_lista) == 1

    def test_a_la_vez_tampoco_crean_dos(self, alumna_lista: Actor) -> None:
        # Es lo que hace el doble montaje de React: dos POST solapados, no seguidos.
        with ThreadPoolExecutor(max_workers=2) as pool:
            ulids = list(pool.map(lambda _: _abrir(alumna_lista), range(2)))

        assert _cuantos(alumna_lista) == 1
        assert ulids[0] == ulids[1]

    def test_cuatro_a_la_vez_siguen_siendo_uno(self, alumna_lista: Actor) -> None:
        with ThreadPoolExecutor(max_workers=4) as pool:
            ulids = list(pool.map(lambda _: _abrir(alumna_lista), range(4)))

        assert _cuantos(alumna_lista) == 1
        assert len(set(ulids)) == 1


class TestElDesempateEsEstable:
    def test_con_dos_borradores_del_mismo_dia_siempre_sale_el_mismo(
        self, alumna_lista: Actor
    ) -> None:
        """Los que ya quedaron duplicados de antes tienen que resolverse igual siempre.

        Sin desempate por `id`, dos filas con la misma fecha las ordena el motor como
        quiere, y cada petición se llevaba una distinta.
        """
        from app.datos.repos import consultas as q

        with sesion_con_alcance(alumna_lista.coach_id) as s:
            alumna = s.scalars(select(Alumna)).one()
            ciclo = s.scalars(select(Ciclo)).one()
            hoy = dia_calendario(ahora_utc(), alumna.zona_horaria)
            for _ in range(2):
                s.add(
                    Chequeo(
                        coach_id=alumna_lista.coach_id,
                        alumna_id=alumna.id,
                        ciclo_id=ciclo.id,
                        fecha=hoy,
                        estado="borrador",
                    )
                )

        vistos = set()
        for _ in range(6):
            with sesion_con_alcance(alumna_lista.coach_id) as s:
                alumna = s.scalars(select(Alumna)).one()
                ciclo = s.scalars(select(Ciclo)).one()
                borrador = q.borrador_de(s, alumna.id, ciclo.id)
                assert borrador is not None
                vistos.add(borrador.ulid)

        assert len(vistos) == 1
