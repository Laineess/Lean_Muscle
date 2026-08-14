"""Guardas de publicacion de plan.

Regla critica de negocio: sin fotos aprobadas no se genera ni se ajusta ningun plan, y una
coach no publica plan nuevo si el chequeo del mes anterior sigue sin validar.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.compartido.errores import Codigo, ErrorDeDominio
from app.dominio.chequeo import EstadoChequeo

#: Factores Atwater. Se usan para verificar que los macros publicados cuadren con las kcal.
KCAL_POR_GRAMO = {"proteina": Decimal(4), "carbohidrato": Decimal(4), "grasa": Decimal(9)}
#: Tolerancia de cuadre entre macros y calorias declaradas.
TOLERANCIA_KCAL = Decimal("0.05")


class TipoPlan(StrEnum):
    NUTRICION = "nutricion"
    ENTRENAMIENTO = "entrenamiento"


class EstadoPlan(StrEnum):
    BORRADOR = "borrador"
    PUBLICADO = "publicado"


@dataclass(frozen=True, slots=True)
class Macros:
    proteina_g: Decimal
    carbohidrato_g: Decimal
    grasa_g: Decimal

    def kcal_calculadas(self) -> Decimal:
        return (
            self.proteina_g * KCAL_POR_GRAMO["proteina"]
            + self.carbohidrato_g * KCAL_POR_GRAMO["carbohidrato"]
            + self.grasa_g * KCAL_POR_GRAMO["grasa"]
        )


@dataclass(frozen=True, slots=True)
class ContextoPublicacion:
    tipo: TipoPlan
    estado_chequeo_del_ciclo: EstadoChequeo
    fotos_aprobadas: bool
    chequeo_anterior_validado: bool
    kcal_objetivo: int | None = None
    macros: Macros | None = None
    contenido: dict[str, Any] | None = None


def guardas_de_publicacion(ctx: ContextoPublicacion) -> tuple[ErrorDeDominio, ...]:
    """Todo lo que impide publicar, junto. Vacio = se puede publicar."""
    errores: list[ErrorDeDominio] = []

    if not ctx.chequeo_anterior_validado:
        errores.append(ErrorDeDominio(Codigo.CHEQUEO_ANTERIOR_SIN_VALIDAR))

    if not ctx.fotos_aprobadas or ctx.estado_chequeo_del_ciclo is not EstadoChequeo.VALIDADO:
        errores.append(
            ErrorDeDominio(
                Codigo.SIN_FOTOS_APROBADAS,
                estado_chequeo=ctx.estado_chequeo_del_ciclo.value,
            )
        )

    if ctx.tipo is TipoPlan.NUTRICION:
        errores.extend(_guardas_de_nutricion(ctx))

    return tuple(errores)


def _guardas_de_nutricion(ctx: ContextoPublicacion) -> list[ErrorDeDominio]:
    errores: list[ErrorDeDominio] = []

    if ctx.kcal_objetivo is None or ctx.kcal_objetivo <= 0:
        errores.append(ErrorDeDominio(Codigo.PLAN_SIN_CALORIAS))
    if ctx.macros is None:
        errores.append(ErrorDeDominio(Codigo.PLAN_SIN_MACROS))

    if ctx.macros is not None and ctx.kcal_objetivo:
        calculadas = ctx.macros.kcal_calculadas()
        objetivo = Decimal(ctx.kcal_objetivo)
        desvio = abs(calculadas - objetivo) / objetivo
        if desvio > TOLERANCIA_KCAL:
            errores.append(
                ErrorDeDominio(
                    Codigo.MACROS_NO_CUADRAN_CON_CALORIAS,
                    kcal_objetivo=ctx.kcal_objetivo,
                    kcal_de_macros=str(calculadas),
                    tolerancia=str(TOLERANCIA_KCAL),
                )
            )

    return errores
