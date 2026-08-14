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

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


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
    valor: Decimal


class ChequeoPublico(Esquema):
    ulid: str
    numero: int
    fecha: date
    estado: str
    peso_kg: Decimal | None
    porcentaje_grasa: Decimal | None
    medidas: dict[str, Decimal]
    fotos: dict[str, bool]
    feedback: str | None
    alerta_outlier: bool


class PesajePublico(Esquema):
    fecha: date
    peso_kg: Decimal


# ---------------------------------------------------------------------------
# Frente de alumna
# ---------------------------------------------------------------------------


class CicloPublico(Esquema):
    numero: int
    inicia_en: date
    termina_en: date
    estado_pago: str
    precio: Decimal


class PerfilAlumna(Esquema):
    ulid: str
    nombre: str
    correo: str
    estatura_cm: int | None
    objetivo: str | None
    bascula_ref: str | None
    lugar_ref: str | None
    hora_ref: str | None
    zona_horaria: str


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
    #: Nulo cuando el pago del ciclo no está validado: la guarda vive en el servidor.
    nutricion: PlanPublico | None
    entrenamiento: PlanPublico | None
    bloqueado_por_pago: bool
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
    peso_kg: Decimal | None
    peso_previo: Decimal | None
    objetivo: str | None
    pago: str
    ultimo_acceso: date | None
    alerta: str | None


class ResumenPanel(Esquema):
    coach: str
    marca: str
    plan: str
    limite_alumnas: int
    precio_ciclo: Decimal
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
    objetivo: str | None = None
    nivel_experiencia: str | None = None
    precio_ciclo: Decimal | None = None


class AlumnaDadaDeAlta(Esquema):
    alumna_ulid: str
    correo: str
    #: Se devuelve una sola vez, para que la coach pueda dictarla si el correo no llega.
    clave_temporal: str


class EdicionDeAlumna(Esquema):
    nombre: str
    whatsapp: str | None = None
    estatura_cm: int | None = None
    objetivo: str | None = None
    nivel_experiencia: str | None = None
    equipo: str | None = None
    ocupacion: str | None = None
    bascula_ref: str | None = None
    lugar_ref: str | None = None
    hora_ref: str | None = None
    zona_horaria: str | None = None
    porcentaje_grasa_objetivo: Decimal | None = None
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
    monto: Decimal
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
    monto: Decimal
    fecha: date
    concepto: str
    alumna_ulid: str | None = None
    nota: str | None = None


class TotalPorCategoria(Esquema):
    categoria: str
    monto: Decimal


class ResumenMes(Esquema):
    mes: str
    ingresos: Decimal
    gastos: Decimal
    utilidad: Decimal


class PanelFinanciero(Esquema):
    ingresos: Decimal
    gastos: Decimal
    utilidad: Decimal
    #: Fracción de los ingresos que queda como utilidad.
    margen: Decimal
    ingreso_por_alumna: Decimal
    #: Ingreso esperado si todas renuevan. **Es proyección, no dato**, y la pantalla lo dice.
    proyeccion_mensual: Decimal
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
    precio: Decimal
    dias: int
    activa: bool


class TarifaNueva(Esquema):
    codigo: str
    nombre: str
    descripcion: str | None = None
    precio: Decimal
    dias: int = 30
    activa: bool = True


# ---------------------------------------------------------------------------
# Planes editables
# ---------------------------------------------------------------------------


class AlimentoCatalogo(Esquema):
    ulid: str
    nombre: str
    marca: str | None
    porcion: Decimal
    unidad: str
    kcal: Decimal
    proteina: Decimal
    carbo: Decimal
    grasa: Decimal
    grupo: str | None
    #: `false` = viene de la base pública compartida por todas las coaches.
    propio: bool


class AlimentoNuevo(Esquema):
    nombre: str
    marca: str | None = None
    porcion: Decimal
    unidad: str = "g"
    kcal: Decimal
    proteina: Decimal = Decimal(0)
    carbo: Decimal = Decimal(0)
    grasa: Decimal = Decimal(0)
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


class FotoPublica(Esquema):
    """Metadatos de la fotografía. **La imagen no viaja aquí**: se pide por su propia ruta,
    y esa lectura vuelve a quedar registrada."""

    angulo: str
    #: Nula si ya se purgó: la fila sobrevive con fecha y motivo, la imagen no.
    disponible: bool
    nitidez: Decimal | None
    luminancia: Decimal | None
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
    monto: Decimal | None
    fecha: date | None
    referencia: str | None
    banco: str | None
    confianza: Decimal
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
    porcentaje_grasa: Decimal


# ---------------------------------------------------------------------------
# Captura del chequeo (frente de alumna)
# ---------------------------------------------------------------------------


class FotoDeBorrador(Esquema):
    """Estado de una toma. La imagen no viaja aquí: se pide por su propia ruta."""

    angulo: str
    estado_auto: str
    motivo_rechazo: str | None = None
    nitidez: Decimal | None
    luminancia: Decimal | None
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
    peso_kg: Decimal | None
    medidas: dict[str, Decimal]
    fotos: list[FotoDeBorrador]
    pesajes: list[PesajePublico]
    max_pesajes: int

    peso_anterior_kg: Decimal | None
    medidas_anteriores: dict[str, Decimal]

    bascula_ref: str | None
    lugar_ref: str | None
    hora_ref: str | None
    bascula_usada: str | None
    lugar_usado: str | None
    hora_usada: str | None


class GuardadoDeChequeo(Esquema):
    """Lo que la pantalla guarda entre pasos. Todo opcional: es un borrador."""

    ayuno_confirmado: bool | None = None
    peso_kg: Decimal | None = None
    varianza_confirmada: bool | None = None
    medidas: dict[str, Decimal] | None = None
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
    precio: Decimal
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
    slug: str
    email: str
    plan: str
    limite_alumnas: int
    estado: str
    precio_ciclo: Decimal
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
    email: str
    slug: str | None = None
    plan: str = "basico"
    limite_alumnas: int = 50
    precio_ciclo: Decimal = Decimal(0)
    color_acento: str = "#c9a227"
    zona_horaria: str = "America/Mexico_City"


class CoachDadaDeAlta(Esquema):
    coach_ulid: str
    email: str
    #: Se devuelve una sola vez. Después solo queda su hash.
    clave_temporal: str


class EdicionDeCoach(Esquema):
    nombre: str
    plan: str
    limite_alumnas: int
    estado: str
    precio_ciclo: Decimal
    color_acento: str


class EdicionDeSuscripcion(Esquema):
    plan: str
    precio: Decimal
    periodicidad: str
    estado: str
    vigente_hasta: date | None = None
    nota: str | None = None


class CobroPublico(Esquema):
    ulid: str
    coach_ulid: str
    monto: Decimal
    fecha: date
    metodo: str
    periodo_inicia: date | None
    periodo_termina: date | None
    nota: str | None


class CobroNuevo(Esquema):
    monto: Decimal
    fecha: date
    metodo: str = "transferencia"
    periodo_inicia: date | None = None
    periodo_termina: date | None = None
    nota: str | None = None


class ResumenDeFacturacion(Esquema):
    cobrado_en_el_ano: Decimal
    facturacion_mensual_esperada: Decimal
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
