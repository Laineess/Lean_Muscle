"""Traduccion de errores de dominio a respuestas HTTP.

Convencion del proyecto: el dominio devuelve un `Codigo`; **este archivo es el unico lugar
donde vive el texto que lee la usuaria**. Cambiar una redaccion no obliga a tocar reglas de
negocio, y una regla nueva sin texto se nota de inmediato.
"""

from __future__ import annotations

from app.compartido.errores import Codigo

#: Codigo -> (estado HTTP, texto para la usuaria).
#: El estado sale del documento de requerimientos: 422 para dato invalido, 409 para
#: conflicto de estado, 403 para guarda de acceso.
RESPUESTAS: dict[Codigo, tuple[int, str]] = {
    # Captura biometrica
    Codigo.PESO_FUERA_DE_RANGO: (
        422,
        "Ese peso está fuera de rango. Aceptamos entre 30.0 y 250.0 kg.",
    ),
    Codigo.MEDIDA_FUERA_DE_RANGO: (
        422,
        "Esa medida está fuera de rango. Revisa cómo pusiste la cinta.",
    ),
    Codigo.MEDIDA_EN_CERO: (422, "Ninguna medida puede quedar en cero."),
    Codigo.ESTATURA_FUERA_DE_RANGO: (422, "La estatura debe estar entre 100 y 250 cm."),
    Codigo.PESAJE_DUPLICADO_EN_FECHA: (
        409,
        "Ya registraste tu peso hoy. Si te equivocaste, corrige el que ya está.",
    ),
    Codigo.PESAJES_DEL_CICLO_AGOTADOS: (
        409,
        "Ya tienes tres pesajes en este ciclo, que es el máximo.",
    ),
    Codigo.VARIANZA_DE_PESO_SIN_CONFIRMAR: (
        422,
        "El cambio de peso es mayor de lo habitual. Confirma el dato o vuelve a pesarte.",
    ),
    # Maquina de estados del chequeo
    Codigo.MEDIDAS_INCOMPLETAS: (422, "Faltan medidas por capturar. Se envían las ocho completas."),
    Codigo.FOTOS_INCOMPLETAS: (
        422,
        "Faltan fotos. Se necesitan las tres: frontal, perfil y espalda.",
    ),
    Codigo.FOTO_ANGULO_DUPLICADO: (
        409,
        "Ya hay una foto de ese ángulo. Bórrala antes de subir otra.",
    ),
    Codigo.PESO_Y_FOTOS_EN_DIAS_DISTINTOS: (
        422,
        "Tu peso y tus fotos tienen que ser del mismo día para poder compararlos.",
    ),
    Codigo.TRANSICION_NO_PERMITIDA: (409, "Ese cambio no aplica al estado actual del chequeo."),
    Codigo.MOTIVO_DE_RECHAZO_REQUERIDO: (
        422,
        "Escribe el motivo del rechazo: es lo que la alumna va a leer.",
    ),
    Codigo.JUSTIFICACION_DE_OUTLIER_REQUERIDA: (
        422,
        "Para sobrescribir la alerta de outlier hace falta una justificación técnica.",
    ),
    Codigo.AYUNO_SIN_CONFIRMAR: (422, "Confirma las condiciones del chequeo antes de continuar."),
    # Calculadora metabolica
    Codigo.PORCENTAJE_DE_GRASA_INVALIDO: (
        422,
        "El porcentaje de grasa tiene que estar entre 1 % y 99 %.",
    ),
    Codigo.REPARTO_DE_MACROS_NO_SUMA_UNO: (
        422,
        "El reparto de macros tiene que sumar exactamente 100 %.",
    ),
    Codigo.DIAS_DE_REFEED_FUERA_DE_RANGO: (422, "Los días de refeed van de 0 a 2 por semana."),
    Codigo.OBJETIVO_DE_GRASA_NO_ES_MENOR: (
        422,
        "El porcentaje de grasa objetivo tiene que ser menor que el actual.",
    ),
    Codigo.PROYECCION_SIN_DEFICIT: (
        409,
        "La proyección de pérdida necesita un ajuste calórico en déficit.",
    ),
    Codigo.PROYECCION_SIN_SUPERAVIT: (
        409,
        "La proyección de ganancia necesita un ajuste calórico en superávit.",
    ),
    Codigo.SIN_PORCENTAJE_DE_GRASA_DEL_CHEQUEO: (
        409,
        "Falta estimar el porcentaje de grasa de este chequeo para poder calcular el plan.",
    ),
    # Agenda
    Codigo.CITA_RANGO_INVALIDO: (422, "La hora de fin tiene que ser posterior a la de inicio."),
    Codigo.CITA_DURACION_INVALIDA: (422, "La duración de la cita está fuera de lo razonable."),
    Codigo.CITA_EN_EL_PASADO: (422, "No se puede agendar una cita en el pasado."),
    Codigo.CITA_SE_SOLAPA: (409, "Ya tienes algo agendado a esa hora."),
    Codigo.MOTIVO_DE_CANCELACION_REQUERIDO: (
        422,
        "Escribe el motivo de la cancelación: la alumna lo va a leer.",
    ),
    Codigo.HORARIO_INVALIDO: (
        422,
        "Revisa ese tramo: la hora de fin tiene que ir después de la de inicio.",
    ),
    Codigo.HUECO_NO_DISPONIBLE: (
        409,
        "Ese horario ya se ocupó. Elige otro de los que quedan libres.",
    ),
    Codigo.SIN_HORARIO_DE_ATENCION: (
        409,
        "Tu coach todavía no publica sus horarios de consulta.",
    ),
    Codigo.TRAMOS_ENCIMADOS: (
        422,
        "Tienes dos tramos encimados el mismo día. Únelos o sepáralos.",
    ),
    # Registro abierto
    Codigo.REGISTRO_CERRADO: (
        403,
        "Esta liga de registro no está disponible. Pídele a tu coach que la active.",
    ),
    Codigo.SIN_PRECIO_DE_INSCRIPCION: (
        409,
        "Falta definir el precio de inscripción: tiene que haber uno y solo uno.",
    ),
    Codigo.CODIGO_INCORRECTO: (422, "Ese código no es. Revísalo y vuelve a escribirlo."),
    Codigo.CODIGO_VENCIDO: (409, "El código caducó. Pide uno nuevo y te lo mandamos."),
    Codigo.DEMASIADOS_REGISTROS: (
        429,
        "Ya hubo varios registros desde aquí. Inténtalo dentro de un rato.",
    ),
    Codigo.SOLICITUD_YA_DECIDIDA: (409, "Esa solicitud ya se resolvió."),
    Codigo.SOLICITUD_SIN_ACEPTAR: (
        403,
        "Tu coach todavía no acepta tu solicitud. Esto se abre en cuanto lo haga.",
    ),
    # Finanzas
    Codigo.MONTO_INVALIDO: (422, "El monto tiene que ser mayor que cero."),
    Codigo.MONTO_FUERA_DE_RANGO: (422, "Ese monto está fuera de lo razonable. Revisa los ceros."),
    Codigo.CATEGORIA_INVALIDA: (422, "Esa categoría no corresponde al tipo de movimiento."),
    Codigo.CONCEPTO_REQUERIDO: (
        422,
        "Escribe un concepto: sin él el movimiento no se entiende después.",
    ),
    Codigo.MOVIMIENTO_AUTOMATICO_NO_EDITABLE: (
        409,
        "Este ingreso viene de un pago validado. Corrígelo en el pago, no aquí.",
    ),
    Codigo.DURACION_DE_TARIFA_INVALIDA: (
        422,
        "La duración del plan debe estar entre 1 y 365 días.",
    ),
    # Alta y cuenta
    Codigo.CORREO_YA_REGISTRADO: (409, "Ese correo ya tiene una cuenta."),
    Codigo.CORREO_INVALIDO: (422, "Ese correo no parece válido."),
    Codigo.LIMITE_DE_ALUMNAS_ALCANZADO: (409, "Alcanzaste el límite de alumnas de tu plan."),
    Codigo.CONTRASENA_DEBIL: (
        422,
        "La contraseña necesita al menos 8 caracteres, con un número y un carácter especial.",
    ),
    Codigo.CONTRASENA_ACTUAL_INCORRECTA: (422, "Tu contraseña actual no es correcta."),
    # Guardas de plan y ciclo
    Codigo.CHEQUEO_ANTERIOR_SIN_VALIDAR: (
        409,
        "Antes de publicar un plan nuevo hay que validar el chequeo anterior.",
    ),
    Codigo.SIN_FOTOS_APROBADAS: (409, "Sin fotos aprobadas no se genera ni se ajusta ningún plan."),
    Codigo.PLAN_SIN_CALORIAS: (422, "Falta el objetivo de calorías."),
    Codigo.PLAN_SIN_MACROS: (422, "Falta la distribución de macronutrientes."),
    Codigo.MACROS_NO_CUADRAN_CON_CALORIAS: (
        422,
        "Los macros no cuadran con las calorías del objetivo.",
    ),
    Codigo.CICLO_VENCIDO: (403, "Tu ciclo terminó. Renueva para seguir viendo tu plan."),
    Codigo.PAGO_SIN_VALIDAR: (
        403,
        "Tu pago todavía no ha sido validado. En cuanto tu coach lo confirme se desbloquea.",
    ),
    # Perfil, consentimientos y acceso
    Codigo.CUESTIONARIO_INCOMPLETO: (403, "Completa tu cuestionario inicial antes de empezar."),
    Codigo.CONSENTIMIENTO_FALTANTE: (403, "Falta uno de los consentimientos obligatorios."),
    Codigo.PROTOCOLO_FOTO_RECHAZADO: (
        403,
        "Sin aceptar el protocolo fotográfico no se puede crear tu plan.",
    ),
    Codigo.MENOR_DE_EDAD: (403, "El servicio es solo para mayores de 18 años."),
    Codigo.CREDENCIALES_INVALIDAS: (401, "Correo o contraseña incorrectos."),
    Codigo.SESION_EXPIRADA: (401, "Tu sesión expiró. Vuelve a entrar."),
    Codigo.CONTRASENA_INICIAL_SIN_CAMBIAR: (
        403,
        "Antes de nada, cambia la contraseña con la que te dieron de alta.",
    ),
    Codigo.CLAVE_INICIAL_VENCIDA: (
        401,
        "Esa contraseña ya venció. Pídele a tu coach que te la vuelva a generar.",
    ),
    Codigo.DEMASIADOS_INTENTOS: (
        429,
        "Demasiados intentos fallidos. Espera unos minutos antes de volver a probar.",
    ),
    Codigo.SIN_PERMISO: (403, "No tienes permiso para ver esto."),
    # Aislamiento
    Codigo.SIN_ALCANCE_DE_INQUILINO: (500, "Error interno. El equipo ya fue notificado."),
}


def respuesta_para(codigo: Codigo) -> tuple[int, str]:
    """Estado y texto de un codigo. Un codigo sin texto es un error de programacion."""
    if codigo not in RESPUESTAS:  # pragma: no cover - lo cubre la prueba de cobertura
        raise KeyError(f"{codigo} no tiene texto para la usuaria en RESPUESTAS")
    return RESPUESTAS[codigo]
