"""Guardas de publicacion de plan y vigencia del ciclo."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.compartido.errores import Codigo, ErrorDeDominio
from app.dominio.chequeo import EstadoChequeo
from app.dominio.ciclo import (
    DIAS_INACTIVIDAD_ALERTA,
    Ciclo,
    EstadoCiclo,
    EstadoPago,
    esta_inactiva,
    estado_al_dia,
    exigir_acceso_al_plan,
    renueva_dentro_de,
)
from app.dominio.plan import (
    ContextoPublicacion,
    Macros,
    TipoPlan,
    guardas_de_publicacion,
)

MACROS_OK = Macros(Decimal(140), Decimal(175), Decimal(58))
"""140*4 + 175*4 + 58*9 = 1782 kcal, dentro del 5 % de 1850."""


def contexto(**cambios: object) -> ContextoPublicacion:
    base: dict[str, object] = {
        "tipo": TipoPlan.NUTRICION,
        "estado_chequeo_del_ciclo": EstadoChequeo.VALIDADO,
        "fotos_aprobadas": True,
        "chequeo_anterior_validado": True,
        "kcal_objetivo": 1850,
        "macros": MACROS_OK,
    }
    base.update(cambios)
    return ContextoPublicacion(**base)  # type: ignore[arg-type]


def codigos(ctx: ContextoPublicacion) -> set[Codigo]:
    return {e.codigo for e in guardas_de_publicacion(ctx)}


class TestPublicacionDePlan:
    def test_un_plan_completo_se_publica(self) -> None:
        assert guardas_de_publicacion(contexto()) == ()

    def test_sin_fotos_aprobadas_no_hay_plan(self) -> None:
        # Regla critica: "no se inicia el tratamiento ni se ajusta el plan sin fotos validas".
        assert Codigo.SIN_FOTOS_APROBADAS in codigos(contexto(fotos_aprobadas=False))

    def test_un_chequeo_pendiente_tampoco_habilita_plan(self) -> None:
        ctx = contexto(estado_chequeo_del_ciclo=EstadoChequeo.PENDIENTE_EVALUACION)
        assert Codigo.SIN_FOTOS_APROBADAS in codigos(ctx)

    def test_el_chequeo_anterior_sin_validar_bloquea(self) -> None:
        ctx = contexto(chequeo_anterior_validado=False)
        assert Codigo.CHEQUEO_ANTERIOR_SIN_VALIDAR in codigos(ctx)

    def test_sin_calorias_no_se_publica_nutricion(self) -> None:
        assert Codigo.PLAN_SIN_CALORIAS in codigos(contexto(kcal_objetivo=None))

    def test_sin_macros_no_se_publica_nutricion(self) -> None:
        assert Codigo.PLAN_SIN_MACROS in codigos(contexto(macros=None))

    def test_macros_que_no_cuadran_con_las_calorias_se_rechazan(self) -> None:
        # 40 g de proteina no sostienen 1850 kcal: casi seguro es un dedazo.
        flacos = Macros(Decimal(40), Decimal(60), Decimal(20))
        assert Codigo.MACROS_NO_CUADRAN_CON_CALORIAS in codigos(contexto(macros=flacos))

    def test_un_plan_de_entrenamiento_no_pide_macros(self) -> None:
        ctx = contexto(tipo=TipoPlan.ENTRENAMIENTO, kcal_objetivo=None, macros=None)
        assert guardas_de_publicacion(ctx) == ()

    def test_entrenamiento_si_exige_chequeo_validado(self) -> None:
        ctx = contexto(
            tipo=TipoPlan.ENTRENAMIENTO, kcal_objetivo=None, macros=None, fotos_aprobadas=False
        )
        assert Codigo.SIN_FOTOS_APROBADAS in codigos(ctx)


class TestCiclo:
    def test_dura_treinta_dias(self) -> None:
        c = Ciclo(1, date(2026, 7, 15), EstadoCiclo.ACTIVO, EstadoPago.VALIDADO)
        assert c.termina_en == date(2026, 8, 14)

    def test_sin_pago_validado_el_ciclo_no_esta_activo(self) -> None:
        c = Ciclo(1, date(2026, 8, 1), EstadoCiclo.ACTIVO, EstadoPago.PENDIENTE)
        assert estado_al_dia(c, date(2026, 8, 5)) is EstadoCiclo.PENDIENTE_PAGO

    def test_pago_pendiente_bloquea_la_vista_del_plan(self) -> None:
        c = Ciclo(1, date(2026, 8, 1), EstadoCiclo.ACTIVO, EstadoPago.PENDIENTE)
        with pytest.raises(ErrorDeDominio) as exc:
            exigir_acceso_al_plan(c, date(2026, 8, 5))
        assert exc.value.codigo is Codigo.PAGO_SIN_VALIDAR

    def test_ciclo_vencido_bloquea_aunque_este_pagado(self) -> None:
        c = Ciclo(1, date(2026, 6, 1), EstadoCiclo.ACTIVO, EstadoPago.VALIDADO)
        with pytest.raises(ErrorDeDominio) as exc:
            exigir_acceso_al_plan(c, date(2026, 8, 5))
        assert exc.value.codigo is Codigo.CICLO_VENCIDO

    def test_un_ciclo_vigente_y_pagado_deja_ver_el_plan(self) -> None:
        c = Ciclo(1, date(2026, 8, 1), EstadoCiclo.ACTIVO, EstadoPago.VALIDADO)
        exigir_acceso_al_plan(c, date(2026, 8, 5))  # no lanza

    def test_el_ultimo_dia_ya_no_es_vigente(self) -> None:
        c = Ciclo(1, date(2026, 8, 1), EstadoCiclo.ACTIVO, EstadoPago.VALIDADO)
        assert c.vigente_en(date(2026, 8, 30))
        assert not c.vigente_en(c.termina_en)

    def test_avisa_de_renovaciones_a_quince_dias(self) -> None:
        c = Ciclo(1, date(2026, 8, 1), EstadoCiclo.ACTIVO, EstadoPago.VALIDADO)
        assert renueva_dentro_de(c, date(2026, 8, 25))
        assert not renueva_dentro_de(c, date(2026, 8, 10))


class TestRetencion:
    def test_tres_dias_sin_entrar_dispara_la_alerta(self) -> None:
        assert esta_inactiva(date(2026, 8, 10), date(2026, 8, 13))

    def test_dos_dias_todavia_no(self) -> None:
        assert not esta_inactiva(date(2026, 8, 11), date(2026, 8, 13))

    def test_quien_nunca_entro_cuenta_como_inactiva(self) -> None:
        assert esta_inactiva(None, date(2026, 8, 13))

    def test_el_umbral_es_el_acordado(self) -> None:
        assert DIAS_INACTIVIDAD_ALERTA == 3
