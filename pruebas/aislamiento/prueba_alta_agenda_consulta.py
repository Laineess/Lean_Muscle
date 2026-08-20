"""Dar de alta a una alumna agenda su primera consulta.

El alta desde el panel se hace con la alumna delante, en el consultorio. Y el chequeo no
abre sin una consulta del ciclo: sin esta cita, la primera medición quedaba bloqueada justo
el día en que las dos estaban sentadas para tomarla, con un mensaje pidiéndole a la coach
que agendara la consulta que estaba teniendo.

Corre contra MySQL porque lo que se comprueba es lo que queda escrito, no lo que devuelve
una función.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.compartido.fechas import ahora_utc, dia_calendario
from app.datos.alcance import motor, sesion_con_alcance
from app.datos.base import Base
from app.datos.modelos import Alumna, Cita, Coach, CobroProgramado, Servicio, Tarifa, Usuario
from app.dominio.agenda import EstadoCita, Modalidad, TipoCita, ventana_de_chequeo
from app.servicios import cuentas
from app.servicios.seguridad import hash_contrasena


@pytest.fixture(scope="module")
def alta_hecha() -> Iterator[int]:
    """Una coach que da de alta a una alumna. Devuelve el id de la coach."""
    try:
        maquina = motor()
        with maquina.connect():
            pass
    except OperationalError as exc:  # pragma: no cover - depende del entorno
        pytest.skip(f"sin MySQL disponible: {exc}")

    Base.metadata.drop_all(maquina)
    Base.metadata.create_all(maquina)

    with Session(maquina) as s:
        coach = Coach(nombre="Mariana", slug="mariana", email="mariana@ejemplo.mx")
        s.add(coach)
        s.flush()

        suya = Usuario(
            coach_id=coach.id,
            rol="coach",
            email="mariana@ejemplo.mx",
            hash_contrasena=hash_contrasena("x"),
        )
        s.add(suya)
        s.flush()

        # Lo que la coach cobra: la inscripción se paga una vez y el ciclo cada mes.
        s.add(
            Servicio(
                coach_id=coach.id,
                nombre="Inscripción",
                motivo="inscripcion",
                precio=Decimal("500.00"),
                activo=True,
            )
        )
        tarifa = Tarifa(
            coach_id=coach.id,
            codigo="MENSUAL",
            nombre="Mensual",
            precio=Decimal("1200.00"),
            dias=30,
        )
        s.add(tarifa)
        s.flush()
        coach_id, usuario_id, tarifa_id = int(coach.id), int(suya.id), int(tarifa.id)
        s.commit()

    # El alta lee para comprobar el correo, y toda lectura exige alcance de inquilino.
    with sesion_con_alcance(coach_id) as s:
        cuentas.dar_de_alta(
            s,
            coach_id=coach_id,
            nombre="Carlos Ruiz",
            correo="carlos@ejemplo.mx",
            whatsapp=None,
            fecha_nacimiento=date(1994, 3, 22),
            estatura_cm=178,
            tarifa_id=tarifa_id,
            nivel_experiencia=None,
            emitida_por=usuario_id,
        )

    yield coach_id
    Base.metadata.drop_all(maquina)


def _cita(coach_id: int) -> Cita:
    with sesion_con_alcance(coach_id) as s:
        return s.scalars(select(Cita)).one()


class TestLaConsultaSeAgendaSola:
    def test_queda_una_cita(self, alta_hecha: int) -> None:
        assert _cita(alta_hecha) is not None

    def test_es_una_consulta_y_no_un_bloqueo(self, alta_hecha: int) -> None:
        # Solo las de tipo consulta abren la ventana del chequeo.
        assert _cita(alta_hecha).tipo == TipoCita.CONSULTA.value

    def test_es_de_hoy(self, alta_hecha: int) -> None:
        assert _cita(alta_hecha).inicia_en.date() == ahora_utc().date()

    def test_dura_lo_que_dura_una_consulta_de_esa_coach(self, alta_hecha: int) -> None:
        cita = _cita(alta_hecha)
        with sesion_con_alcance(alta_hecha) as s:
            coach = s.get(Coach, alta_hecha)
            assert coach is not None
            minutos = (cita.termina_en - cita.inicia_en).total_seconds() / 60
            assert minutos == coach.duracion_consulta_min

    def test_va_confirmada_y_presencial(self, alta_hecha: int) -> None:
        # La alumna está delante: no hay nada que confirmar ni por qué suponerla remota.
        cita = _cita(alta_hecha)
        assert cita.estado == EstadoCita.CONFIRMADA.value
        assert cita.modalidad == Modalidad.PRESENCIAL.value

    def test_es_de_la_alumna_recien_dada_de_alta(self, alta_hecha: int) -> None:
        with sesion_con_alcance(alta_hecha) as s:
            alumna = s.scalars(select(Alumna)).one()
            assert _cita(alta_hecha).alumna_id == alumna.id


class TestLaVentanaDelChequeoAbreHoy:
    """Lo que de verdad importa: que pueda medirse el mismo día."""

    def test_la_ventana_de_esa_consulta_esta_abierta_hoy(self, alta_hecha: int) -> None:
        cita = _cita(alta_hecha)
        with sesion_con_alcance(alta_hecha) as s:
            alumna = s.scalars(select(Alumna)).one()
            hoy = dia_calendario(ahora_utc(), alumna.zona_horaria)
        assert ventana_de_chequeo(cita.inicia_en).abierta(hoy)

    def test_la_consulta_cae_dentro_del_ciclo(self, alta_hecha: int) -> None:
        # La guarda descarta las consultas anteriores al inicio del ciclo.
        from app.datos.modelos import Ciclo

        cita = _cita(alta_hecha)
        with sesion_con_alcance(alta_hecha) as s:
            ciclo = s.scalars(select(Ciclo)).one()
        assert cita.inicia_en.date() >= ciclo.inicia_en


class TestLosDosCobrosDelAlta:
    """La inscripción y el primer ciclo son dos cargos, no uno.

    Antes salía una sola fila etiquetada «Inscripción» por el precio del ciclo: cobraba de
    menos y la inscripción no quedaba registrada en ninguna parte.
    """

    def _cobros(self, coach_id: int) -> list[CobroProgramado]:
        with sesion_con_alcance(coach_id) as s:
            return list(s.scalars(select(CobroProgramado).order_by(CobroProgramado.id)).all())

    def test_quedan_dos(self, alta_hecha: int) -> None:
        assert len(self._cobros(alta_hecha)) == 2

    def test_uno_es_la_inscripcion_con_su_propio_precio(self, alta_hecha: int) -> None:
        inscripcion = next(c for c in self._cobros(alta_hecha) if c.motivo == "inscripcion")
        assert inscripcion.monto == Decimal("500.00")
        assert inscripcion.concepto == "Inscripción"

    def test_el_otro_es_el_ciclo_con_el_precio_de_la_tarifa(self, alta_hecha: int) -> None:
        ciclo = next(c for c in self._cobros(alta_hecha) if c.motivo == "mensualidad")
        assert ciclo.monto == Decimal("1200.00")

    def test_los_dos_nacen_pendientes(self, alta_hecha: int) -> None:
        assert all(c.estado == "pendiente" for c in self._cobros(alta_hecha))

    def test_ninguno_cobra_el_ciclo_bajo_el_nombre_de_inscripcion(self, alta_hecha: int) -> None:
        inscripcion = next(c for c in self._cobros(alta_hecha) if c.motivo == "inscripcion")
        assert inscripcion.monto != Decimal("1200.00")
