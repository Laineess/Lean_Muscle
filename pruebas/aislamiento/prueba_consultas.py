"""Prueba de fuga sobre cada consulta de lectura.

El encabezado de `app/datos/repos/consultas.py` dice que **cada función necesita su prueba
de aislamiento**. Este archivo la cumple: siembra dos coaches con datos equivalentes,
ejecuta cada consulta con la sesión de la coach A, y falla si aparece un solo registro de la
coach B.

Es lo que sustituye de verdad al Row Level Security que MySQL no tiene: no una promesa, una
prueba que corre en cada cambio. Si falla, no se despliega.

Requiere MySQL. Se salta sola si no hay base, para que el resto de la batería siga corriendo
en una máquina limpia.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.datos.alcance import motor, sesion_con_alcance
from app.datos.base import Base
from app.datos.modelos import (
    Alumna,
    Chequeo,
    Ciclo,
    Cita,
    Coach,
    Consentimiento,
    Foto,
    HistorialClinico,
    Medida,
    Mensaje,
    Notificacion,
    Pago,
    Pesaje,
    Plan,
    Usuario,
)
from app.datos.repos import consultas as q
from app.servicios.seguridad import hash_contrasena

pytestmark = [pytest.mark.integracion, pytest.mark.aislamiento]

FECHA = date(2026, 8, 1)
MOMENTO = datetime(2026, 8, 1, 7, tzinfo=UTC)


@dataclass(frozen=True)
class Inquilino:
    """Los identificadores que necesita cada prueba para pedir por A y comprobar contra B."""

    coach_id: int
    usuario_id: int
    alumna_id: int
    alumna_ulid: str
    ciclo_id: int
    chequeo_id: int
    chequeo_ulid: str
    borrador_id: int
    cita_ulid: str


def _sembrar(s: Session, etiqueta: str) -> Inquilino:
    """Un inquilino completo: alumna con chequeo, medidas, plan, pago, cita y aviso."""
    coach = Coach(nombre=f"Coach {etiqueta}", slug=etiqueta, email=f"{etiqueta}@ejemplo.mx")
    s.add(coach)
    s.flush()

    usuario = Usuario(
        coach_id=coach.id,
        rol="alumna",
        email=f"alumna-{etiqueta}@ejemplo.mx",
        hash_contrasena=hash_contrasena("x"),
        ultimo_acceso_en=MOMENTO,
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

    chequeo = Chequeo(
        coach_id=coach.id,
        alumna_id=alumna.id,
        ciclo_id=ciclo.id,
        fecha=FECHA,
        estado="pendiente_evaluacion",
    )
    s.add(chequeo)
    s.flush()

    cita = Cita(
        coach_id=coach.id,
        alumna_id=alumna.id,
        titulo=f"Consulta de {etiqueta}",
        inicia_en=MOMENTO,
        termina_en=MOMENTO + timedelta(hours=1),
    )

    # Un segundo chequeo, este abierto: es lo que `borrador_de` tiene que encontrar, y lo que
    # no debe encontrar cuando se pide con el ciclo de la otra coach.
    borrador = Chequeo(
        coach_id=coach.id,
        alumna_id=alumna.id,
        ciclo_id=ciclo.id,
        fecha=FECHA + timedelta(days=30),
        estado="borrador",
    )
    s.add(borrador)
    s.flush()

    s.add_all(
        [
            Foto(
                coach_id=coach.id,
                chequeo_id=chequeo.id,
                angulo="frontal",
                storage_key=f"coach/{coach.id}/f.webp",
            ),
            Mensaje(
                coach_id=coach.id,
                alumna_id=alumna.id,
                autor="coach",
                cuerpo=f"Mensaje de {etiqueta}",
                enviado_en=MOMENTO,
            ),
            Consentimiento(
                coach_id=coach.id,
                alumna_id=alumna.id,
                tipo="protocolo_foto",
                version_texto="v2",
                texto_hash="0" * 64,
                aceptado_en=MOMENTO,
            ),
            Pesaje(
                coach_id=coach.id,
                alumna_id=alumna.id,
                chequeo_id=chequeo.id,
                fecha=FECHA,
                peso_kg=Decimal("65.2"),
            ),
            Medida(coach_id=coach.id, chequeo_id=chequeo.id, tipo="cintura", valor=Decimal("74.1")),
            HistorialClinico(
                coach_id=coach.id,
                alumna_id=alumna.id,
                lesiones=f"Historial de {etiqueta}",
                vigente_desde=MOMENTO,
            ),
            Plan(
                coach_id=coach.id,
                alumna_id=alumna.id,
                ciclo_id=ciclo.id,
                tipo="nutricion",
                contenido={},
            ),
            Pago(
                coach_id=coach.id,
                alumna_id=alumna.id,
                ciclo_id=ciclo.id,
                monto=Decimal("1200.00"),
                estado="validado",
            ),
            Notificacion(
                coach_id=coach.id, destinatario_id=usuario.id, tipo="recordatorio", payload={}
            ),
            cita,
        ]
    )
    s.flush()

    return Inquilino(
        coach_id=coach.id,
        usuario_id=usuario.id,
        alumna_id=alumna.id,
        alumna_ulid=alumna.ulid,
        ciclo_id=ciclo.id,
        chequeo_id=chequeo.id,
        chequeo_ulid=chequeo.ulid,
        borrador_id=borrador.id,
        cita_ulid=cita.ulid,
    )


@pytest.fixture(scope="module")
def inquilinos() -> Iterator[tuple[Inquilino, Inquilino]]:
    try:
        maquina = motor()
        with maquina.connect():
            pass
    except OperationalError as exc:  # pragma: no cover - depende del entorno
        pytest.skip(f"sin MySQL disponible: {exc}")

    Base.metadata.drop_all(maquina)
    Base.metadata.create_all(maquina)

    with Session(maquina) as s:
        a = _sembrar(s, "aaa")
        b = _sembrar(s, "bbb")
        s.commit()

    yield a, b
    Base.metadata.drop_all(maquina)


# ---------------------------------------------------------------------------
# Lo que se pide con el ULID de la otra coach simplemente no existe
# ---------------------------------------------------------------------------


def test_no_se_alcanza_una_alumna_ajena_por_ulid(inquilinos: tuple[Inquilino, Inquilino]) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        assert q.alumna_por_ulid(s, a.alumna_ulid) is not None
        # El ULID de B existe en la base, pero no para esta sesión: 404, no 403. Un 403
        # confirmaría que existe en otro inquilino.
        assert q.alumna_por_ulid(s, b.alumna_ulid) is None


def test_no_se_alcanza_un_chequeo_ajeno_por_ulid(inquilinos: tuple[Inquilino, Inquilino]) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        assert q.chequeo_por_ulid(s, a.chequeo_ulid) is not None
        assert q.chequeo_por_ulid(s, b.chequeo_ulid) is None


def test_no_se_alcanza_una_cita_ajena_por_ulid(inquilinos: tuple[Inquilino, Inquilino]) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        assert q.cita_por_ulid(s, a.cita_ulid) is not None
        assert q.cita_por_ulid(s, b.cita_ulid) is None


def test_el_usuario_de_otra_coach_no_resuelve_a_su_alumna(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        assert q.alumna_de_usuario(s, a.usuario_id) is not None
        assert q.alumna_de_usuario(s, b.usuario_id) is None


# ---------------------------------------------------------------------------
# Las listas nunca traen filas de la otra coach
# ---------------------------------------------------------------------------


def test_la_cartera_solo_trae_alumnas_propias(inquilinos: tuple[Inquilino, Inquilino]) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        filas = q.cartera(s)
    assert len(filas) == 1
    assert all(f.coach_id == a.coach_id for f in filas)
    assert all(f.id != b.alumna_id for f in filas)


def test_los_chequeos_de_una_alumna_ajena_salen_vacios(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        # Pedir por el id interno de la alumna de B es el ataque más directo posible.
        assert q.chequeos_de(s, b.alumna_id) == []
        assert q.chequeos_de(s, a.alumna_id) != []


def test_las_medidas_de_un_chequeo_ajeno_salen_vacias(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        ajenas = q.medidas_de(s, [b.chequeo_id])
        propias = q.medidas_de(s, [a.chequeo_id])
    assert ajenas[b.chequeo_id] == {}
    assert propias[a.chequeo_id] != {}


def test_el_peso_de_un_chequeo_ajeno_no_viaja(inquilinos: tuple[Inquilino, Inquilino]) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        assert q.peso_de_chequeo(s, [b.chequeo_id]) == {}
        assert q.peso_de_chequeo(s, [a.chequeo_id]) != {}


def test_los_pesajes_del_ciclo_ajeno_salen_vacios(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        # Este va por JOIN contra `chequeo`: el filtro tiene que alcanzar también la tabla
        # unida, que es donde se escapan los datos cuando se escribe a mano.
        assert q.pesajes_del_ciclo(s, b.alumna_id, b.ciclo_id) == []
        assert q.pesajes_del_ciclo(s, a.alumna_id, a.ciclo_id) != []


def test_el_ciclo_de_una_alumna_ajena_no_existe(inquilinos: tuple[Inquilino, Inquilino]) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        assert q.ciclo_vigente(s, b.alumna_id) is None
        assert q.ciclo_vigente(s, a.alumna_id) is not None


def test_los_ciclos_vigentes_no_mezclan_inquilinos(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        vigentes = q.ciclos_vigentes(s, [a.alumna_id, b.alumna_id])
    assert set(vigentes) == {a.alumna_id}


def test_los_planes_de_un_ciclo_ajeno_salen_vacios(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        assert q.planes_del_ciclo(s, b.alumna_id, b.ciclo_id) == {}
        assert q.planes_del_ciclo(s, a.alumna_id, a.ciclo_id) != {}


def test_el_historial_clinico_ajeno_no_se_lee(inquilinos: tuple[Inquilino, Inquilino]) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        # De todo lo que hay aquí, esto es lo más sensible: historial clínico de otra coach.
        assert q.historial_vigente(s, b.alumna_id) is None
        assert q.historial_vigente(s, a.alumna_id) is not None


def test_los_pagos_de_un_ciclo_ajeno_no_viajan(inquilinos: tuple[Inquilino, Inquilino]) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        assert q.pago_del_ciclo(s, [b.ciclo_id]) == {}
        assert q.pago_del_ciclo(s, [a.ciclo_id]) != {}


def test_los_avisos_de_otro_usuario_no_se_cuentan(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        assert q.avisos_sin_leer(s, b.usuario_id) == 0
        assert q.avisos_sin_leer(s, a.usuario_id) == 1


def test_el_ultimo_acceso_de_otro_usuario_no_se_expone(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        accesos = q.ultimo_acceso_de(s, [a.usuario_id, b.usuario_id])
    assert set(accesos) == {a.usuario_id}


def test_el_ultimo_chequeo_por_alumna_no_mezcla(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        ultimos = q.ultimo_chequeo_por_alumna(s, [a.alumna_id, b.alumna_id])
    assert set(ultimos) == {a.alumna_id}


def test_la_agenda_solo_trae_citas_propias(inquilinos: tuple[Inquilino, Inquilino]) -> None:
    a, _ = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        citas = q.citas_entre(s, MOMENTO - timedelta(days=1), MOMENTO + timedelta(days=1))
    assert len(citas) == 1
    assert citas[0].coach_id == a.coach_id


def test_la_agenda_del_dia_solo_trae_citas_propias(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    a, _ = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        citas = q.citas_del_dia(s, MOMENTO.date())
    assert all(c.coach_id == a.coach_id for c in citas)


# ---------------------------------------------------------------------------
# Simetría: la comprobación vale en los dos sentidos
# ---------------------------------------------------------------------------


def test_la_segunda_coach_tampoco_ve_a_la_primera(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    """Sin esto, un filtro que devolviera siempre las filas de la coach A pasaría todas las
    pruebas anteriores."""
    a, b = inquilinos
    with sesion_con_alcance(b.coach_id) as s:
        filas = q.cartera(s)
        assert len(filas) == 1
        assert filas[0].id == b.alumna_id
        assert q.alumna_por_ulid(s, a.alumna_ulid) is None


# ---------------------------------------------------------------------------
# Consultas de la captura y de la mensajería
# ---------------------------------------------------------------------------


def test_el_borrador_de_otra_alumna_no_se_alcanza(inquilinos: tuple[Inquilino, Inquilino]) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        propio = q.borrador_de(s, a.alumna_id, a.ciclo_id)
        assert propio is not None and propio.id == a.borrador_id
        # Con los identificadores internos de B, que es el ataque más directo posible.
        assert q.borrador_de(s, b.alumna_id, b.ciclo_id) is None


def test_las_fotos_de_un_chequeo_ajeno_no_se_listan(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        assert q.fotos_de(s, a.chequeo_id) != []
        assert q.fotos_de(s, b.chequeo_id) == []


def test_las_medidas_de_un_chequeo_ajeno_no_se_listan(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        assert q.medidas_del_chequeo(s, a.chequeo_id) != []
        assert q.medidas_del_chequeo(s, b.chequeo_id) == []


def test_el_hilo_de_otra_alumna_no_se_lee(inquilinos: tuple[Inquilino, Inquilino]) -> None:
    """Lo más obvio de filtrar y lo más fácil de olvidar: la conversación privada."""
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        assert q.mensajes_de(s, a.alumna_id) != []
        assert q.mensajes_de(s, b.alumna_id) == []


def test_el_consentimiento_de_otra_alumna_no_cuenta(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    """Si se colara, una alumna podría enviar su chequeo apoyada en el consentimiento de
    otra: el registro de quién aceptó qué dejaría de significar nada."""
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        assert q.consentimiento_vigente(s, a.alumna_id, "protocolo_foto") is not None
        assert q.consentimiento_vigente(s, b.alumna_id, "protocolo_foto") is None


def test_las_proximas_citas_de_una_alumna_ajena_no_se_alcanzan(
    inquilinos: tuple[Inquilino, Inquilino],
) -> None:
    a, b = inquilinos
    with sesion_con_alcance(a.coach_id) as s:
        assert q.proximas_citas_de(s, a.alumna_id, MOMENTO - timedelta(days=1)) != []
        assert q.proximas_citas_de(s, b.alumna_id, MOMENTO - timedelta(days=1)) == []
