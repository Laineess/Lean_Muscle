"""Contrato de la API.

Los nombres salen en `camelCase` porque es lo que consume TypeScript, pero el dominio y la
base siguen en `snake_case`: la traducción vive aquí y en ningún otro lado.

**Ningún esquema expone la llave interna ni el `coach_id`.** Hacia afuera solo viaja el
ULID: quien reciba una respuesta no debe poder enumerar alumnas cambiando un número, ni
deducir cuántos inquilinos hay.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel

#: Un `Decimal` sale de Pydantic como cadena, y del otro lado TypeScript los declara
#: `number`: sumar dos importes concatenaba en vez de sumar. Se serializan como número.
Numero = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class Esquema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        ser_json_timedelta="iso8601",
    )


# ---------------------------------------------------------------------------
# Identidad
# ---------------------------------------------------------------------------


class Credenciales(Esquema):
    correo: str
    contrasena: str
    #: No guarda la contraseña en el navegador: alarga la vigencia de la cookie de sesión.
    recordarme: bool = False


class ActorPublico(Esquema):
    rol: str
    nombre: str
    correo: str
    #: Reemplaza al dorado de MyProgressPlan en toda la interfaz de sus alumnas.
    color_acento: str
    marca: str


# ---------------------------------------------------------------------------
# Chequeos y medidas
# ---------------------------------------------------------------------------


class MedidaPublica(Esquema):
    tipo: str
    valor: Numero


class ChequeoPublico(Esquema):
    ulid: str
    numero: int
    fecha: date
    estado: str
    peso_kg: Numero | None
    porcentaje_grasa: Numero | None
    medidas: dict[str, Numero]
    fotos: dict[str, bool]
    feedback: str | None
    alerta_outlier: bool


class PesajePublico(Esquema):
    fecha: date
    peso_kg: Numero


# ---------------------------------------------------------------------------
# Frente de alumna
# ---------------------------------------------------------------------------


class CicloPublico(Esquema):
    numero: int
    inicia_en: date
    termina_en: date
    estado_pago: str
    precio: Numero


class PerfilAlumna(Esquema):
    ulid: str
    nombre: str
    correo: str
    estatura_cm: int | None
    plan: str | None
    bascula_ref: str | None
    lugar_ref: str | None
    hora_ref: str | None
    zona_horaria: str
    #: Falso hasta que contesta el cuestionario inicial. Es lo que decide si al entrar ve
    #: primero la presentación de su coach.
    cuestionario_completo: bool = True


class CitaDeAlumna(Esquema):
    """Una cita vista por la alumna. Sin las notas de la coach, que son suyas."""

    ulid: str
    titulo: str
    modalidad: str
    estado: str
    inicia_en: datetime
    termina_en: datetime


class InicioAlumna(Esquema):
    """Todo lo que pinta la pantalla de inicio, en una sola llamada.

    Una pantalla, una petición: la alumna la abre en el celular con mala señal, y tres
    llamadas en cascada se sienten mucho peor que una sola un poco más grande.
    """

    perfil: PerfilAlumna
    ciclo: CicloPublico | None
    chequeos: list[ChequeoPublico]
    ultimo_feedback: str | None
    avisos_sin_leer: int
    coach: str
    #: Lo que viene: sirve para el cuadro de próximas fechas del inicio.
    proximas_citas: list[CitaDeAlumna]


class PlanPublico(Esquema):
    tipo: str
    ciclo: int
    estado: str
    publicado_en: datetime | None
    contenido: dict[str, object]
    kcal_objetivo: int | None
    proteina_g: int | None
    carbohidrato_g: int | None
    grasa_g: int | None


class PlanesDeAlumna(Esquema):
    #: Nulo cuando el ciclo está bloqueado: la guarda vive en el servidor.
    nutricion: PlanPublico | None
    entrenamiento: PlanPublico | None
    bloqueado_por_pago: bool
    #: `pago`, `ciclo_vencido`, `sin_ciclo` o nulo. Sin esto la pantalla decía «falta tu
    #: comprobante» a quien ya había pagado y solo tenía el ciclo terminado.
    motivo_bloqueo: str | None
    restricciones: str | None
    lesiones: str | None


# ---------------------------------------------------------------------------
# Frente de coach
# ---------------------------------------------------------------------------


class FilaCartera(Esquema):
    ulid: str
    nombre: str
    ciclo: int
    estado: str
    chequeo_estado: str | None
    chequeo_fecha: date | None
    peso_kg: Numero | None
    peso_previo: Numero | None
    #: Nombre del plan comercial que contrató. Sustituye al antiguo objetivo.
    plan: str | None
    pago: str
    ultimo_acceso: date | None
    alerta: str | None
    #: Cuánto debe en cobros vencidos. Cero significa al corriente.
    adeudo: Numero


class ResumenPanel(Esquema):
    coach: str
    marca: str
    plan: str
    limite_alumnas: int
    precio_ciclo: Numero
    por_validar: list[FilaCartera]
    con_alerta: list[FilaCartera]
    activas: int
    por_cobrar: int


class CitaPublica(Esquema):
    ulid: str
    titulo: str
    tipo: str
    estado: str
    modalidad: str
    alumna_ulid: str | None
    alumna_nombre: str | None
    inicia_en: datetime
    termina_en: datetime
    notas: str | None
    motivo_cancelacion: str | None


class CitaNueva(Esquema):
    titulo: str
    tipo: str = "consulta"
    modalidad: str = "video"
    alumna_ulid: str | None = None
    inicia_en: datetime
    termina_en: datetime
    notas: str | None = None


class CancelacionCita(Esquema):
    motivo: str


class AltaDeAlumna(Esquema):
    """Lo que la coach captura al dar de alta.

    **No incluye datos de salud a propósito**: el historial clínico y los consentimientos los
    llena la propia alumna al entrar. Que la coach los capture por ella viciaría el
    consentimiento, que la ley exige expreso y personal para datos sensibles.
    """

    nombre: str
    correo: str
    whatsapp: str | None = None
    fecha_nacimiento: date
    estatura_cm: int | None = None
    #: ULID del plan comercial. Es lo que determina cuánto se le cobra.
    tarifa_ulid: str | None = None
    nivel_experiencia: str | None = None


class AlumnaDadaDeAlta(Esquema):
    alumna_ulid: str
    correo: str
    #: Se devuelve una sola vez, para que la coach pueda dictarla si el correo no llega.
    clave_temporal: str


class EdicionDeAlumna(Esquema):
    nombre: str
    whatsapp: str | None = None
    estatura_cm: int | None = None
    tarifa_ulid: str | None = None
    nivel_experiencia: str | None = None
    equipo: str | None = None
    ocupacion: str | None = None
    bascula_ref: str | None = None
    lugar_ref: str | None = None
    hora_ref: str | None = None
    zona_horaria: str | None = None
    porcentaje_grasa_objetivo: Numero | None = None
    estado: str | None = None


class ClaveTemporalPedida(Esquema):
    #: Cómo verificó la coach que era ella. Sin este registro, entregar una clave por
    #: WhatsApp es indistinguible de entregársela a quien se hizo pasar por la alumna.
    motivo_verificacion: str


class ClaveTemporalEmitida(Esquema):
    clave: str
    vence_en: datetime


class CambioDeContrasena(Esquema):
    actual: str
    nueva: str


# ---------------------------------------------------------------------------
# Finanzas
# ---------------------------------------------------------------------------


class MovimientoPublico(Esquema):
    ulid: str
    tipo: str
    categoria: str
    monto: Numero
    fecha: date
    concepto: str
    alumna_ulid: str | None
    alumna_nombre: str | None
    #: Generado al validar un pago: no se edita a mano.
    automatico: bool
    nota: str | None


class MovimientoNuevo(Esquema):
    tipo: str
    categoria: str
    monto: Numero
    fecha: date
    concepto: str
    alumna_ulid: str | None = None
    nota: str | None = None
    #: Cobro programado que salda este ingreso. Al registrarlo, ese cobro pasa a pagado.
    cobro_ulid: str | None = None


class TotalPorCategoria(Esquema):
    categoria: str
    monto: Numero


class ResumenMes(Esquema):
    mes: str
    ingresos: Numero
    gastos: Numero
    utilidad: Numero


class PanelFinanciero(Esquema):
    ingresos: Numero
    gastos: Numero
    utilidad: Numero
    #: Fracción de los ingresos que queda como utilidad.
    margen: Numero
    ingreso_por_alumna: Numero
    #: Ingreso esperado si todas renuevan. **Es proyección, no dato**, y la pantalla lo dice.
    proyeccion_mensual: Numero
    alumnas_activas: int
    por_mes: list[ResumenMes]
    ingresos_por_categoria: list[TotalPorCategoria]
    gastos_por_categoria: list[TotalPorCategoria]
    movimientos: list[MovimientoPublico]


class TarifaPublica(Esquema):
    ulid: str
    codigo: str
    nombre: str
    descripcion: str | None
    precio: Numero
    dias: int
    activa: bool


class TarifaNueva(Esquema):
    codigo: str
    nombre: str
    descripcion: str | None = None
    precio: Numero
    dias: int = 30
    activa: bool = True


# ---------------------------------------------------------------------------
# Planes editables
# ---------------------------------------------------------------------------


class AlimentoCatalogo(Esquema):
    ulid: str
    nombre: str
    marca: str | None
    porcion: Numero
    unidad: str
    kcal: Numero
    proteina: Numero
    carbo: Numero
    grasa: Numero
    grupo: str | None
    #: `false` = viene de la base pública compartida por todas las coaches.
    propio: bool


class AlimentoNuevo(Esquema):
    nombre: str
    marca: str | None = None
    porcion: Numero
    unidad: str = "g"
    kcal: Numero
    proteina: Numero = Decimal(0)
    carbo: Numero = Decimal(0)
    grasa: Numero = Decimal(0)
    grupo: str | None = None


class EjercicioCatalogo(Esquema):
    ulid: str
    nombre: str
    grupo: str | None
    equipo: str | None
    patron: str | None
    tiene_video: bool
    contraindicaciones: str | None
    propio: bool


class RepartoDeMacros(Esquema):
    """Fracciones que suman 1. La base lo exige con un CHECK."""

    carbohidrato: Numero
    proteina: Numero
    grasa: Numero


class ParametrosDeCiclo(Esquema):
    """Las entradas de la calculadora. Se guardan con el plan para que el ciclo siguiente
    arranque de lo que la coach dejó, no de valores por omisión."""

    actividad: str
    porcentaje_ajuste: Numero
    reparto: RepartoDeMacros
    base_proteina: str
    dias_refeed: int
    porcentaje_dia_refeed: Numero
    relacion_ganancia: str


class PlanGuardado(Esquema):
    """El contenido va como JSON libre: su forma cambia seguido —tiempos de comida, días,
    bloques— y no se consulta por dentro, se lee completo."""

    tipo: str
    contenido: dict[str, object]
    kcal_objetivo: int | None = None
    proteina_g: int | None = None
    carbohidrato_g: int | None = None
    grasa_g: int | None = None
    publicar: bool = False
    #: Solo viajan con el plan de nutrición, que es donde vive la calculadora.
    parametros: ParametrosDeCiclo | None = None


class ChequeoDelConstructor(Esquema):
    """El último chequeo. Peso y grasa son las entradas que mandan toda la cadena."""

    fecha: date
    estado: str
    peso_kg: Numero | None
    porcentaje_grasa: Numero | None


class ExpedienteDeConstructor(Esquema):
    """Todo lo que necesita el constructor de planes, en una sola llamada."""

    alumna_ulid: str
    alumna: str
    ciclo: int
    fecha_nacimiento: date
    sexo: str | None
    estatura_cm: int | None
    porcentaje_grasa_objetivo: Numero | None
    chequeo: ChequeoDelConstructor | None
    parametros: ParametrosDeCiclo
    nutricion: PlanPublico | None
    entrenamiento: PlanPublico | None


class FotoPublica(Esquema):
    """Metadatos de la fotografía. **La imagen no viaja aquí**: se pide por su propia ruta,
    y esa lectura vuelve a quedar registrada."""

    angulo: str
    #: Nula si ya se purgó: la fila sobrevive con fecha y motivo, la imagen no.
    disponible: bool
    nitidez: Numero | None
    luminancia: Numero | None
    estado_auto: str
    es_linea_base: bool
    tomada_en: datetime | None
    purgada_en: datetime | None
    dias_para_purga: int | None


class HistorialPublico(Esquema):
    lesiones: str | None
    condiciones: str | None
    medicacion: str | None
    restricciones: str | None
    vigente_desde: datetime
    #: Cuántas versiones hay. El historial no se sobrescribe: se inserta una nueva.
    versiones: int


class ComprobanteLeido(Esquema):
    """Lo que el OCR entendió. **No es una validación**: la coach confirma siempre."""

    pago_ulid: str
    monto: Numero | None
    fecha: date | None
    referencia: str | None
    banco: str | None
    confianza: Numero
    #: Bajo 85 % conviene mirar el comprobante a ojo antes de confirmar.
    requiere_revision: bool


class SuscripcionNueva(Esquema):
    """Lo que entrega `PushManager.subscribe()` en el navegador."""

    endpoint: str
    p256dh: str
    auth: str


class MensajePublico(Esquema):
    ulid: str
    autor: str
    cuerpo: str
    enviado_en: datetime
    leido_en: datetime | None


class MensajeNuevo(Esquema):
    cuerpo: str


class EstimacionGrasa(Esquema):
    porcentaje_grasa: Numero


# ---------------------------------------------------------------------------
# Captura del chequeo (frente de alumna)
# ---------------------------------------------------------------------------


class FotoDeBorrador(Esquema):
    """Estado de una toma. La imagen no viaja aquí: se pide por su propia ruta."""

    angulo: str
    estado_auto: str
    motivo_rechazo: str | None = None
    nitidez: Numero | None
    luminancia: Numero | None
    tomada_en: datetime | None


class BorradorChequeo(Esquema):
    """Todo lo que el flujo de captura necesita, en una sola llamada.

    Incluye los valores del chequeo anterior porque la pantalla los muestra al lado de cada
    campo: pedirlos aparte sería una segunda petición en un teléfono con mala señal.
    """

    ulid: str
    numero: int
    fecha: date
    estado: str
    ayuno_confirmado: bool
    varianza_confirmada: bool
    nota_alumna: str | None
    peso_kg: Numero | None
    medidas: dict[str, Numero]
    fotos: list[FotoDeBorrador]
    pesajes: list[PesajePublico]
    max_pesajes: int

    peso_anterior_kg: Numero | None
    medidas_anteriores: dict[str, Numero]

    bascula_ref: str | None
    lugar_ref: str | None
    hora_ref: str | None
    bascula_usada: str | None
    lugar_usado: str | None
    hora_usada: str | None


class GuardadoDeChequeo(Esquema):
    """Lo que la pantalla guarda entre pasos. Todo opcional: es un borrador."""

    ayuno_confirmado: bool | None = None
    peso_kg: Numero | None = None
    varianza_confirmada: bool | None = None
    medidas: dict[str, Numero] | None = None
    nota_alumna: str | None = None
    bascula_usada: str | None = None
    lugar_usado: str | None = None
    hora_usada: str | None = None


class EnvioRechazado(Esquema):
    """Por qué no se pudo enviar. Van **todas** las causas, no la primera."""

    errores: list[dict[str, object]]
    campos_faltantes: dict[str, list[str]]


class LlavePush(Esquema):
    """Llave pública VAPID. Es pública por definición: viaja al navegador."""

    publica: str


class ValidacionChequeo(Esquema):
    feedback: str
    justificacion_outlier: str | None = None


class RechazoChequeo(Esquema):
    motivo: str


# ---------------------------------------------------------------------------
# Panel de plataforma (superadmin)
# ---------------------------------------------------------------------------


class SuscripcionPublica(Esquema):
    plan: str
    precio: Numero
    periodicidad: str
    estado: str
    inicia_en: date
    vigente_hasta: date | None
    nota: str | None


class FilaDeCoach(Esquema):
    """Una coach vista desde la plataforma.

    **Solo agregados.** Ninguna de estas cifras permite llegar a una alumna concreta: son
    cuántas, no quiénes. Es la línea que sostiene que la plataforma sea Encargado y no
    Responsable frente a la LFPDPPP.
    """

    ulid: str
    nombre: str
    #: Nombre comercial que ven las alumnas. Puede no ser el de la persona.
    marca: str
    slug: str
    email: str
    plan: str
    limite_alumnas: int
    estado: str
    precio_ciclo: Numero
    creado_en: datetime

    alumnas: int
    alumnas_activas: int
    chequeos_por_validar: int
    chequeos_del_mes: int
    fotos: int
    mb_fotos: int
    ultimo_acceso: datetime | None
    #: Días sin que nadie de esa cuenta entre. Nulo si nunca ha entrado nadie.
    dias_inactiva: int | None

    suscripcion: SuscripcionPublica | None


class AltaDeCoach(Esquema):
    nombre: str
    #: Vacío = se usa el nombre. Es lo que ven sus alumnas en la barra y en los correos.
    marca: str = ""
    email: str
    slug: str | None = None
    plan: str = "basico"
    limite_alumnas: int = 50
    precio_ciclo: Numero = Decimal(0)
    color_acento: str = "#c9a227"
    zona_horaria: str = "America/Mexico_City"


class CoachDadaDeAlta(Esquema):
    coach_ulid: str
    email: str
    #: Se devuelve una sola vez. Después solo queda su hash.
    clave_temporal: str


class EdicionDeCoach(Esquema):
    nombre: str
    marca: str
    plan: str
    limite_alumnas: int
    estado: str
    precio_ciclo: Numero
    color_acento: str


class EdicionDeSuscripcion(Esquema):
    plan: str
    precio: Numero
    periodicidad: str
    estado: str
    vigente_hasta: date | None = None
    nota: str | None = None


class CobroPublico(Esquema):
    ulid: str
    coach_ulid: str
    monto: Numero
    fecha: date
    metodo: str
    periodo_inicia: date | None
    periodo_termina: date | None
    nota: str | None


class CobroNuevo(Esquema):
    monto: Numero
    fecha: date
    metodo: str = "transferencia"
    periodo_inicia: date | None = None
    periodo_termina: date | None = None
    nota: str | None = None


class ResumenDeFacturacion(Esquema):
    cobrado_en_el_ano: Numero
    facturacion_mensual_esperada: Numero
    coaches_al_corriente: int
    coaches_vencidas: int
    coaches_en_cortesia: int
    por_mes: list[ResumenMes]


class SaludPublica(Esquema):
    """Lo que falla en silencio. Es lo que hay que mirar una vez al mes."""

    avisos_pendientes: int
    avisos_agotados: int
    ultimo_aviso_enviado: datetime | None
    fotos_por_purgar: int
    mb_totales: int
    suscripciones_push: int
    sesiones_vivas: int
    coaches_activas: int
    coaches_inactivas: int


class MovimientoDeAuditoria(Esquema):
    """Sin `detalle` ni identificador de entidad: solo qué se hizo y en qué cuenta."""

    cuando: datetime
    coach: str
    actor_tipo: str
    accion: str
    entidad: str


# ---------------------------------------------------------------------------
# Marca de la coach
# ---------------------------------------------------------------------------


class MarcaPublica(Esquema):
    nombre: str
    marca: str
    color_acento: str
    #: Nulo mientras no haya subido logo. La interfaz cae a las iniciales.
    tiene_logo: bool


class EdicionDeMarca(Esquema):
    nombre: str
    marca: str
    color_acento: str


class DatoDeFicha(Esquema):
    """Un renglón de la ficha. La coach nombra el rótulo: no hay campos impuestos."""

    rotulo: str
    valor: str


class PresentacionPublica(Esquema):
    """Lo que la alumna ve antes del cuestionario."""

    titulo: str
    texto: str
    ficha: list[DatoDeFicha]
    activa: bool
    tiene_foto: bool
    #: Nombre comercial y color, para que la pantalla se pinte con su marca.
    marca: str
    color_acento: str


class EdicionDePresentacion(Esquema):
    titulo: str
    texto: str
    ficha: list[DatoDeFicha]
    activa: bool = True


# ---------------------------------------------------------------------------
# Cuestionario inicial
# ---------------------------------------------------------------------------


class PreguntaPublica(Esquema):
    ulid: str
    texto: str
    ayuda: str | None
    #: `texto`, `texto_largo`, `numero`, `opcion` o `si_no`.
    tipo: str
    opciones: list[str]
    obligatoria: bool
    orden: int
    activa: bool


class PreguntaNueva(Esquema):
    texto: str
    ayuda: str | None = None
    tipo: str = "texto"
    opciones: list[str] = []
    obligatoria: bool = False
    orden: int = 0
    activa: bool = True


class NucleoClinico(Esquema):
    """La parte que no se puede quitar: la exige la ley y la consulta el plan."""

    lesiones: str | None = None
    condiciones: str | None = None
    medicacion: str | None = None
    restricciones: str | None = None


class RespuestaDePregunta(Esquema):
    pregunta_ulid: str
    valor: str


class CuestionarioParaAlumna(Esquema):
    """El cuestionario tal como lo ve la alumna, con lo que ya hubiera contestado."""

    completo: bool
    nucleo: NucleoClinico
    preguntas: list[PreguntaPublica]
    respuestas: list[RespuestaDePregunta]
    #: Los que todavía tiene que aceptar. Vacío si ya los aceptó todos.
    consentimientos_pendientes: list[str]


class EnvioDeCuestionario(Esquema):
    nucleo: NucleoClinico
    respuestas: list[RespuestaDePregunta] = []
    #: Tipos de consentimiento que acepta en este envío.
    consentimientos: list[str] = []


class RespuestaDeAlumna(Esquema):
    """Una respuesta vista por la coach, con su pregunta al lado."""

    pregunta: str
    tipo: str
    valor: str


# ---------------------------------------------------------------------------
# La calculadora con la forma de la hoja original
# ---------------------------------------------------------------------------


class CeldaDeHoja(Esquema):
    celda: str
    rotulo: str
    #: Ya formateado como lo enseña Excel. La coach compara de un vistazo, no opera con él.
    valor: str
    unidad: str
    #: La fórmula del archivo, tal cual. Solo para leerla.
    formula: str
    capturado: bool


class BloqueDeHoja(Esquema):
    titulo: str
    rango: str
    celdas: list[CeldaDeHoja]


class TablaDeHoja(Esquema):
    titulo: str
    rango: str
    encabezados: list[str]
    filas: list[list[str]]


class HojaDeCalculo(Esquema):
    """La hoja completa. Nula solo si falta el chequeo del que salen peso y grasa."""

    alumna: str
    bloques: list[BloqueDeHoja]
    tablas: list[TablaDeHoja]
    #: Por qué no se puede calcular todavía, si es el caso.
    falta: str | None = None


# ---------------------------------------------------------------------------
# Expediente de validación
# ---------------------------------------------------------------------------


class ChequeoDeValidacion(Esquema):
    """Un chequeo con todo lo que la coach mira para validarlo."""

    ulid: str
    numero: int
    fecha: date
    estado: str
    peso_kg: Numero | None
    porcentaje_grasa: Numero | None
    medidas: dict[str, Numero]
    nota_alumna: str | None
    alerta_outlier: bool
    varianza_confirmada: bool
    bascula_usada: str | None
    lugar_usado: str | None
    hora_usada: str | None


class ExpedienteDeValidacion(Esquema):
    """Todo lo que pinta la pantalla de validación, en una sola llamada."""

    alumna_ulid: str
    alumna: str
    estatura_cm: int | None
    plan: str | None
    #: El que toca validar. Nulo si no hay ninguno pendiente.
    actual: ChequeoDeValidacion | None
    #: Los anteriores, del más viejo al más nuevo, para el selector de comparación.
    anteriores: list[ChequeoDeValidacion]
    lesiones: str | None
    restricciones: str | None


# ---------------------------------------------------------------------------
# Documentos legales
# ---------------------------------------------------------------------------


class DocumentoLegal(Esquema):
    """El texto tal cual está en `docs/`, en Markdown.

    `marcadores` lleva los huecos sin rellenar. Un aviso de privacidad con huecos no cumple
    la LFPDPPP, así que la pantalla lo dice en vez de aparentar que está terminado.
    """

    clave: str
    titulo: str
    version: str
    actualizado: str
    contenido: str
    marcadores: list[str]


# ---------------------------------------------------------------------------
# Planes comerciales y cobros programados
# ---------------------------------------------------------------------------


class PlanComercial(Esquema):
    """Lo que la coach vende. `Tarifa` en la base; se llama plan hacia afuera porque `Plan`
    ya es el de nutrición y entrenamiento."""

    ulid: str
    codigo: str
    nombre: str
    descripcion: str | None
    precio: Numero
    dias: int
    #: `baja`, `media` o `alta`. Descriptiva: no la usa ningún cálculo.
    intensidad: str
    activa: bool
    #: Cuántas alumnas lo tienen contratado. Desactivar uno con alumnas dentro es un error.
    alumnas: int


class PlanComercialNuevo(Esquema):
    codigo: str
    nombre: str
    descripcion: str | None = None
    precio: Numero
    dias: int = 30
    intensidad: str = "media"
    activa: bool = True


class CobroDeAlumna(Esquema):
    ulid: str
    fecha: date
    motivo: str
    concepto: str
    monto: Numero
    #: `pendiente`, `en_revision`, `pagado` o `cancelado`.
    estado: str
    pagado_en: date | None
    nota: str | None
    #: `vencido` cuando la fecha pasó y sigue sin pagarse. Es lo que pausa el plan.
    vencido: bool
    tiene_comprobante: bool
    #: Por qué se rechazó el comprobante anterior, si lo hubo. La alumna lo lee tal cual.
    motivo_rechazo: str | None = None


class CobroNuevoProgramado(Esquema):
    fecha: date
    motivo: str = "mensualidad"
    concepto: str | None = None
    monto: Numero
    nota: str | None = None


class AlumnaConCobros(Esquema):
    """Lo que devuelve el buscador de finanzas: a quién cobrar y qué le falta."""

    ulid: str
    nombre: str
    plan: str | None
    pendientes: list[CobroDeAlumna]
    adeudo: Numero


class ComprobantePorRevisar(Esquema):
    """Lo que la coach ve en su bandeja antes de abrir la imagen."""

    cobro_ulid: str
    alumna_ulid: str
    alumna: str
    plan: str | None
    fecha_cobro: date
    concepto: str
    #: Lo que la coach espera recibir.
    monto_esperado: Numero
    subido_en: datetime | None

    #: Lo que el OCR entendió del comprobante. **No valida nada**: es una sugerencia.
    monto_leido: Numero | None
    fecha_leida: date | None
    referencia: str | None
    banco: str | None
    confianza: Numero
    #: El OCR leyó un importe distinto al esperado. Mirar la imagen deja de ser opcional.
    monto_no_cuadra: bool


class RechazoDeComprobante(Esquema):
    motivo: str
