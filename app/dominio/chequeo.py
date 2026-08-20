"""Maquina de estados del chequeo mensual y sus guardas.

Es el corazon del sistema. Ninguna transicion se dispara desde el cliente: la capa de
rutas construye un `Instantanea` con lo que hay en base y pregunta aqui si se puede pasar.

Modulo puro: sin ORM, sin HTTP. Eso es lo que permite probar todas las reglas sin levantar
una base de datos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum

from app.compartido.errores import Codigo, ErrorDeDominio
from app.dominio.medidas import NivelVarianza, TipoMedida, evaluar_varianza, faltantes


class EstadoChequeo(StrEnum):
    BORRADOR = "borrador"
    PENDIENTE_EVALUACION = "pendiente_evaluacion"
    VALIDADO = "validado"
    RECHAZADO_CALIDAD = "rechazado_calidad"
    #: Borrador que cruzo la medianoche sin completar. Se conserva la fila para la bitacora.
    DESCARTADO = "descartado"


class Angulo(StrEnum):
    FRONTAL = "frontal"
    PERFIL = "perfil"
    ESPALDA = "espalda"


ANGULOS_REQUERIDOS: frozenset[Angulo] = frozenset(Angulo)


class Transicion(StrEnum):
    ENVIAR = "enviar"
    VALIDAR = "validar"
    RECHAZAR = "rechazar"
    RECAPTURAR = "recapturar"
    DESCARTAR = "descartar"


#: Grafo de transiciones permitidas. Lo que no esta aqui, no ocurre.
TRANSICIONES: dict[Transicion, tuple[frozenset[EstadoChequeo], EstadoChequeo]] = {
    Transicion.ENVIAR: (
        frozenset({EstadoChequeo.BORRADOR}),
        EstadoChequeo.PENDIENTE_EVALUACION,
    ),
    Transicion.VALIDAR: (
        frozenset({EstadoChequeo.PENDIENTE_EVALUACION}),
        EstadoChequeo.VALIDADO,
    ),
    Transicion.RECHAZAR: (
        frozenset({EstadoChequeo.PENDIENTE_EVALUACION}),
        EstadoChequeo.RECHAZADO_CALIDAD,
    ),
    Transicion.RECAPTURAR: (
        frozenset({EstadoChequeo.RECHAZADO_CALIDAD}),
        EstadoChequeo.BORRADOR,
    ),
    Transicion.DESCARTAR: (
        frozenset({EstadoChequeo.BORRADOR}),
        EstadoChequeo.DESCARTADO,
    ),
}


@dataclass(frozen=True, slots=True)
class Instantanea:
    """Todo lo que las guardas necesitan saber de un chequeo, sin conocer la base de datos."""

    estado: EstadoChequeo
    fecha: date
    """Dia calendario del chequeo, evaluado en la zona horaria de la coach."""

    ayuno_confirmado: bool
    medidas_capturadas: frozenset[TipoMedida] = frozenset()
    angulos_capturados: frozenset[Angulo] = frozenset()
    fecha_pesaje: date | None = None
    fechas_de_fotos: frozenset[date] = frozenset()
    peso_kg: Decimal | None = None
    peso_anterior_kg: Decimal | None = None
    varianza_confirmada_por_alumna: bool = False
    cuestionario_completo: bool = True
    protocolo_foto_aceptado: bool = True


@dataclass(frozen=True, slots=True)
class ResultadoEnvio:
    """Lo que impide enviar (todo junto, no de uno en uno) y la alerta que hereda la coach."""

    errores: tuple[ErrorDeDominio, ...] = ()
    alerta_outlier: bool = False
    campos_faltantes: dict[str, list[str]] = field(default_factory=dict)

    @property
    def puede_enviar(self) -> bool:
        return not self.errores


def guardas_de_envio(inst: Instantanea) -> ResultadoEnvio:
    """Evalua **todas** las guardas de BORRADOR -> PENDIENTE_EVALUACION.

    Devuelve la lista completa en lugar de fallar en la primera: la alumna arregla todo de
    una pasada en vez de descubrir un problema nuevo en cada envio.
    """
    errores: list[ErrorDeDominio] = []
    faltan: dict[str, list[str]] = {}

    # --- Precondiciones de perfil ------------------------------------------
    if not inst.cuestionario_completo:
        errores.append(ErrorDeDominio(Codigo.CUESTIONARIO_INCOMPLETO))
    if not inst.protocolo_foto_aceptado:
        errores.append(ErrorDeDominio(Codigo.PROTOCOLO_FOTO_RECHAZADO))
    if not inst.ayuno_confirmado:
        errores.append(ErrorDeDominio(Codigo.AYUNO_SIN_CONFIRMAR))

    # --- Completitud de la captura -----------------------------------------
    medidas_faltantes = faltantes(set(inst.medidas_capturadas))
    if medidas_faltantes:
        nombres = sorted(m.value for m in medidas_faltantes)
        faltan["medidas"] = nombres
        errores.append(
            ErrorDeDominio(
                Codigo.MEDIDAS_INCOMPLETAS,
                faltantes=nombres,
                capturadas=len(inst.medidas_capturadas),
                requeridas=len(TipoMedida),
            )
        )

    angulos_faltantes = ANGULOS_REQUERIDOS - inst.angulos_capturados
    if angulos_faltantes:
        nombres = sorted(a.value for a in angulos_faltantes)
        faltan["fotos"] = nombres
        errores.append(ErrorDeDominio(Codigo.FOTOS_INCOMPLETAS, faltantes=nombres))

    if inst.fecha_pesaje is None or inst.peso_kg is None:
        faltan.setdefault("peso", []).append("pesaje")
        # Código propio y no el de las medidas: compartirlo sacaba dos veces «faltan
        # medidas», y la segunda mandaba a la alumna a revisar una pantalla donde no
        # faltaba nada. Lo que falta es el peso, y así lo dice.
        errores.append(ErrorDeDominio(Codigo.PESO_SIN_CAPTURAR))

    # --- Sincronia peso-fotos: mismo dia calendario, no ventana movil de 24 h ----
    dias = {d for d in (inst.fecha_pesaje, *inst.fechas_de_fotos) if d is not None}
    if dias and dias != {inst.fecha}:
        errores.append(
            ErrorDeDominio(
                Codigo.PESO_Y_FOTOS_EN_DIAS_DISTINTOS,
                fecha_chequeo=inst.fecha.isoformat(),
                dias=sorted(d.isoformat() for d in dias),
            )
        )

    # --- Varianza de peso ---------------------------------------------------
    alerta_outlier = False
    if inst.peso_kg is not None:
        varianza = evaluar_varianza(inst.peso_kg, inst.peso_anterior_kg)
        if varianza.nivel is NivelVarianza.ALERTA_COACH:
            alerta_outlier = True
        if varianza.nivel is not NivelVarianza.NORMAL and not inst.varianza_confirmada_por_alumna:
            errores.append(
                ErrorDeDominio(
                    Codigo.VARIANZA_DE_PESO_SIN_CONFIRMAR,
                    porcentaje=str(varianza.porcentaje),
                    nivel=varianza.nivel.value,
                )
            )

    return ResultadoEnvio(tuple(errores), alerta_outlier, faltan)


#: Mientras espera resolución, la coach todavía puede estimar y corregir. Después no: de ese
#: porcentaje sale el plan que ya se calculó, y cambiarlo por detrás deja el plan publicado
#: diciendo una cosa y el expediente otra.
ABIERTO_A_LA_COACH: frozenset[EstadoChequeo] = frozenset({EstadoChequeo.PENDIENTE_EVALUACION})

#: La alumna captura mientras es suyo. Enviado, ya no lo toca.
ABIERTO_A_LA_ALUMNA: frozenset[EstadoChequeo] = frozenset(
    {EstadoChequeo.BORRADOR, EstadoChequeo.RECHAZADO_CALIDAD}
)


def exigir_abierto(estado: EstadoChequeo, abiertos: frozenset[EstadoChequeo]) -> None:
    """Lanza si el chequeo ya no admite cambios.

    Va aparte de `transicionar` porque no todo cambio es una transición: estimar el
    porcentaje de grasa o borrar una foto no mueven el estado, y sin esta guarda se colaban
    sobre un expediente ya cerrado.
    """
    if estado not in abiertos:
        raise ErrorDeDominio(
            Codigo.CHEQUEO_YA_RESUELTO,
            estado=estado.value,
            abiertos=sorted(e.value for e in abiertos),
        )


def transicionar(
    estado: EstadoChequeo,
    transicion: Transicion,
    *,
    motivo: str | None = None,
    justificacion_outlier: str | None = None,
    alerta_outlier_abierta: bool = False,
) -> EstadoChequeo:
    """Aplica una transicion o lanza. No revisa las guardas de envio: eso es `guardas_de_envio`."""
    origenes, destino = TRANSICIONES[transicion]
    if estado not in origenes:
        raise ErrorDeDominio(
            Codigo.TRANSICION_NO_PERMITIDA,
            estado=estado.value,
            transicion=transicion.value,
            origenes=sorted(e.value for e in origenes),
        )

    if transicion is Transicion.RECHAZAR and not (motivo or "").strip():
        raise ErrorDeDominio(Codigo.MOTIVO_DE_RECHAZO_REQUERIDO)

    # Sobrescribir la alerta de outlier (>10 %) exige comentario tecnico de la coach.
    if (
        transicion is Transicion.VALIDAR
        and alerta_outlier_abierta
        and not (justificacion_outlier or "").strip()
    ):
        raise ErrorDeDominio(Codigo.JUSTIFICACION_DE_OUTLIER_REQUERIDA)

    return destino


def debe_descartarse(inst: Instantanea, hoy: date) -> bool:
    """Un borrador que no cerro su dia calendario ya no es comparable: se descarta a medianoche.

    Deliberadamente estricto — un peso de ayer con fotos de hoy no mide lo mismo.
    """
    if inst.estado is not EstadoChequeo.BORRADOR:
        return False
    if hoy <= inst.fecha:
        return False
    return bool(guardas_de_envio(inst).errores)
