"""Finanzas de la coach: ingresos, gastos y rentabilidad.

Es contabilidad de gestión, no fiscal: sirve para que la coach sepa si su negocio gana
dinero, no para presentar declaraciones. Por eso no hay IVA desglosado ni folios fiscales.

Todo el dinero va en `Decimal`. Con coma flotante, sumar cien movimientos de 1200.00
produce centavos fantasma, y eso en una pantalla de ingresos se nota.

Módulo puro: sin base de datos ni HTTP.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.compartido.errores import Codigo, ErrorDeDominio

CENTAVOS = Decimal("0.01")
CERO = Decimal("0.00")


def centavos(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


class TipoMovimiento(StrEnum):
    INGRESO = "ingreso"
    GASTO = "gasto"


class CategoriaIngreso(StrEnum):
    CICLO = "ciclo"
    """Cobro del plan mensual de una alumna. Se genera solo al validar un pago."""
    CONSULTA = "consulta"
    """Consulta suelta, fuera de plan."""
    OTRO_INGRESO = "otro_ingreso"


class CategoriaGasto(StrEnum):
    PLATAFORMA = "plataforma"
    """Lo que la coach le paga a MyProgressPlan."""
    EQUIPO = "equipo"
    LOCAL = "local"
    FORMACION = "formacion"
    PUBLICIDAD = "publicidad"
    IMPUESTOS = "impuestos"
    OTRO_GASTO = "otro_gasto"


CATEGORIAS: dict[TipoMovimiento, frozenset[str]] = {
    TipoMovimiento.INGRESO: frozenset(c.value for c in CategoriaIngreso),
    TipoMovimiento.GASTO: frozenset(c.value for c in CategoriaGasto),
}

#: Tope de cordura. Un movimiento por encima de esto casi siempre es un dedazo de ceros.
MONTO_MAXIMO = Decimal("1000000.00")


@dataclass(frozen=True, slots=True)
class Movimiento:
    """Una entrada o salida de dinero. `alumna_id` solo cuando el ingreso viene de alguien."""

    tipo: TipoMovimiento
    categoria: str
    monto: Decimal
    fecha: date
    concepto: str
    alumna_id: int | None = None
    #: Los movimientos generados al validar un pago no se editan a mano: se corrigen en el
    #: pago que los originó, para que el ingreso y el cobro no se separen.
    automatico: bool = False

    @property
    def signo(self) -> Decimal:
        return self.monto if self.tipo is TipoMovimiento.INGRESO else -self.monto


def validar(movimiento: Movimiento) -> None:
    """Reglas de un movimiento suelto."""
    if movimiento.monto <= CERO:
        raise ErrorDeDominio(Codigo.MONTO_INVALIDO, monto=str(movimiento.monto))

    if movimiento.monto > MONTO_MAXIMO:
        raise ErrorDeDominio(
            Codigo.MONTO_FUERA_DE_RANGO, monto=str(movimiento.monto), maximo=str(MONTO_MAXIMO)
        )

    if movimiento.categoria not in CATEGORIAS[movimiento.tipo]:
        raise ErrorDeDominio(
            Codigo.CATEGORIA_INVALIDA,
            categoria=movimiento.categoria,
            tipo=movimiento.tipo.value,
        )

    if not movimiento.concepto.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)


def exigir_editable(movimiento: Movimiento) -> None:
    """Un movimiento automático refleja un pago validado; editarlo a mano descuadraría el
    ingreso contra el cobro que lo originó."""
    if movimiento.automatico:
        raise ErrorDeDominio(Codigo.MOVIMIENTO_AUTOMATICO_NO_EDITABLE)


# ---------------------------------------------------------------------------
# Agregados
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Resumen:
    ingresos: Decimal
    gastos: Decimal

    @property
    def utilidad(self) -> Decimal:
        return centavos(self.ingresos - self.gastos)

    @property
    def margen(self) -> Decimal:
        """Fracción de los ingresos que queda como utilidad. Sin ingresos no hay margen."""
        if self.ingresos == CERO:
            return CERO
        return (self.utilidad / self.ingresos).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def resumir(movimientos: Iterable[Movimiento]) -> Resumen:
    ingresos = CERO
    gastos = CERO
    for m in movimientos:
        if m.tipo is TipoMovimiento.INGRESO:
            ingresos += m.monto
        else:
            gastos += m.monto
    return Resumen(centavos(ingresos), centavos(gastos))


def por_categoria(movimientos: Iterable[Movimiento], tipo: TipoMovimiento) -> dict[str, Decimal]:
    """Totales por categoría, de mayor a menor: es el orden en que se leen."""
    totales: dict[str, Decimal] = {}
    for m in movimientos:
        if m.tipo is tipo:
            totales[m.categoria] = totales.get(m.categoria, CERO) + m.monto
    return dict(
        sorted(((k, centavos(v)) for k, v in totales.items()), key=lambda p: p[1], reverse=True)
    )


def por_mes(movimientos: Iterable[Movimiento]) -> dict[str, Resumen]:
    """Agrupa por `AAAA-MM`, en orden cronológico. Es lo que alimenta la gráfica."""
    cubos: dict[str, list[Movimiento]] = {}
    for m in movimientos:
        cubos.setdefault(f"{m.fecha.year:04d}-{m.fecha.month:02d}", []).append(m)
    return {mes: resumir(cubos[mes]) for mes in sorted(cubos)}


# ---------------------------------------------------------------------------
# Tarifas
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Tarifa:
    """Precio de un plan comercial de la coach.

    El precio se copia al ciclo al momento de cobrarlo, no se lee de aquí: si la coach sube
    la tarifa, las alumnas con ciclo abierto siguen pagando lo pactado.
    """

    codigo: str
    nombre: str
    precio: Decimal
    dias: int = 30
    activa: bool = True

    @property
    def precio_diario(self) -> Decimal:
        return centavos(self.precio / Decimal(self.dias))


def validar_tarifa(tarifa: Tarifa) -> None:
    if tarifa.precio <= CERO or tarifa.precio > MONTO_MAXIMO:
        raise ErrorDeDominio(Codigo.MONTO_FUERA_DE_RANGO, monto=str(tarifa.precio))
    if tarifa.dias < 1 or tarifa.dias > 365:
        raise ErrorDeDominio(Codigo.DURACION_DE_TARIFA_INVALIDA, dias=tarifa.dias)
    if not tarifa.nombre.strip():
        raise ErrorDeDominio(Codigo.CONCEPTO_REQUERIDO)


def proyeccion_mensual(activas: int, tarifa: Tarifa) -> Decimal:
    """Ingreso esperado si todas las alumnas activas renuevan. Es una proyección, no un dato:
    la pantalla tiene que decirlo."""
    return centavos(Decimal(activas) * tarifa.precio)


def ingreso_por_alumna(resumen: Resumen, alumnas: int) -> Decimal:
    """Cuánto deja cada alumna en promedio. Es el número que dice si conviene subir precio o
    sumar gente."""
    if alumnas <= 0:
        return CERO
    return centavos(resumen.ingresos / Decimal(alumnas))
