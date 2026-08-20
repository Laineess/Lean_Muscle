"""Reglas de la baja: los quince días de lectura y la confirmación por nombre.

Se calculan sin base de datos, así que se prueban sin base de datos.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.compartido.errores import ErrorDeDominio
from app.dominio.baja import (
    GRACIA_DE_LECTURA,
    EstadoDeAlumna,
    borra_el,
    esta_vencida,
    exigir_confirmacion,
    puede_leer_lo_suyo,
)

AHORA = datetime(2026, 8, 19, 10, 0, tzinfo=UTC)


class TestPlazo:
    def test_se_borra_quince_dias_despues(self) -> None:
        assert borra_el(AHORA) == AHORA + GRACIA_DE_LECTURA

    def test_recien_dada_de_baja_no_se_borra(self) -> None:
        assert not esta_vencida(AHORA, AHORA)

    def test_al_cumplirse_el_plazo_se_borra(self) -> None:
        assert esta_vencida(AHORA - GRACIA_DE_LECTURA, AHORA)

    def test_una_alumna_sin_baja_no_vence_nunca(self) -> None:
        assert not esta_vencida(None, AHORA)


class TestLecturaDeGracia:
    def test_puede_bajar_lo_suyo_mientras_dure(self) -> None:
        assert puede_leer_lo_suyo(EstadoDeAlumna.BAJA.value, AHORA - timedelta(days=3), AHORA)

    def test_pasado_el_plazo_ya_no_entra(self) -> None:
        # Aunque el trabajo de purga no haya corrido: el plazo lo fija la fecha de la baja,
        # no la puntualidad del servidor.
        assert not puede_leer_lo_suyo(EstadoDeAlumna.BAJA.value, AHORA - GRACIA_DE_LECTURA, AHORA)

    @pytest.mark.parametrize(
        "estado",
        [EstadoDeAlumna.ACTIVA, EstadoDeAlumna.BORRADA, EstadoDeAlumna.DESCARTADA],
    )
    def test_esto_solo_aplica_a_una_baja(self, estado: EstadoDeAlumna) -> None:
        assert not puede_leer_lo_suyo(estado.value, AHORA, AHORA)


class TestConfirmacion:
    def test_el_nombre_exacto_pasa(self) -> None:
        exigir_confirmacion("Andrea Sáenz", "Andrea Sáenz")

    def test_sin_acentos_tambien(self) -> None:
        # El objetivo es que se detenga a leer a quién da de baja, no ganarle a la ortografía.
        exigir_confirmacion("Andrea Sáenz", "andrea saenz")

    def test_con_espacios_de_sobra_tambien(self) -> None:
        exigir_confirmacion("Andrea Sáenz", "  Andrea   Sáenz ")

    @pytest.mark.parametrize("escrito", ["Andrea", "Andrea Saens", "", "Otra Persona"])
    def test_lo_que_no_es_su_nombre_no_pasa(self, escrito: str) -> None:
        with pytest.raises(ErrorDeDominio):
            exigir_confirmacion("Andrea Sáenz", escrito)


class TestCartera:
    def test_solo_activa_y_pausa_son_cartera(self) -> None:
        from app.datos.repos.consultas import FUERA_DE_CARTERA

        fuera = {e.value for e in EstadoDeAlumna} - {
            EstadoDeAlumna.ACTIVA.value,
            EstadoDeAlumna.PAUSA.value,
        }
        assert fuera == set(FUERA_DE_CARTERA), (
            "los estados que no son cartera y el filtro de la consulta se separaron"
        )


#: Tablas que cuelgan de la alumna o de su cuenta y **no** se borran con la baja, cada una
#: con el motivo por el que la ley pide conservarla. Agregar aquí obliga a justificarlo.
SOBREVIVEN = {
    "consentimiento": "constancia de qué texto aceptó y cuándo; cinco años",
    "acceso_sensible": "bitácora de quién vio su expediente; cinco años",
    "solicitud_arco": "constancia de que ejerció un derecho y cómo se resolvió",
    "movimiento_financiero": "es la contabilidad de la coach y ya no lleva su nombre",
    "alumna": "la ficha se vacía, no se borra: de ella cuelga todo lo anterior",
    "anuncio": "apunta al usuario de la coach que lo escribió, no al de ella",
    "cobro_coach": "apunta al superadmin que registró el cobro de la coach",
}


class TestBorradoCompleto:
    def test_toda_tabla_que_cuelga_de_ella_se_borra_o_se_declara(self) -> None:
        """Una tabla nueva que cuelgue de la alumna y nadie contemple aquí sobrevive a su
        baja en silencio, que es exactamente lo que el aviso de privacidad promete que no
        pasa."""
        from app.datos.base import Base
        from app.servicios.baja import POR_ALUMNA, POR_CHEQUEO, POR_CICLO, POR_USUARIO

        cubiertas = {
            t.__tablename__ for t in POR_ALUMNA + POR_CHEQUEO + POR_CICLO + POR_USUARIO
        } | {"chequeo", "ciclo", "usuario"}

        sueltas = []
        for tabla in Base.metadata.tables.values():
            apunta = any(
                fk.column.table.name in {"alumna", "usuario", "chequeo", "ciclo"}
                for c in tabla.columns
                for fk in c.foreign_keys
            )
            if not apunta or tabla.name in cubiertas or tabla.name in SOBREVIVEN:
                continue
            sueltas.append(tabla.name)

        assert not sueltas, (
            f"estas tablas cuelgan de la alumna y la baja no las toca: {sorted(sueltas)}. "
            "O se agregan a las listas de `servicios/baja.py`, o se declara aquí por qué "
            "la ley obliga a conservarlas."
        )

    def test_lo_que_sobrevive_esta_declarado_en_el_servicio(self) -> None:
        from app.servicios.baja import SE_CONSERVAN

        # La ficha no está en el servicio porque no «sobrevive»: se vacía.
        # La ficha y las dos que apuntan a otra persona no «sobreviven»: nunca fueron suyas.
        assert set(SE_CONSERVAN) == set(SOBREVIVEN) - {"alumna", "anuncio", "cobro_coach"}
