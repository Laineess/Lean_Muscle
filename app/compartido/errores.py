"""Errores tipados del dominio.

Convencion acordada (Propuesta Backend 15.5): una regla de negocio nunca devuelve una
cadena. Devuelve un error con `codigo`; la capa HTTP lo traduce a estado y a texto en
`app/rutas/traduccion.py`, que es el unico lugar donde vive el mensaje que lee la usuaria.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class Codigo(StrEnum):
    # --- Captura biometrica -------------------------------------------------
    PESO_FUERA_DE_RANGO = "PESO_FUERA_DE_RANGO"
    MEDIDA_FUERA_DE_RANGO = "MEDIDA_FUERA_DE_RANGO"
    MEDIDA_EN_CERO = "MEDIDA_EN_CERO"
    ESTATURA_FUERA_DE_RANGO = "ESTATURA_FUERA_DE_RANGO"
    PESAJE_DUPLICADO_EN_FECHA = "PESAJE_DUPLICADO_EN_FECHA"
    PESAJES_DEL_CICLO_AGOTADOS = "PESAJES_DEL_CICLO_AGOTADOS"
    VARIANZA_DE_PESO_SIN_CONFIRMAR = "VARIANZA_DE_PESO_SIN_CONFIRMAR"

    # --- Maquina de estados del chequeo ------------------------------------
    MEDIDAS_INCOMPLETAS = "MEDIDAS_INCOMPLETAS"
    FOTOS_INCOMPLETAS = "FOTOS_INCOMPLETAS"
    FOTO_ANGULO_DUPLICADO = "FOTO_ANGULO_DUPLICADO"
    PESO_Y_FOTOS_EN_DIAS_DISTINTOS = "PESO_Y_FOTOS_EN_DIAS_DISTINTOS"
    TRANSICION_NO_PERMITIDA = "TRANSICION_NO_PERMITIDA"
    MOTIVO_DE_RECHAZO_REQUERIDO = "MOTIVO_DE_RECHAZO_REQUERIDO"
    JUSTIFICACION_DE_OUTLIER_REQUERIDA = "JUSTIFICACION_DE_OUTLIER_REQUERIDA"
    AYUNO_SIN_CONFIRMAR = "AYUNO_SIN_CONFIRMAR"

    # --- Calculadora metabolica --------------------------------------------
    PORCENTAJE_DE_GRASA_INVALIDO = "PORCENTAJE_DE_GRASA_INVALIDO"
    REPARTO_DE_MACROS_NO_SUMA_UNO = "REPARTO_DE_MACROS_NO_SUMA_UNO"
    DIAS_DE_REFEED_FUERA_DE_RANGO = "DIAS_DE_REFEED_FUERA_DE_RANGO"
    OBJETIVO_DE_GRASA_NO_ES_MENOR = "OBJETIVO_DE_GRASA_NO_ES_MENOR"
    PROYECCION_SIN_DEFICIT = "PROYECCION_SIN_DEFICIT"
    PROYECCION_SIN_SUPERAVIT = "PROYECCION_SIN_SUPERAVIT"
    SIN_PORCENTAJE_DE_GRASA_DEL_CHEQUEO = "SIN_PORCENTAJE_DE_GRASA_DEL_CHEQUEO"

    # --- Agenda -------------------------------------------------------------
    CITA_RANGO_INVALIDO = "CITA_RANGO_INVALIDO"
    CITA_DURACION_INVALIDA = "CITA_DURACION_INVALIDA"
    CITA_EN_EL_PASADO = "CITA_EN_EL_PASADO"
    CITA_SE_SOLAPA = "CITA_SE_SOLAPA"
    MOTIVO_DE_CANCELACION_REQUERIDO = "MOTIVO_DE_CANCELACION_REQUERIDO"

    # --- Finanzas -----------------------------------------------------------
    MONTO_INVALIDO = "MONTO_INVALIDO"
    MONTO_FUERA_DE_RANGO = "MONTO_FUERA_DE_RANGO"
    CATEGORIA_INVALIDA = "CATEGORIA_INVALIDA"
    CONCEPTO_REQUERIDO = "CONCEPTO_REQUERIDO"
    MOVIMIENTO_AUTOMATICO_NO_EDITABLE = "MOVIMIENTO_AUTOMATICO_NO_EDITABLE"
    DURACION_DE_TARIFA_INVALIDA = "DURACION_DE_TARIFA_INVALIDA"

    # --- Alta y cuenta ------------------------------------------------------
    CORREO_YA_REGISTRADO = "CORREO_YA_REGISTRADO"
    CORREO_INVALIDO = "CORREO_INVALIDO"
    LIMITE_DE_ALUMNAS_ALCANZADO = "LIMITE_DE_ALUMNAS_ALCANZADO"
    CONTRASENA_DEBIL = "CONTRASENA_DEBIL"
    CONTRASENA_ACTUAL_INCORRECTA = "CONTRASENA_ACTUAL_INCORRECTA"

    # --- Guardas de plan y ciclo -------------------------------------------
    CHEQUEO_ANTERIOR_SIN_VALIDAR = "CHEQUEO_ANTERIOR_SIN_VALIDAR"
    SIN_FOTOS_APROBADAS = "SIN_FOTOS_APROBADAS"
    PLAN_SIN_CALORIAS = "PLAN_SIN_CALORIAS"
    PLAN_SIN_MACROS = "PLAN_SIN_MACROS"
    MACROS_NO_CUADRAN_CON_CALORIAS = "MACROS_NO_CUADRAN_CON_CALORIAS"
    CICLO_VENCIDO = "CICLO_VENCIDO"
    PAGO_SIN_VALIDAR = "PAGO_SIN_VALIDAR"

    # --- Perfil, consentimientos y acceso ----------------------------------
    CUESTIONARIO_INCOMPLETO = "CUESTIONARIO_INCOMPLETO"
    CONSENTIMIENTO_FALTANTE = "CONSENTIMIENTO_FALTANTE"
    PROTOCOLO_FOTO_RECHAZADO = "PROTOCOLO_FOTO_RECHAZADO"
    MENOR_DE_EDAD = "MENOR_DE_EDAD"
    CREDENCIALES_INVALIDAS = "CREDENCIALES_INVALIDAS"
    SESION_EXPIRADA = "SESION_EXPIRADA"
    SIN_PERMISO = "SIN_PERMISO"

    # --- Aislamiento --------------------------------------------------------
    SIN_ALCANCE_DE_INQUILINO = "SIN_ALCANCE_DE_INQUILINO"


class ErrorDeDominio(Exception):
    """Violacion de una regla de negocio. No conoce HTTP."""

    def __init__(self, codigo: Codigo, **detalle: Any) -> None:
        super().__init__(codigo.value)
        self.codigo = codigo
        self.detalle: dict[str, Any] = detalle

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuracion
        return f"ErrorDeDominio({self.codigo.value}, {self.detalle!r})"


class SinAlcanceDeInquilino(RuntimeError):
    """Se intento una consulta sin `coach_id` en el contexto. Falla ruidoso, nunca silencioso."""

    codigo = Codigo.SIN_ALCANCE_DE_INQUILINO
