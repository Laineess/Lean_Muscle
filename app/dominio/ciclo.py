"""Vigencia del ciclo de 30 dias y bloqueos por pago.

El MVP cobra con comprobante cargado por la alumna y validado por la coach (asistido por
OCR). No hay cobro automatico, y por eso la reforma a la LFPC de diciembre 2025 todavia no
aplica en su forma estricta — ver Anexo Legal, seccion 1.2. Si en Fase 2 entra pasarela,
esta logica cambia y el contrato debe inscribirse ante PROFECO.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from app.compartido.errores import Codigo, ErrorDeDominio

DIAS_POR_CICLO = 30
#: Con cuanta anticipacion se avisa a la coach de las renovaciones proximas.
DIAS_AVISO_RENOVACION = 15
#: Dias naturales sin actividad que disparan el protocolo de retencion.
DIAS_INACTIVIDAD_ALERTA = 3


class EstadoCiclo(StrEnum):
    PENDIENTE_PAGO = "pendiente_pago"
    ACTIVO = "activo"
    VENCIDO = "vencido"


class EstadoPago(StrEnum):
    PENDIENTE = "pendiente"
    VALIDADO = "validado"
    RECHAZADO = "rechazado"


@dataclass(frozen=True, slots=True)
class Ciclo:
    numero: int
    inicia_en: date
    estado: EstadoCiclo
    estado_pago: EstadoPago

    @property
    def termina_en(self) -> date:
        return self.inicia_en + timedelta(days=DIAS_POR_CICLO)

    def vigente_en(self, dia: date) -> bool:
        return self.inicia_en <= dia < self.termina_en


def estado_al_dia(ciclo: Ciclo, dia: date) -> EstadoCiclo:
    """Estado recalculado. Lo aplica el trabajo programado de las 07:00."""
    if ciclo.estado_pago is not EstadoPago.VALIDADO:
        return EstadoCiclo.PENDIENTE_PAGO
    return EstadoCiclo.ACTIVO if ciclo.vigente_en(dia) else EstadoCiclo.VENCIDO


def exigir_acceso_al_plan(ciclo: Ciclo, dia: date) -> None:
    """Guarda de la vista 'Mi Plan'. Pago pendiente o ciclo vencido la bloquean."""
    estado = estado_al_dia(ciclo, dia)
    if estado is EstadoCiclo.PENDIENTE_PAGO:
        raise ErrorDeDominio(Codigo.PAGO_SIN_VALIDAR, ciclo=ciclo.numero)
    if estado is EstadoCiclo.VENCIDO:
        raise ErrorDeDominio(
            Codigo.CICLO_VENCIDO,
            ciclo=ciclo.numero,
            termino_en=ciclo.termina_en.isoformat(),
        )


def renueva_dentro_de(ciclo: Ciclo, dia: date, dias: int = DIAS_AVISO_RENOVACION) -> bool:
    return dia <= ciclo.termina_en <= dia + timedelta(days=dias)


def esta_inactiva(ultimo_acceso: date | None, hoy: date) -> bool:
    if ultimo_acceso is None:
        return True
    return (hoy - ultimo_acceso).days >= DIAS_INACTIVIDAD_ALERTA
