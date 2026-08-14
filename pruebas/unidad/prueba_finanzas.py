"""Finanzas de la coach.

El dinero va en Decimal: la mitad de estas pruebas existen para que sumar cien movimientos
no produzca centavos fantasma.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.compartido.errores import Codigo, ErrorDeDominio
from app.dominio.finanzas import (
    CategoriaGasto,
    CategoriaIngreso,
    Movimiento,
    Resumen,
    Tarifa,
    TipoMovimiento,
    exigir_editable,
    ingreso_por_alumna,
    por_categoria,
    por_mes,
    proyeccion_mensual,
    resumir,
    validar,
    validar_tarifa,
)

HOY = date(2026, 8, 13)


def ingreso(monto: str, categoria: str = "ciclo", fecha: date = HOY, **extra: object) -> Movimiento:
    return Movimiento(
        tipo=TipoMovimiento.INGRESO,
        categoria=categoria,
        monto=Decimal(monto),
        fecha=fecha,
        concepto="Ciclo de agosto",
        **extra,  # type: ignore[arg-type]
    )


def gasto(monto: str, categoria: str = "plataforma", fecha: date = HOY) -> Movimiento:
    return Movimiento(
        tipo=TipoMovimiento.GASTO,
        categoria=categoria,
        monto=Decimal(monto),
        fecha=fecha,
        concepto="Suscripción",
    )


class TestValidacion:
    def test_un_movimiento_correcto_pasa(self) -> None:
        validar(ingreso("1200.00"))

    def test_el_monto_no_puede_ser_cero(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            validar(ingreso("0"))
        assert exc.value.codigo is Codigo.MONTO_INVALIDO

    def test_el_monto_no_puede_ser_negativo(self) -> None:
        # El signo lo da el tipo, no el monto: un gasto negativo sería un ingreso disfrazado.
        with pytest.raises(ErrorDeDominio) as exc:
            validar(gasto("-500.00"))
        assert exc.value.codigo is Codigo.MONTO_INVALIDO

    def test_un_monto_absurdo_se_rechaza(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            validar(ingreso("99000000.00"))
        assert exc.value.codigo is Codigo.MONTO_FUERA_DE_RANGO

    def test_una_categoria_de_gasto_no_vale_para_un_ingreso(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            validar(ingreso("1200.00", categoria="publicidad"))
        assert exc.value.codigo is Codigo.CATEGORIA_INVALIDA

    def test_una_categoria_de_ingreso_no_vale_para_un_gasto(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            validar(gasto("500.00", categoria="ciclo"))
        assert exc.value.codigo is Codigo.CATEGORIA_INVALIDA

    def test_el_concepto_no_puede_ir_vacio(self) -> None:
        movimiento = Movimiento(
            tipo=TipoMovimiento.GASTO,
            categoria=CategoriaGasto.LOCAL,
            monto=Decimal("500.00"),
            fecha=HOY,
            concepto="   ",
        )
        with pytest.raises(ErrorDeDominio) as exc:
            validar(movimiento)
        assert exc.value.codigo is Codigo.CONCEPTO_REQUERIDO


class TestMovimientosAutomaticos:
    def test_un_movimiento_manual_se_edita(self) -> None:
        exigir_editable(ingreso("1200.00"))

    def test_un_ingreso_de_pago_validado_no_se_edita_a_mano(self) -> None:
        # Editarlo aquí descuadraría el ingreso contra el cobro que lo originó.
        with pytest.raises(ErrorDeDominio) as exc:
            exigir_editable(ingreso("1200.00", automatico=True))
        assert exc.value.codigo is Codigo.MOVIMIENTO_AUTOMATICO_NO_EDITABLE


class TestResumen:
    def test_suma_ingresos_y_gastos(self) -> None:
        r = resumir([ingreso("1200.00"), ingreso("1200.00"), gasto("450.00")])
        assert r.ingresos == Decimal("2400.00")
        assert r.gastos == Decimal("450.00")
        assert r.utilidad == Decimal("1950.00")

    def test_cien_movimientos_no_producen_centavos_fantasma(self) -> None:
        # Con coma flotante esto daría 120000.00000000001.
        r = resumir([ingreso("1200.00") for _ in range(100)])
        assert r.ingresos == Decimal("120000.00")

    def test_una_agenda_vacia_da_cero_sin_reventar(self) -> None:
        r = resumir([])
        assert r.ingresos == Decimal("0.00")
        assert r.utilidad == Decimal("0.00")
        assert r.margen == Decimal("0.00")

    def test_el_margen_es_la_fraccion_de_utilidad(self) -> None:
        r = Resumen(Decimal("10000.00"), Decimal("2500.00"))
        assert r.margen == Decimal("0.750")

    def test_sin_ingresos_el_margen_es_cero_no_una_division_por_cero(self) -> None:
        assert Resumen(Decimal("0.00"), Decimal("500.00")).margen == Decimal("0.00")

    def test_un_mes_en_perdida_da_utilidad_negativa(self) -> None:
        r = resumir([ingreso("1200.00"), gasto("3000.00")])
        assert r.utilidad == Decimal("-1800.00")


class TestAgrupaciones:
    def test_las_categorias_salen_de_mayor_a_menor(self) -> None:
        movimientos = [
            gasto("450.00", "plataforma"),
            gasto("2000.00", "local"),
            gasto("300.00", "publicidad"),
        ]
        assert list(por_categoria(movimientos, TipoMovimiento.GASTO)) == [
            "local",
            "plataforma",
            "publicidad",
        ]

    def test_por_categoria_ignora_el_otro_tipo(self) -> None:
        movimientos = [ingreso("1200.00"), gasto("450.00")]
        assert por_categoria(movimientos, TipoMovimiento.INGRESO) == {"ciclo": Decimal("1200.00")}

    def test_los_meses_salen_en_orden_cronologico(self) -> None:
        movimientos = [
            ingreso("1200.00", fecha=date(2026, 8, 1)),
            ingreso("1200.00", fecha=date(2026, 6, 1)),
            ingreso("1200.00", fecha=date(2026, 7, 1)),
        ]
        assert list(por_mes(movimientos)) == ["2026-06", "2026-07", "2026-08"]

    def test_cada_mes_trae_su_propio_resumen(self) -> None:
        movimientos = [
            ingreso("1200.00", fecha=date(2026, 7, 5)),
            gasto("450.00", fecha=date(2026, 7, 8)),
            ingreso("2400.00", fecha=date(2026, 8, 2)),
        ]
        meses = por_mes(movimientos)
        assert meses["2026-07"].utilidad == Decimal("750.00")
        assert meses["2026-08"].utilidad == Decimal("2400.00")


class TestTarifas:
    def test_una_tarifa_correcta_pasa(self) -> None:
        validar_tarifa(Tarifa("PRO", "Profesional", Decimal("1200.00")))

    def test_una_tarifa_gratis_se_rechaza(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            validar_tarifa(Tarifa("X", "Gratis", Decimal("0.00")))
        assert exc.value.codigo is Codigo.MONTO_FUERA_DE_RANGO

    def test_una_duracion_imposible_se_rechaza(self) -> None:
        with pytest.raises(ErrorDeDominio) as exc:
            validar_tarifa(Tarifa("X", "Raro", Decimal("1200.00"), dias=0))
        assert exc.value.codigo is Codigo.DURACION_DE_TARIFA_INVALIDA

    def test_el_precio_diario_sale_del_precio_y_los_dias(self) -> None:
        assert Tarifa("PRO", "Profesional", Decimal("1200.00")).precio_diario == Decimal("40.00")

    def test_la_proyeccion_multiplica_alumnas_por_precio(self) -> None:
        tarifa = Tarifa("PRO", "Profesional", Decimal("1200.00"))
        assert proyeccion_mensual(7, tarifa) == Decimal("8400.00")

    def test_sin_alumnas_la_proyeccion_es_cero(self) -> None:
        assert proyeccion_mensual(0, Tarifa("PRO", "P", Decimal("1200.00"))) == Decimal("0.00")


class TestIngresoPorAlumna:
    def test_reparte_el_ingreso_entre_las_alumnas(self) -> None:
        r = Resumen(Decimal("8400.00"), Decimal("2000.00"))
        assert ingreso_por_alumna(r, 7) == Decimal("1200.00")

    def test_sin_alumnas_no_divide_entre_cero(self) -> None:
        assert ingreso_por_alumna(Resumen(Decimal("0.00"), Decimal("0.00")), 0) == Decimal("0.00")

    def test_redondea_a_centavos(self) -> None:
        r = Resumen(Decimal("1000.00"), Decimal("0.00"))
        assert ingreso_por_alumna(r, 3) == Decimal("333.33")


class TestCategorias:
    def test_las_categorias_de_ingreso_y_gasto_no_se_traslapan(self) -> None:
        # Si se traslaparan, la validación de categoría dejaría de distinguir el tipo.
        ingresos = {c.value for c in CategoriaIngreso}
        gastos = {c.value for c in CategoriaGasto}
        assert not (ingresos & gastos)
