"""La prueba que sustituye al Row Level Security que MySQL no tiene.

Siembra dos coaches, ejecuta cada lectura con la sesion de la coach A y falla si aparece un
solo registro de la B. Una funcion de repositorio nueva sin su prueba de aislamiento no
pasa el CI, y **la fase 2 no empieza hasta que esta bateria este en verde**.

Requiere MySQL. Se salta sola si no hay base disponible, para que el resto de la bateria
siga corriendo en una maquina limpia.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.compartido.errores import SinAlcanceDeInquilino
from app.datos.alcance import alcance_actual, crear_motor, motor, sesion_con_alcance
from app.datos.base import Base
from app.datos.modelos import Alumna, Coach, Usuario
from app.servicios.seguridad import hash_contrasena

pytestmark = [pytest.mark.integracion, pytest.mark.aislamiento]


@pytest.fixture(scope="module")
def base_lista() -> Iterator[dict[str, int]]:
    try:
        maquina = motor()
        with maquina.connect():
            pass
    except OperationalError as exc:  # pragma: no cover - depende del entorno
        pytest.skip(f"sin MySQL disponible: {exc}")

    Base.metadata.drop_all(maquina)
    Base.metadata.create_all(maquina)

    ids: dict[str, int] = {}
    with Session(maquina) as s:
        for etiqueta, nombre in (("a", "Coach A"), ("b", "Coach B")):
            coach = Coach(nombre=nombre, slug=etiqueta, email=f"{etiqueta}@ejemplo.mx")
            s.add(coach)
            s.flush()
            ids[etiqueta] = coach.id

            usuario = Usuario(
                coach_id=coach.id,
                rol="alumna",
                email=f"alumna-{etiqueta}@ejemplo.mx",
                hash_contrasena=hash_contrasena("x"),
            )
            s.add(usuario)
            s.flush()

            s.add(
                Alumna(
                    coach_id=coach.id,
                    usuario_id=usuario.id,
                    nombre=f"Alumna de {nombre}",
                    fecha_nacimiento=date(1994, 3, 22),
                )
            )
        s.commit()

    yield ids
    Base.metadata.drop_all(maquina)


def test_una_coach_solo_ve_sus_alumnas(base_lista: dict[str, int]) -> None:
    with sesion_con_alcance(base_lista["a"]) as s:
        alumnas = s.scalars(select(Alumna)).all()
    assert len(alumnas) == 1
    assert alumnas[0].coach_id == base_lista["a"]


def test_pedir_por_id_una_alumna_ajena_no_devuelve_nada(base_lista: dict[str, int]) -> None:
    with sesion_con_alcance(base_lista["b"]) as s:
        ajena = s.scalars(select(Alumna).where(Alumna.coach_id == base_lista["a"])).all()
    # El filtro de alcance se compone con el WHERE del programador: A and B = imposible.
    assert ajena == []


def test_leer_sin_alcance_falla_ruidoso() -> None:
    ficha = alcance_actual.set(None)
    try:
        with pytest.raises(SinAlcanceDeInquilino):
            with Session(motor()) as s:
                s.scalars(select(Alumna)).all()
    finally:
        alcance_actual.reset(ficha)


def test_la_variable_del_inquilino_no_sobrevive_al_pool(base_lista: dict[str, int]) -> None:
    """`@app_coach_id` vive en la conexion y el pool la reutiliza.

    Si el envoltorio olvidara limpiarla, la siguiente peticion heredaria el inquilino de la
    anterior — la fuga mas dificil de ver, porque solo aparece bajo concurrencia.
    """
    from sqlalchemy import text

    with sesion_con_alcance(base_lista["a"]):
        pass

    # Una conexion cruda del mismo pool no debe traer valor heredado.
    with crear_motor().connect() as conexion:
        heredado = conexion.execute(text("SELECT @app_coach_id")).scalar()
    assert heredado is None
