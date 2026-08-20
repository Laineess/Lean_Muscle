"""Plazos de los derechos ARCO. Se cuentan en días hábiles, no naturales."""

from __future__ import annotations

from datetime import date

from app.dominio.arco import (
    PLAZO_EJECUCION,
    PLAZO_RESPUESTA,
    Derecho,
    Estado,
    plazo_de,
    siguiente,
    sumar_habiles,
)


class TestDiasHabiles:
    def test_el_fin_de_semana_no_cuenta(self) -> None:
        # Viernes 14 de agosto de 2026 + 1 hábil = lunes 17.
        assert sumar_habiles(date(2026, 8, 14), 1) == date(2026, 8, 17)

    def test_veinte_habiles_son_cuatro_semanas(self) -> None:
        assert sumar_habiles(date(2026, 8, 14), 20) == date(2026, 9, 11)

    def test_cero_habiles_no_mueve_la_fecha(self) -> None:
        assert sumar_habiles(date(2026, 8, 14), 0) == date(2026, 8, 14)

    def test_los_plazos_son_los_de_la_ley(self) -> None:
        assert (PLAZO_RESPUESTA, PLAZO_EJECUCION) == (20, 15)


class TestPlazo:
    def test_recien_recibida_corre_el_de_respuesta(self) -> None:
        p = plazo_de(Estado.RECIBIDA, date(2026, 8, 14), None, date(2026, 8, 14))
        assert p is not None
        assert p.vence_el == date(2026, 9, 11)
        assert not p.vencido

    def test_contestada_corre_el_de_ejecucion_desde_la_respuesta(self) -> None:
        p = plazo_de(Estado.RESPONDIDA, date(2026, 8, 14), date(2026, 8, 20), date(2026, 8, 20))
        assert p is not None
        assert p.vence_el == sumar_habiles(date(2026, 8, 20), 15)

    def test_resuelta_ya_no_tiene_plazo(self) -> None:
        assert (
            plazo_de(Estado.RESUELTA, date(2026, 1, 1), date(2026, 1, 2), date(2026, 8, 14)) is None
        )

    def test_pasado_el_dia_queda_vencida(self) -> None:
        p = plazo_de(Estado.RECIBIDA, date(2026, 1, 1), None, date(2026, 8, 14))
        assert p is not None and p.vencido

    def test_avisa_antes_de_que_se_acabe(self) -> None:
        """De nada sirve enterarse el día que vence."""
        vence = sumar_habiles(date(2026, 8, 14), 20)
        p = plazo_de(Estado.RECIBIDA, date(2026, 8, 14), None, vence)
        assert p is not None and p.urge and not p.vencido


class TestAvance:
    def test_el_orden_no_tiene_vuelta_atras(self) -> None:
        assert siguiente(Estado.RECIBIDA) is Estado.RESPONDIDA
        assert siguiente(Estado.RESPONDIDA) is Estado.RESUELTA
        assert siguiente(Estado.RESUELTA) is Estado.RESUELTA

    def test_estan_los_cuatro_derechos(self) -> None:
        assert {d.value for d in Derecho} == {"A", "R", "C", "O"}
