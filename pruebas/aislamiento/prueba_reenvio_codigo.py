"""Reenvío de código del registro abierto por HTTP, con la sesión de una alumna.

El resto de la registro se prueba sin base de datos; aquí se tira un `TestClient` contra la
app para comprobar que el endpoint `/api/mi/codigo/reenviar` atiende a una solicitud que
aún espera verificar el correo, y solo a esa. Nace para no regresar al bug que devolvía el
código en claro y que rompía el envío del correo.

Requiere MySQL igual que el resto de la batería de aislamiento: se salta sola si no hay.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.compartido.fechas import ahora_utc
from app.datos.alcance import motor, sesion_con_alcance
from app.datos.base import Base
from app.datos.modelos import Alumna, Coach, Sesion, SolicitudDeRegistro, Usuario
from app.dominio import registro as dom
from app.rutas import sesion as sas
from app.servicios.registro import _emitir_codigo
from app.servicios.seguridad import hash_contrasena, nuevo_token_de_sesion

pytestmark = pytest.mark.integracion


@pytest.fixture(scope="module")
def escenario() -> Iterator[dict[str, str]]:
    try:
        maquina = motor()
        with maquina.connect():
            pass
    except OperationalError as exc:  # pragma: no cover - depende del entorno
        pytest.skip(f"sin MySQL disponible: {exc}")

    Base.metadata.drop_all(maquina)
    Base.metadata.create_all(maquina)

    token, token_hash = nuevo_token_de_sesion()

    with Session(maquina) as s:
        coach = Coach(nombre="Coach A", slug="a", email="a@ejemplo.mx")
        s.add(coach)
        s.flush()

        usuario = Usuario(
            coach_id=coach.id,
            rol="alumna",
            email="alumna-a@ejemplo.mx",
            hash_contrasena=hash_contrasena("x"),
            debe_cambiar_contrasena=False,
        )
        s.add(usuario)
        s.flush()

        alumna = Alumna(
            coach_id=coach.id,
            usuario_id=usuario.id,
            nombre="Alumna de Coach A",
            fecha_nacimiento=date(1994, 3, 22),
            estado="solicitud",
        )
        s.add(alumna)
        s.flush()

        solicitud = SolicitudDeRegistro(
            coach_id=coach.id,
            alumna_id=alumna.id,
            estado=dom.Estado.SIN_VERIFICAR.value,
            codigo_hash="",
            codigo_vence_en=ahora_utc(),
        )
        _emitir_codigo(solicitud)
        # El código se emitió hace más que la espera entre reenvíos: se puede pedir uno nuevo.
        solicitud.codigo_vence_en = ahora_utc() + dom.CODIGO_VIVE - timedelta(seconds=61)
        s.add(solicitud)

        s.add(
            Sesion(
                coach_id=coach.id,
                usuario_id=usuario.id,
                token_hash=token_hash,
                vence_en=ahora_utc() + timedelta(hours=12),
                ip="127.0.0.1",
                user_agent="test",
            )
        )
        s.commit()

    yield {"cookie": sas.NOMBRE_COOKIE, "token": token}
    Base.metadata.drop_all(maquina)


def _cliente(escenario: dict[str, str], token: str | None = None) -> TestClient:
    from app.main import app

    cliente = TestClient(app)
    if token is not None:
        cliente.cookies.set(escenario["cookie"], token)
    return cliente


def test_reenviar_codigo_devuelve_un_codigo_valido(escenario: dict[str, str]) -> None:
    cliente = _cliente(escenario, escenario["token"])
    respuesta = cliente.post("/api/mi/codigo/reenviar")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert "codigo" in cuerpo

    with sesion_con_alcance(1) as s:
        solicitud = s.scalars(select(SolicitudDeRegistro)).first()
        assert solicitud is not None
        assert solicitud.estado == dom.Estado.SIN_VERIFICAR.value


def test_sin_sesion_no_reenvia(escenario: dict[str, str]) -> None:
    cliente = _cliente(escenario)
    respuesta = cliente.post("/api/mi/codigo/reenviar")
    assert respuesta.status_code == 401