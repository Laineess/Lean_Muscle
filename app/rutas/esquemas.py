"""Contrato de la API. La traducción `snake_case` ↔ `camelCase` vive aquí y en ningún otro
lado, y ningún esquema expone la llave interna ni el `coach_id`: hacia afuera solo el ULID.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

#: Pydantic lo serializa como cadena y TypeScript lo declara `number`: sumar concatenaba.
Numero = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]

# Cada tope coincide con el ancho de su columna. Sin ellos MySQL corta con «Data too long»
# y la API devuelve un 500 en vez de un 422 que diga cuál es el campo.
Texto10 = Annotated[str, Field(max_length=10)]
Texto20 = Annotated[str, Field(max_length=20)]
Texto30 = Annotated[str, Field(max_length=30)]
Texto40 = Annotated[str, Field(max_length=40)]
Texto60 = Annotated[str, Field(max_length=60)]
Texto80 = Annotated[str, Field(max_length=80)]
Texto120 = Annotated[str, Field(max_length=120)]
Texto160 = Annotated[str, Field(max_length=160)]
Texto180 = Annotated[str, Field(max_length=180)]
Texto200 = Annotated[str, Field(max_length=200)]
Texto255 = Annotated[str, Field(max_length=255)]
Texto300 = Annotated[str, Field(max_length=300)]
Texto500 = Annotated[str, Field(max_length=500)]
#: Para columnas TEXT. El tope no es del motor: aceptar veinte mil caracteres regala disco.
TextoLargo = Annotated[str, Field(max_length=4000)]

#: Un entero que cabe en `Integer`. Nadie come 100 000 kcal, pero el motor sí revienta.
Gramos = Annotated[int, Field(ge=0, le=100000)]

#: Dinero en `Numeric(10, 2)`: ocho enteros y dos decimales. Un peso más y el motor corta.
Dinero = Annotated[Decimal, Field(gt=0, le=Decimal("99999999.99"))]
#: Igual, pero admite cero y negativos: los movimientos de finanzas pueden ser gasto.
Importe = Annotated[Decimal, Field(ge=Decimal("-99999999.99"), le=Decimal("99999999.99"))]


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
    correo: Texto180
    #: Sin tope: se cifra antes de guardarse y el hash de Argon2 siempre mide lo mismo.
    contrasena: str
    #: No guarda la contraseña en el navegador: alarga la vigencia de la cookie de sesión.
    recordarme: bool = False


class ActorPublico(Esquema):
    rol: str
    nombre: str
    correo: str
    #: Sus dos colores reemplazan a los de MyFittPlan en la interfaz de sus alumnas.
    color_acento: str
    color_secundario: str
    marca: str
    #: Entró con la contraseña inicial. Hasta que la cambie no se abre nada más.
    debe_cambiar_contrasena: bool = False
    #: Preferencia de idioma de la cuenta ("es" | "en").
    idioma: str = "es"


class IdiomaPreferido(Esquema):
    idioma: Literal["es", "en"]


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
    #: Falso hasta que lo contesta; decide si al entrar ve primero la presentación.
    cuestionario_completo: bool = True
    estado: str = "activa"
    #: Cuándo se borra su expediente. Solo va cuando está dada de baja.
    borra_en: datetime | None = None


class CitaDeAlumna(Esquema):
    """Una cita vista por la alumna. Sin las notas de la coach, que son suyas."""

    ulid: str
    titulo: str
    modalidad: str
    estado: str
    inicia_en: datetime
    termina_en: datetime


class ResumenDePlan(Esquema):
    """Si ya tiene plan y qué le toca hoy. Sin esto la pantalla pintaba una rutina de
    ejemplo a alumnas a las que nadie les había asignado nada."""

    publicado: bool
    kcal_objetivo: int | None
    dias_entrenamiento: int
    primer_dia: str | None


class InicioAlumna(Esquema):
    """La pantalla de inicio entera, en una llamada: en un celular con mala señal, tres
    peticiones en cascada se sienten peor que una sola más grande."""

    perfil: PerfilAlumna
    ciclo: CicloPublico | None
    chequeos: list[ChequeoPublico]
    ultimo_feedback: str | None
    avisos_sin_leer: int
    #: Título del último aviso sin leer, para no tener que pedir la lista solo para el banner.
    ultimo_aviso: str | None = None
    coach: str
    #: Lo que viene: sirve para el cuadro de próximas fechas del inicio.
    proximas_citas: list[CitaDeAlumna]
    #: Nulo mientras su coach no le haya publicado nada.
    plan: ResumenDePlan | None = None


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
    #: Cada cuánto se le piden fotos de sus comidas. Solo aplica al plan de nutrición.
    frecuencia_fotos: str = "ninguna"


class PlanesDeAlumna(Esquema):
    #: Nulo cuando el ciclo está bloqueado: la guarda vive en el servidor.
    nutricion: PlanPublico | None
    entrenamiento: PlanPublico | None
    bloqueado_por_pago: bool
    #: `pago`, `ciclo_vencido`, `sin_ciclo` o nulo. Sin distinguirlos, la pantalla le pedía
    #: comprobante a quien ya había pagado y solo tenía el ciclo terminado.
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


class MarcaDeCobro(Esquema):
    """Un cobro visto desde la agenda. No es una cita: no tiene hora ni ocupa hueco."""

    ulid: str
    fecha: date
    alumna_ulid: str
    alumna: str
    concepto: str
    monto: Numero
    estado: str
    vencido: bool


class AgendaDeCoach(Esquema):
    """Su semana completa: lo que atiende y lo que cobra, en una sola llamada."""

    citas: list[CitaPublica]
    cobros: list[MarcaDeCobro]


class CitaNueva(Esquema):
    titulo: Texto160
    tipo: Texto20 = "consulta"
    modalidad: Texto20 = "video"
    alumna_ulid: Texto30 | None = None
    inicia_en: datetime
    termina_en: datetime
    notas: TextoLargo | None = None


class CancelacionCita(Esquema):
    motivo: Texto255


class AltaDeAlumna(Esquema):
    """Lo que la coach captura al dar de alta. Sin datos de salud: capturarlos por ella
    viciaría el consentimiento, que la ley exige expreso y personal."""

    nombre: Texto120
    correo: Texto180
    whatsapp: Texto30 | None = None
    fecha_nacimiento: date
    #: El rango es el del CHECK de la tabla: fuera de él, el motor cortaba con un 500.
    estatura_cm: Annotated[int, Field(ge=100, le=250)] | None = None
    #: ULID del plan comercial. Es lo que determina cuánto se le cobra.
    tarifa_ulid: Texto30 | None = None
    nivel_experiencia: Texto20 | None = None


class AlumnaDadaDeAlta(Esquema):
    alumna_ulid: str
    correo: str
    #: Se devuelve una sola vez, para que la coach pueda dictarla si el correo no llega.
    clave_temporal: str


class PerfilEditable(Esquema):
    """Lo guardado hoy. El PUT escribe todos los campos, así que lo que el formulario no
    cargue de aquí se pierde al guardar."""

    ulid: str
    nombre: str
    correo: str
    whatsapp: str | None
    fecha_nacimiento: date
    estatura_cm: int | None
    tarifa_ulid: str | None
    nivel_experiencia: str | None
    equipo: str | None
    ocupacion: str | None
    bascula_ref: str | None
    lugar_ref: str | None
    hora_ref: str | None
    zona_horaria: str
    porcentaje_grasa_objetivo: Numero | None
    estado: str


class EdicionDeAlumna(Esquema):
    nombre: Texto120
    whatsapp: Texto30 | None = None
    estatura_cm: Annotated[int, Field(ge=100, le=250)] | None = None
    tarifa_ulid: Texto30 | None = None
    nivel_experiencia: Texto20 | None = None
    equipo: Texto30 | None = None
    ocupacion: Texto180 | None = None
    bascula_ref: Texto120 | None = None
    lugar_ref: Texto120 | None = None
    hora_ref: Texto20 | None = None
    zona_horaria: Texto60 | None = None
    porcentaje_grasa_objetivo: Annotated[Decimal, Field(gt=0, lt=1)] | None = None
    estado: Texto20 | None = None


class ClaveTemporalPedida(Esquema):
    #: Cómo verificó que era ella. Sin el registro, dictar la clave por WhatsApp es
    #: indistinguible de dársela a quien se hizo pasar por la alumna.
    motivo_verificacion: Texto255


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
    tipo: Texto20
    categoria: Texto30
    monto: Importe
    fecha: date
    concepto: Texto180
    alumna_ulid: Texto30 | None = None
    nota: TextoLargo | None = None
    #: Cobro programado que salda este ingreso. Al registrarlo, ese cobro pasa a pagado.
    cobro_ulid: Texto30 | None = None


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
    nombre: Texto160
    marca: Texto120 | None = None
    #: `Numeric(7, 2)` y `Numeric(6, 2)`: pasarse revienta contra el motor.
    porcion: Annotated[Decimal, Field(gt=0, lt=100000)]
    unidad: Texto10 = "g"
    kcal: Annotated[Decimal, Field(ge=0, lt=100000)]
    proteina: Annotated[Decimal, Field(ge=0, lt=10000)] = Decimal(0)
    carbo: Annotated[Decimal, Field(ge=0, lt=10000)] = Decimal(0)
    grasa: Annotated[Decimal, Field(ge=0, lt=10000)] = Decimal(0)
    grupo: Texto60 | None = None


class EjercicioCatalogo(Esquema):
    ulid: str
    nombre: str
    grupo: str | None
    equipo: str | None
    patron: str | None
    tiene_video: bool
    contraindicaciones: str | None
    propio: bool


class EjercicioNuevo(Esquema):
    nombre: Texto160
    grupo: Texto60 | None = None
    equipo: Texto60 | None = None
    patron: Texto60 | None = None


#: Fracción de un reparto: `Numeric(4, 3)`, entre 0 y 1.
Fraccion = Annotated[Decimal, Field(ge=0, le=1)]


class RepartoDeMacros(Esquema):
    """Fracciones que suman 1. La base lo exige con un CHECK."""

    carbohidrato: Fraccion
    proteina: Fraccion
    grasa: Fraccion


class ParametrosDeCiclo(Esquema):
    """Las entradas de la calculadora. Se guardan con el plan para que el ciclo siguiente
    arranque de lo que la coach dejó, no de valores por omisión."""

    actividad: Texto20
    #: Con signo: −0.28 es un déficit del 28 %. `Numeric(4, 3)`.
    porcentaje_ajuste: Annotated[Decimal, Field(ge=-1, le=1)]
    reparto: RepartoDeMacros
    base_proteina: Texto30
    dias_refeed: Annotated[int, Field(ge=0, le=2)]
    porcentaje_dia_refeed: Fraccion
    relacion_ganancia: Texto10


class PlanGuardado(Esquema):
    """El contenido va como JSON libre: su forma cambia seguido —tiempos de comida, días,
    bloques— y no se consulta por dentro, se lee completo."""

    tipo: Texto20
    contenido: dict[str, object]
    kcal_objetivo: Gramos | None = None
    proteina_g: Gramos | None = None
    carbohidrato_g: Gramos | None = None
    grasa_g: Gramos | None = None
    publicar: bool = False
    #: Solo viajan con el plan de nutrición, que es donde vive la calculadora.
    parametros: ParametrosDeCiclo | None = None
    #: `ninguna`, `diaria`, `semanal`, `quincenal` o `mensual`.
    frecuencia_fotos: Texto20 = "ninguna"


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
    #: Su plan y su precio: el calendario de cobros propone la mensualidad con esto.
    plan_nombre: str | None = None
    plan_precio: Numero | None = None


class FotoPublica(Esquema):
    """Metadatos. La imagen se pide por su propia ruta, y esa lectura queda registrada."""

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

    endpoint: Texto500
    p256dh: Texto255
    auth: Texto255


class MensajePublico(Esquema):
    ulid: str
    autor: str
    cuerpo: str
    enviado_en: datetime
    leido_en: datetime | None


class MensajeNuevo(Esquema):
    cuerpo: TextoLargo


class AnuncioNuevo(Esquema):
    """Lo que la coach escribe: un título y una frase."""

    titulo: Texto80
    cuerpo: Texto300
    #: ULIDs de a quién va. Vacío es «a todas mis pacientes activas».
    alumnas: Annotated[list[Texto30], Field(max_length=500)] = []


class AnuncioPublico(Esquema):
    ulid: str
    titulo: str
    cuerpo: str
    enviado_en: datetime
    enviadas: int
    leidas: int


class AvisoDeAlumna(Esquema):
    ulid: str
    titulo: str
    cuerpo: str
    recibido_en: datetime
    leido_en: datetime | None


class EstimacionGrasa(Esquema):
    #: Fracción: 0.22 es 22 %. `Numeric(4, 3)`.
    porcentaje_grasa: Annotated[Decimal, Field(gt=0, lt=1)]


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
    """El flujo de captura entero, en una llamada. Incluye el chequeo anterior porque la
    pantalla lo muestra al lado de cada campo."""

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
    #: El dominio revisa el rango de verdad; esto solo evita el 500 del motor.
    peso_kg: Annotated[Decimal, Field(gt=0, lt=1000)] | None = None
    varianza_confirmada: bool | None = None
    medidas: (
        Annotated[dict[Texto30, Annotated[Decimal, Field(gt=0, lt=1000)]], Field(max_length=20)]
        | None
    ) = None
    nota_alumna: TextoLargo | None = None
    bascula_usada: Texto120 | None = None
    lugar_usado: Texto120 | None = None
    hora_usada: Texto20 | None = None


class EnvioRechazado(Esquema):
    """Por qué no se pudo enviar. Van **todas** las causas, no la primera."""

    errores: list[dict[str, object]]
    campos_faltantes: dict[str, list[str]]


class LlavePush(Esquema):
    """Llave pública VAPID. Es pública por definición: viaja al navegador."""

    publica: str


class ValidacionChequeo(Esquema):
    feedback: TextoLargo
    justificacion_outlier: TextoLargo | None = None


class RechazoChequeo(Esquema):
    motivo: TextoLargo


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
    """Una coach vista desde la plataforma. Solo agregados —cuántas, no quiénes—: es lo que
    sostiene que la plataforma sea Encargado y no Responsable frente a la LFPDPPP."""

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
    nombre: Texto120
    #: Vacío = se usa el nombre. Es lo que ven sus alumnas en la barra y en los correos.
    marca: Texto120 = ""
    email: Texto180
    slug: Texto60 | None = None
    plan: Texto30 = "basico"
    limite_alumnas: Annotated[int, Field(ge=1, le=100000)] = 50
    precio_ciclo: Importe = Decimal(0)
    color_acento: Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")] = "#c9a227"
    zona_horaria: Texto60 = "America/Mexico_City"


class CoachDadaDeAlta(Esquema):
    coach_ulid: str
    email: str
    #: Se devuelve una sola vez. Después solo queda su hash.
    clave_temporal: str


class EdicionDeCoach(Esquema):
    """Términos comerciales. Sin el color de marca: lo elige la coach en su apariencia."""

    nombre: Texto120
    marca: Texto120
    plan: Texto30
    limite_alumnas: Annotated[int, Field(ge=1, le=100000)]
    estado: Texto20
    precio_ciclo: Importe


class EdicionDeSuscripcion(Esquema):
    plan: Texto30
    precio: Importe
    periodicidad: Texto10
    estado: Texto20
    vigente_hasta: date | None = None
    nota: TextoLargo | None = None


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
    #: Admite negativos: un cobro mal capturado se corrige con otro en contra, no editándolo.
    monto: Importe
    fecha: date
    metodo: Texto40 = "transferencia"
    periodo_inicia: date | None = None
    periodo_termina: date | None = None
    nota: TextoLargo | None = None


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
    color_secundario: str
    #: Nulo mientras no haya subido logo. La interfaz cae a las iniciales.
    tiene_logo: bool


class EdicionDeMarca(Esquema):
    nombre: Texto120
    marca: Texto120
    #: Hexadecimal, con o sin canal alfa. La columna son nueve caracteres.
    color_acento: Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")]
    color_secundario: Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")] = (
        "#C9A227"
    )


class DatoDeFicha(Esquema):
    """Un renglón de la ficha. La coach nombra el rótulo: no hay campos impuestos."""

    rotulo: Texto60
    valor: Texto200


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
    color_secundario: str


class EdicionDePresentacion(Esquema):
    titulo: Texto160
    texto: TextoLargo
    ficha: Annotated[list[DatoDeFicha], Field(max_length=8)]
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
    texto: Texto300
    ayuda: Texto300 | None = None
    tipo: Texto20 = "texto"
    #: Una lista sin tope permite mandar cien mil opciones en un JSON de un campo.
    opciones: Annotated[list[Texto200], Field(max_length=30)] = []
    obligatoria: bool = False
    orden: Annotated[int, Field(ge=0, le=9999)] = 0
    activa: bool = True


class NucleoClinico(Esquema):
    """La parte que no se puede quitar: la exige la ley y la consulta el plan."""

    lesiones: TextoLargo | None = None
    condiciones: TextoLargo | None = None
    medicacion: TextoLargo | None = None
    restricciones: TextoLargo | None = None


class RespuestaDePregunta(Esquema):
    pregunta_ulid: Texto30
    valor: TextoLargo


class PlanParaElegir(Esquema):
    """Un plan visto por quien todavía no lo contrata: sin `alumnas` ni código interno."""

    ulid: str
    nombre: str
    descripcion: str | None
    precio: Numero
    dias: int
    intensidad: str


class CuestionarioParaAlumna(Esquema):
    """El cuestionario tal como lo ve la alumna, con lo que ya hubiera contestado."""

    completo: bool
    nucleo: NucleoClinico
    preguntas: list[PreguntaPublica]
    respuestas: list[RespuestaDePregunta]
    #: Los que todavía tiene que aceptar. Vacío si ya los aceptó todos.
    consentimientos_pendientes: list[str]
    #: Los planes que vende su coach. Se le enseñan mientras no tenga uno elegido.
    planes: list[PlanParaElegir] = []
    plan_elegido: str | None = None


class EnvioDeCuestionario(Esquema):
    nucleo: NucleoClinico
    #: El plan que pide. Es una solicitud: el ciclo se crea con el que la coach confirme.
    tarifa_ulid: Texto30 | None = None
    respuestas: Annotated[list[RespuestaDePregunta], Field(max_length=200)] = []
    #: Tipos de consentimiento que acepta en este envío.
    consentimientos: Annotated[list[Texto30], Field(max_length=20)] = []


class RespuestaDeAlumna(Esquema):
    """Una respuesta vista por la coach, con su pregunta al lado."""

    pregunta: str
    tipo: str
    valor: str


class FotoDeComidaPublica(Esquema):
    """Una foto de un plato. **La imagen no viaja aquí**: se pide por su propia ruta."""

    ulid: str
    subida_en: datetime
    #: Cuándo se borra. Va explícito para que la alumna lo vea, no lo tenga que calcular.
    expira_en: datetime
    tiempo: str | None
    nota: str | None
    comentario: str | None


class FotosDeComidaDeAlumna(Esquema):
    """Lo que ve la alumna: qué le toca y qué mandó que siga viva."""

    #: `ninguna`, `diaria`, `semanal`, `quincenal` o `mensual`.
    frecuencia: str
    rotulo: str
    #: Nulo si la coach no pide fotos.
    desde: date | None
    hasta: date | None
    cumplido: bool
    fotos: list[FotoDeComidaPublica]


class ComentarioDeFoto(Esquema):
    comentario: TextoLargo


# ---------------------------------------------------------------------------
# Horario de atención y reserva de consultas
# ---------------------------------------------------------------------------


class TramoDeHorario(Esquema):
    """Un rato en que la coach atiende, en su hora local. `HH:MM`."""

    dia_semana: Annotated[int, Field(ge=0, le=6)]
    desde: Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
    hasta: Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]


class HorarioDeCoach(Esquema):
    tramos: Annotated[list[TramoDeHorario], Field(max_length=60)]
    duracion_consulta_min: Annotated[int, Field(ge=15, le=240)] = 60
    margen_consulta_min: Annotated[int, Field(ge=0, le=120)] = 15
    antelacion_horas: Annotated[int, Field(ge=0, le=720)] = 24
    horizonte_semanas: Annotated[int, Field(ge=1, le=26)] = 8
    zona_horaria: Texto60 = "America/Mexico_City"


class HuecoPublico(Esquema):
    inicia_en: datetime
    termina_en: datetime


class ReservaDeConsulta(Esquema):
    inicia_en: datetime
    modalidad: Texto20 = "video"


# ---------------------------------------------------------------------------
# Registro abierto
# ---------------------------------------------------------------------------


class LigaDeRegistro(Esquema):
    """Lo que ve quien abre la liga de una coach, antes de escribir nada."""

    coach: Texto120
    marca: Texto120
    color_acento: Texto10
    tiene_logo: bool
    abierta: bool
    #: Por qué no está disponible, cuando no lo está. Nulo si todo está en orden.
    motivo: str | None = None
    precio_inscripcion: Numero | None = None
    concepto_inscripcion: Texto120 | None = None


class RegistroNuevo(Esquema):
    nombre: Texto120
    correo: Texto180
    #: Sin tope: se cifra antes de guardarse y el hash de Argon2 siempre mide lo mismo.
    contrasena: str
    fecha_nacimiento: date
    whatsapp: Texto30 | None = None
    #: Los dos van juntos y los dos son obligatorios: aquí es donde entrega sus datos.
    acepta_terminos: bool = False
    acepta_privacidad: bool = False


class RegistroAceptado(Esquema):
    correo: str
    #: Solo fuera de producción, para poder terminar el recorrido sin buzón de correo.
    codigo: str | None = None


class CodigoDeRegistro(Esquema):
    correo: Texto180
    codigo: Annotated[str, Field(pattern=r"^\d{6}$")]


class CorreoDeRegistro(Esquema):
    correo: Texto180


class EstadoDeSolicitud(Esquema):
    """En qué punto va su registro. Es lo que dibuja la pantalla de la solicitante."""

    es_solicitud: bool
    estado: str
    paso: str
    coach: str
    cuestionario_completo: bool
    tiene_cita: bool
    comprobante_subido: bool
    #: Cuándo se borra sola si la deja a medias.
    vence_en: datetime | None = None
    cita_inicia_en: datetime | None = None


class AvisoDeBaja(Esquema):
    """Lo que la coach tiene que mirar antes de dar de baja. La baja no tiene deshacer."""

    nombre: str
    adeudo: Numero
    cobros_vencidos: int
    chequeos: int
    #: Cuándo se borra su expediente si confirma hoy.
    borraria_el: datetime


class ConfirmacionDeBaja(Esquema):
    #: El nombre de la alumna, tecleado. Es lo único que evita darle de baja a otra.
    nombre: Texto120


class BajaHecha(Esquema):
    borra_el: datetime


class SolicitudEnBandeja(Esquema):
    """Una solicitud vista por la coach, con lo que necesita para decidir sin abrir nada más.

    No trae historial clínico ni respuestas: eso vive en el expediente y su lectura queda
    anotada en la bitácora. Aquí solo va lo que sostiene la decisión.
    """

    ulid: str
    alumna_ulid: str
    nombre: str
    correo: str
    whatsapp: str | None
    edad: int
    estado: str
    paso: str
    registrada_en: datetime
    #: Cuándo desaparece sola si nadie hace nada. Nulo si ya está decidida.
    borra_en: datetime | None

    cuestionario_completo: bool
    plan_pedido: str | None
    plan_pedido_ulid: str | None
    precio_plan: Numero | None

    cita_inicia_en: datetime | None
    cita_modalidad: str | None

    cobro_ulid: str | None
    monto_inscripcion: Numero | None
    #: `pendiente`, `en_revision` o `pagado`. Es lo que decide si hay algo que mirar.
    estado_del_pago: str | None
    monto_leido: Numero | None
    motivo_descarte: str | None


class AceptacionDeSolicitud(Esquema):
    #: El plan que la coach confirma. Nulo deja el que la alumna pidió.
    tarifa_ulid: Texto30 | None = None
    #: Da por bueno el comprobante en el mismo gesto. Puede aceptarla sin hacerlo.
    validar_pago: bool = False


class DescarteDeSolicitud(Esquema):
    #: Lo lee ella tal cual en su correo, así que no es un campo de trámite.
    motivo: Texto500


class RegistroDeCoach(Esquema):
    """El interruptor de la liga, con lo que le falta para poder encenderla."""

    abierto: bool
    liga: str
    puede_encenderse: bool
    motivo: str | None = None
    servicios_de_inscripcion: int
    precio_inscripcion: Numero | None = None
    solicitudes_pendientes: int = 0


class InterruptorDeRegistro(Esquema):
    abierto: bool


# ---------------------------------------------------------------------------
# Derechos ARCO
# ---------------------------------------------------------------------------


class SolicitudArcoNueva(Esquema):
    #: `A`, `R`, `C` u `O`. La ley exige que se identifique con claridad cuál se ejerce.
    derecho: Annotated[str, Field(pattern=r"^[ARCO]$")]
    detalle: TextoLargo = ""


class SolicitudArcoPublica(Esquema):
    ulid: str
    derecho: str
    rotulo: str
    estado: str
    detalle: str | None
    respuesta: str | None
    recibida_en: datetime
    respondida_en: datetime | None
    resuelta_en: datetime | None
    #: Nulo cuando ya se resolvió: no hay plazo que correr.
    vence_el: date | None
    dias_restantes: int | None
    #: Solo la ve la coach: la alumna no necesita saber a quién más le corre el plazo.
    alumna: str | None = None


class RespuestaArco(Esquema):
    respuesta: TextoLargo


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


class FilaDeTabla(Esquema):
    celdas: list[str]
    #: La fila que le toca a esta alumna.
    suya: bool = False
    #: Su valor se sale del rango de esta fila. Es otro aviso, no el mismo.
    fuera: bool = False


class TablaDeHoja(Esquema):
    titulo: str
    encabezados: list[str]
    filas: list[FilaDeTabla]
    nota: str = ""
    #: Cuando lo suyo es una columna y no una fila, su índice.
    columna_suya: int | None = None


class TramoDeImc(Esquema):
    """Un tramo de la escala, de `desde` a `hasta` inclusive."""

    nombre: str
    desde: int
    hasta: int
    suyo: bool
    #: El entero exacto donde cae, solo en el tramo suyo.
    valor: int | None = None


class HojaDeCalculo(Esquema):
    """La hoja completa. Nula solo si falta el chequeo del que salen peso y grasa."""

    alumna: str
    bloques: list[BloqueDeHoja]
    tablas: list[TablaDeHoja]
    escala_imc: list[TramoDeImc] = []
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
    """El Markdown tal cual está en `app/legales/`. `marcadores` lleva los huecos sin rellenar: un
    aviso de privacidad con huecos no cumple la LFPDPPP y la pantalla lo dice."""

    clave: str
    titulo: str
    version: str
    actualizado: str
    contenido: str
    marcadores: list[str]


# ---------------------------------------------------------------------------
# Planes comerciales y cobros programados
# ---------------------------------------------------------------------------


class ServicioPublico(Esquema):
    """Un precio suelto del catálogo de la coach: una consulta, material, una inscripción."""

    ulid: str
    nombre: str
    descripcion: str | None
    #: Con qué motivo de cobro se programa: `cita`, `material`, `inscripcion`, `otro`.
    motivo: str
    precio: Numero
    activo: bool


class ServicioNuevo(Esquema):
    nombre: Texto120
    descripcion: TextoLargo | None = None
    motivo: Texto20 = "cita"
    precio: Dinero
    activo: bool = True


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
    codigo: Texto30
    nombre: Texto120
    descripcion: TextoLargo | None = None
    precio: Dinero
    dias: Annotated[int, Field(ge=1, le=365)] = 30
    intensidad: Texto20 = "media"
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
    motivo: Texto20 = "mensualidad"
    concepto: Texto180 | None = None
    monto: Dinero
    nota: TextoLargo | None = None


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
    #: Un PDF no se pinta con `<img>`. La pantalla necesita saberlo para elegir el visor.
    es_pdf: bool = False

    #: Lo que el OCR entendió del comprobante. **No valida nada**: es una sugerencia.
    monto_leido: Numero | None
    fecha_leida: date | None
    referencia: str | None
    banco: str | None
    confianza: Numero
    #: El OCR leyó un importe distinto al esperado. Mirar la imagen deja de ser opcional.
    monto_no_cuadra: bool


class RechazoDeComprobante(Esquema):
    motivo: TextoLargo
