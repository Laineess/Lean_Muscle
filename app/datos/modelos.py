"""Esquema de la base, en un archivo: se lee mejor completo que repartido.

Convenciones en `base.py`. Toda tabla con datos de alumnas hereda de `BaseMultiInquilino`
y lleva `coach_id`; el aislamiento lo aplica `alcance.py` en cada consulta.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import JSON, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.datos.base import ARGS_DE_TABLA, MARCA_DE_TIEMPO, Base, BaseMultiInquilino

# ---------------------------------------------------------------------------
# 1. Identidad y estructura
# ---------------------------------------------------------------------------


class Coach(Base):
    """El inquilino. No hereda de BaseMultiInquilino: es la raiz del aislamiento."""

    __tablename__ = "coach"
    __table_args__ = ARGS_DE_TABLA

    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    #: Nombre comercial que ven las alumnas. Puede no ser el de la persona: «LeanMuscle» no
    #: es «Mariana Cervantes», y es el que va en la barra y en los correos.
    marca: Mapped[str | None] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(40), default="basico", nullable=False)
    limite_alumnas: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="activa", nullable=False)

    # White-label parcial: logo y color. Sin dominio propio en el MVP.
    logo_key: Mapped[str | None] = mapped_column(String(255))
    color_acento: Mapped[str] = mapped_column(String(9), default="#0E3B2B", nullable=False)

    precio_ciclo: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    dia_chequeo: Mapped[int] = mapped_column(TINYINT, default=1, nullable=False)
    zona_horaria: Mapped[str] = mapped_column(
        String(60), default="America/Mexico_City", nullable=False
    )


class Usuario(BaseMultiInquilino):
    """Credenciales. El rol determina que ve; el `coach_id` determina que existe para el."""

    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint("rol in ('coach','alumna','admin_plataforma')", name="rol_valido"),
        ARGS_DE_TABLA,
    )

    rol: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    hash_contrasena: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="activo", nullable=False)
    ultimo_acceso_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    debe_cambiar_contrasena: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Sesion(BaseMultiInquilino):
    """Sesion en tabla, no JWT suelto: permite revocarla desde el panel."""

    __tablename__ = "sesion"
    __table_args__ = (Index("ix_sesion_vence_en", "vence_en"), ARGS_DE_TABLA)

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    vence_en: Mapped[datetime] = mapped_column(MARCA_DE_TIEMPO, nullable=False)
    revocada_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))


class Alumna(BaseMultiInquilino):
    __tablename__ = "alumna"
    __table_args__ = (
        CheckConstraint(
            "estatura_cm is null or estatura_cm between 100 and 250", name="estatura_rango"
        ),
        CheckConstraint("estres is null or estres between 1 and 10", name="estres_rango"),
        ARGS_DE_TABLA,
    )

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    whatsapp: Mapped[str | None] = mapped_column(String(30))
    fecha_nacimiento: Mapped[date] = mapped_column(Date, nullable=False)
    sexo: Mapped[str | None] = mapped_column(String(1))

    #: Dato unico inicial: no se recaptura en cada chequeo.
    estatura_cm: Mapped[int | None] = mapped_column(Integer)

    #: El plan comercial que contrató.
    tarifa_id: Mapped[int | None] = mapped_column(ForeignKey("tarifa.id"))
    nivel_experiencia: Mapped[str | None] = mapped_column(String(20))
    equipo: Mapped[str | None] = mapped_column(String(30))
    estres: Mapped[int | None] = mapped_column(TINYINT)
    ocupacion: Mapped[str | None] = mapped_column(String(180))

    #: La suya, no la de la coach: el "mismo dia calendario" se evalua aqui.
    zona_horaria: Mapped[str] = mapped_column(
        String(60), default="America/Mexico_City", nullable=False
    )

    #: Meta de composicion corporal; alimenta la proyeccion de la calculadora.
    porcentaje_grasa_objetivo: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))

    #: Condiciones del chequeo anterior, para precargarlas y detectar inconsistencias.
    bascula_ref: Mapped[str | None] = mapped_column(String(120))
    lugar_ref: Mapped[str | None] = mapped_column(String(120))
    hora_ref: Mapped[str | None] = mapped_column(String(5))

    cuestionario_completo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="activa", nullable=False)


# ---------------------------------------------------------------------------
# 2. Salud y consentimientos
# ---------------------------------------------------------------------------


class HistorialClinico(BaseMultiInquilino):
    """Versionado: nunca se actualiza, se inserta una version nueva."""

    __tablename__ = "historial_clinico"
    __table_args__ = (
        Index("ix_historial_alumna_vigente", "alumna_id", "vigente_desde"),
        ARGS_DE_TABLA,
    )

    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    lesiones: Mapped[str | None] = mapped_column(Text)
    condiciones: Mapped[str | None] = mapped_column(Text)
    medicacion: Mapped[str | None] = mapped_column(Text)
    restricciones: Mapped[str | None] = mapped_column(Text)
    vigente_desde: Mapped[datetime] = mapped_column(MARCA_DE_TIEMPO, nullable=False)
    registrado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))


class Consentimiento(BaseMultiInquilino):
    """Solo INSERT. `version_texto` y `texto_hash` guardan que texto exacto acepto, que es
    lo que exige el consentimiento expreso para datos sensibles (Anexo Legal, seccion 5)."""

    __tablename__ = "consentimiento"
    __table_args__ = (
        CheckConstraint(
            "tipo in ('terminos','privacidad','protocolo_foto','datos_salud')",
            name="tipo_valido",
        ),
        Index("ix_consentimiento_alumna_tipo", "alumna_id", "tipo"),
        ARGS_DE_TABLA,
    )

    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    version_texto: Mapped[str] = mapped_column(String(20), nullable=False)
    texto_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    aceptado_en: Mapped[datetime] = mapped_column(MARCA_DE_TIEMPO, nullable=False)
    revocado_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))


# ---------------------------------------------------------------------------
# 3. El chequeo
# ---------------------------------------------------------------------------


class Ciclo(BaseMultiInquilino):
    __tablename__ = "ciclo"
    __table_args__ = (
        UniqueConstraint("alumna_id", "numero", name="uq_ciclo_alumna_numero"),
        ARGS_DE_TABLA,
    )

    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    inicia_en: Mapped[date] = mapped_column(Date, nullable=False)
    termina_en: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="pendiente_pago", nullable=False)
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)


class Chequeo(BaseMultiInquilino):
    __tablename__ = "chequeo"
    __table_args__ = (
        CheckConstraint(
            "estado in ('borrador','pendiente_evaluacion','validado','rechazado_calidad','descartado')",
            name="estado_valido",
        ),
        Index("ix_chequeo_alumna_fecha", "alumna_id", "fecha"),
        ARGS_DE_TABLA,
    )

    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    ciclo_id: Mapped[int] = mapped_column(ForeignKey("ciclo.id"), nullable=False)

    #: DATE a proposito: la regla de negocio habla de dia calendario, no de instante.
    fecha: Mapped[date] = mapped_column(Date, nullable=False)

    estado: Mapped[str] = mapped_column(String(30), default="borrador", nullable=False)
    ayuno_confirmado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    enviado_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    validado_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    validado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))

    feedback: Mapped[str | None] = mapped_column(Text)
    motivo_rechazo: Mapped[str | None] = mapped_column(Text)
    nota_alumna: Mapped[str | None] = mapped_column(Text)

    alerta_outlier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    justificacion_outlier: Mapped[str | None] = mapped_column(Text)
    varianza_confirmada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    #: Lo estima la coach al validar. Es la entrada que manda toda la calculadora, y vive en
    #: el chequeo porque se grafica su evolucion mes a mes.
    porcentaje_grasa: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    estimado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))

    #: Entorno declarado, para la advertencia no bloqueante de inconsistencia.
    bascula_usada: Mapped[str | None] = mapped_column(String(120))
    lugar_usado: Mapped[str | None] = mapped_column(String(120))
    hora_usada: Mapped[str | None] = mapped_column(String(5))


class ParametrosCiclo(BaseMultiInquilino):
    """Entradas de la calculadora metabolica, por ciclo y no en el perfil: es lo que permite
    entender despues por que un mes funciono y otro no.

    Origen: `Calculadora del Fitness.xlsm`, celdas C16, C17, B27/C27/E27, C29, G14 y H14.
    """

    __tablename__ = "parametros_ciclo"
    __table_args__ = (
        UniqueConstraint("ciclo_id", name="uq_parametros_ciclo"),
        CheckConstraint("dias_refeed between 0 and 2", name="dias_refeed_rango"),
        CheckConstraint(
            "reparto_carbohidrato + reparto_proteina + reparto_grasa = 1.000",
            name="reparto_suma_uno",
        ),
        ARGS_DE_TABLA,
    )

    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    ciclo_id: Mapped[int] = mapped_column(ForeignKey("ciclo.id"), nullable=False)

    #: Multiplicador de actividad, 1.2 a 1.9 (celda C16).
    nivel_actividad: Mapped[str] = mapped_column(String(20), nullable=False)

    #: Fraccion con signo: -0.28 es un deficit del 28 % (celda C17).
    porcentaje_ajuste: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)

    #: Reparto de macros en fracciones que suman 1 (celdas B27, C27, E27).
    reparto_carbohidrato: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    reparto_proteina: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    reparto_grasa: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)

    #: Contra que peso se expresa la proteina en g/kg (celda C29).
    base_proteina: Mapped[str] = mapped_column(
        String(30), default="masa_libre_de_grasa", nullable=False
    )

    #: Refeeds (celdas G14 y H14). Van a mantenimiento salvo deficit propio.
    dias_refeed: Mapped[int] = mapped_column(TINYINT, default=0, nullable=False)
    porcentaje_dia_refeed: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=0, nullable=False)

    #: Relacion esperada musculo:grasa en fase de ganancia (celdas H18/I18).
    relacion_ganancia: Mapped[str] = mapped_column(String(5), default="2:1", nullable=False)


class Pesaje(BaseMultiInquilino):
    """Un peso por dia, garantizado por el UNIQUE. Hasta 3 por chequeo; el promedio lo
    calcula `app/dominio/medidas.promedio_de_pesajes`."""

    __tablename__ = "pesaje"
    __table_args__ = (
        UniqueConstraint("alumna_id", "fecha", name="uq_pesaje_alumna_fecha"),
        CheckConstraint("peso_kg between 30.0 and 250.0", name="peso_rango"),
        ARGS_DE_TABLA,
    )

    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    chequeo_id: Mapped[int | None] = mapped_column(ForeignKey("chequeo.id"))
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    peso_kg: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    bascula_ref: Mapped[str | None] = mapped_column(String(120))


class Medida(BaseMultiInquilino):
    __tablename__ = "medida"
    __table_args__ = (
        UniqueConstraint("chequeo_id", "tipo", name="uq_medida_chequeo_tipo"),
        CheckConstraint(
            "tipo in ('cintura','abdomen','cadera','busto','pecho','brazo','muslo','pantorrilla')",
            name="tipo_valido",
        ),
        CheckConstraint("valor > 0", name="valor_positivo"),
        ARGS_DE_TABLA,
    )

    chequeo_id: Mapped[int] = mapped_column(ForeignKey("chequeo.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)


class Foto(BaseMultiInquilino):
    """Una por angulo. El original nunca se guarda: entra recortada sin cabeza ni cuello."""

    __tablename__ = "foto"
    __table_args__ = (
        UniqueConstraint("chequeo_id", "angulo", name="uq_foto_chequeo_angulo"),
        CheckConstraint("angulo in ('frontal','perfil','espalda')", name="angulo_valido"),
        Index("ix_foto_purga", "purgada_en", "tomada_en"),
        ARGS_DE_TABLA,
    )

    chequeo_id: Mapped[int] = mapped_column(ForeignKey("chequeo.id"), nullable=False)
    angulo: Mapped[str] = mapped_column(String(10), nullable=False)

    #: Nula cuando la foto ya fue purgada: la fila sobrevive para la bitacora, la imagen no.
    storage_key: Mapped[str | None] = mapped_column(String(255))

    ancho: Mapped[int | None] = mapped_column(Integer)
    alto: Mapped[int | None] = mapped_column(Integer)
    bytes: Mapped[int | None] = mapped_column(BigInteger)

    #: Varianza del laplaciano y luminancia media. Bajo umbral => estado_auto = rechazada.
    nitidez: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    luminancia: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    estado_auto: Mapped[str] = mapped_column(String(20), default="pendiente", nullable=False)

    es_linea_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tomada_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    subida_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    purgada_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    motivo_purga: Mapped[str | None] = mapped_column(String(60))


# ---------------------------------------------------------------------------
# 4. Planes y biblioteca
# ---------------------------------------------------------------------------


class Plan(BaseMultiInquilino):
    """El contenido va en JSON a proposito: su forma cambia seguido, y no se consulta por
    dentro — se lee completo. Lo normalizado se reserva a lo que si se busca y se agrega."""

    __tablename__ = "plan"
    __table_args__ = (
        CheckConstraint("tipo in ('nutricion','entrenamiento')", name="tipo_valido"),
        CheckConstraint("estado in ('borrador','publicado')", name="estado_valido"),
        Index("ix_plan_alumna_ciclo", "alumna_id", "ciclo_id"),
        ARGS_DE_TABLA,
    )

    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    ciclo_id: Mapped[int] = mapped_column(ForeignKey("ciclo.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="borrador", nullable=False)
    publicado_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    contenido: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    #: Desnormalizados fuera del JSON porque son las guardas de publicacion y se filtran.
    kcal_objetivo: Mapped[int | None] = mapped_column(Integer)
    proteina_g: Mapped[int | None] = mapped_column(Integer)
    carbohidrato_g: Mapped[int | None] = mapped_column(Integer)
    grasa_g: Mapped[int | None] = mapped_column(Integer)

    #: Cada cuanto le toca mandar fotos de sus comidas. Solo en el plan de nutricion.
    frecuencia_fotos: Mapped[str] = mapped_column(String(12), default="ninguna", nullable=False)


class FotoDeComida(BaseMultiInquilino):
    """Un plato, para que la coach vea que come de verdad. Se borra a las 36 horas.

    El plazo se cumple por dos vias: las consultas filtran por fecha aunque el archivo siga
    en disco, y un trabajo borra los bytes. Si el trabajo se cae, deja de verse igual.
    """

    __tablename__ = "foto_de_comida"
    __table_args__ = (
        Index("ix_foto_comida_alumna_subida", "alumna_id", "subida_en"),
        Index("ix_foto_comida_purga", "purgada_en", "subida_en"),
        ARGS_DE_TABLA,
    )

    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    #: Nula cuando ya se purgo: la fila sobrevive para la bitacora, la imagen no.
    storage_key: Mapped[str | None] = mapped_column(String(255))
    subida_en: Mapped[datetime] = mapped_column(MARCA_DE_TIEMPO, nullable=False)
    purgada_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    #: Que comida es, en una linea. Sin lista cerrada: los tiempos los decide su plan.
    tiempo: Mapped[str | None] = mapped_column(String(60))
    nota: Mapped[str | None] = mapped_column(Text)
    #: Lo que la coach le contesta al verla.
    comentario: Mapped[str | None] = mapped_column(Text)


class Alimento(Base):
    """`coach_id` nulo = base publica compartida. Por eso no hereda de BaseMultiInquilino:
    una fila con coach_id NULL debe ser visible para todas."""

    __tablename__ = "alimento"
    __table_args__ = (Index("ix_alimento_coach_nombre", "coach_id", "nombre"), ARGS_DE_TABLA)

    coach_id: Mapped[int | None] = mapped_column(BigInteger)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    marca: Mapped[str | None] = mapped_column(String(120))
    porcion: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    unidad: Mapped[str] = mapped_column(String(10), default="g", nullable=False)
    kcal: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    proteina: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    carbo: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    grasa: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    fibra: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    sodio: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    grupo_equivalente: Mapped[str | None] = mapped_column(String(60))
    alergenos: Mapped[list[str] | None] = mapped_column(JSON)


class Ejercicio(Base):
    """Semilla del dataset MIT `hasaneyldrm/exercises-dataset`. Sus GIF no se importan:
    son de Gym visual y requieren licencia aparte."""

    __tablename__ = "ejercicio"
    __table_args__ = (Index("ix_ejercicio_coach_nombre", "coach_id", "nombre"), ARGS_DE_TABLA)

    coach_id: Mapped[int | None] = mapped_column(BigInteger)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    grupo: Mapped[str | None] = mapped_column(String(60))
    equipo: Mapped[str | None] = mapped_column(String(60))
    patron: Mapped[str | None] = mapped_column(String(60))
    video_key: Mapped[str | None] = mapped_column(String(255))
    instrucciones: Mapped[str | None] = mapped_column(Text)
    contraindicaciones: Mapped[str | None] = mapped_column(Text)


class Plantilla(BaseMultiInquilino):
    __tablename__ = "plantilla"
    __table_args__ = (
        UniqueConstraint("coach_id", "codigo", name="uq_plantilla_codigo"),
        ARGS_DE_TABLA,
    )

    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    dias: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    usos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


# ---------------------------------------------------------------------------
# 5. Dinero, comunicacion y cumplimiento
# ---------------------------------------------------------------------------


class Pago(BaseMultiInquilino):
    __tablename__ = "pago"
    __table_args__ = (ARGS_DE_TABLA,)

    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    ciclo_id: Mapped[int] = mapped_column(ForeignKey("ciclo.id"), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    metodo: Mapped[str | None] = mapped_column(String(40))
    comprobante_key: Mapped[str | None] = mapped_column(String(255))

    #: Lo que extrajo el OCR, sin interpretar. La coach valida contra esto.
    ocr: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    confianza: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))

    estado: Mapped[str] = mapped_column(String(20), default="pendiente", nullable=False)
    validado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    validado_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)


class Cita(BaseMultiInquilino):
    """Consultas con alumnas y bloques de trabajo propio de la coach. `alumna_id` nulo es un
    bloqueo: tambien tiene que ocupar hueco o el solape no se detecta."""

    __tablename__ = "cita"
    __table_args__ = (
        CheckConstraint("tipo in ('consulta','bloqueo')", name="tipo_valido"),
        CheckConstraint(
            "estado in ('agendada','confirmada','realizada','cancelada')", name="estado_valido"
        ),
        CheckConstraint("modalidad in ('presencial','video','telefono')", name="modalidad_valida"),
        CheckConstraint("termina_en > inicia_en", name="rango_valido"),
        # El solape se consulta por coach y ventana de tiempo en cada alta.
        Index("ix_cita_coach_inicia", "coach_id", "inicia_en"),
        ARGS_DE_TABLA,
    )

    #: Nulo cuando es un bloque de trabajo de la coach, no una consulta.
    alumna_id: Mapped[int | None] = mapped_column(ForeignKey("alumna.id"))

    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), default="consulta", nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="agendada", nullable=False)
    modalidad: Mapped[str] = mapped_column(String(20), default="video", nullable=False)

    inicia_en: Mapped[datetime] = mapped_column(MARCA_DE_TIEMPO, nullable=False)
    termina_en: Mapped[datetime] = mapped_column(MARCA_DE_TIEMPO, nullable=False)

    enlace: Mapped[str | None] = mapped_column(String(255))
    lugar: Mapped[str | None] = mapped_column(String(160))
    notas: Mapped[str | None] = mapped_column(Text)

    #: Se avisa a la alumna al agendar y un dia antes.
    recordatorio_enviado_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    cancelada_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    motivo_cancelacion: Mapped[str | None] = mapped_column(String(255))


class Tarifa(BaseMultiInquilino):
    """Precio de un plan comercial. Se copia al ciclo al cobrarlo: subirlo aqui no reescribe
    lo que ya se pacto con nadie."""

    __tablename__ = "tarifa"
    __table_args__ = (
        UniqueConstraint("coach_id", "codigo", name="uq_tarifa_codigo"),
        CheckConstraint("precio > 0", name="precio_positivo"),
        CheckConstraint("dias between 1 and 365", name="dias_rango"),
        CheckConstraint("intensidad in ('baja','media','alta')", name="intensidad_valida"),
        ARGS_DE_TABLA,
    )

    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    dias: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    #: Descriptiva: la ve la alumna y ordena la cartera.
    intensidad: Mapped[str] = mapped_column(String(10), default="media", nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Servicio(BaseMultiInquilino):
    """Cargo puntual: una consulta suelta, material, una inscripcion. Aparte de `Tarifa`,
    que es una suscripcion con duracion. El precio se copia al cobro al programarlo."""

    __tablename__ = "servicio"
    __table_args__ = (
        CheckConstraint("precio > 0", name="precio_servicio_positivo"),
        CheckConstraint(
            "motivo in ('inscripcion','mensualidad','cita','material','otro')",
            name="motivo_servicio_valido",
        ),
        Index("ix_servicio_coach_motivo", "coach_id", "motivo"),
        ARGS_DE_TABLA,
    )

    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    #: Con que motivo se programa; el formulario de cobro filtra por esto.
    motivo: Mapped[str] = mapped_column(String(20), default="cita", nullable=False)
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MovimientoFinanciero(BaseMultiInquilino):
    """Contabilidad de gestion de la coach: sirve para saber si su negocio gana dinero, no
    para declarar impuestos. Por eso no hay IVA desglosado ni folios fiscales."""

    __tablename__ = "movimiento_financiero"
    __table_args__ = (
        CheckConstraint("tipo in ('ingreso','gasto')", name="tipo_valido"),
        CheckConstraint("monto > 0", name="monto_positivo"),
        Index("ix_movimiento_coach_fecha", "coach_id", "fecha"),
        ARGS_DE_TABLA,
    )

    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    categoria: Mapped[str] = mapped_column(String(30), nullable=False)

    #: El signo lo da el tipo, nunca el monto: un gasto negativo seria un ingreso disfrazado.
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    concepto: Mapped[str] = mapped_column(String(200), nullable=False)

    #: Solo cuando el ingreso viene de alguien concreto.
    alumna_id: Mapped[int | None] = mapped_column(ForeignKey("alumna.id"))
    pago_id: Mapped[int | None] = mapped_column(ForeignKey("pago.id"))

    #: Generado al validar un pago. Se corrige en el pago, no aqui.
    automatico: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    comprobante_key: Mapped[str | None] = mapped_column(String(255))
    nota: Mapped[str | None] = mapped_column(Text)


class AvisoEnviado(BaseMultiInquilino):
    """Sello de cada aviso disparado: un trabajo que corre dos veces no manda dos correos.
    La llave lleva dentro el hecho que lo disparo (`cita:{id}:recordatorio`)."""

    __tablename__ = "aviso_enviado"
    __table_args__ = (
        UniqueConstraint("coach_id", "llave", name="uq_aviso_llave"),
        Index("ix_aviso_destinatario", "destinatario_id", "creado_en"),
        ARGS_DE_TABLA,
    )

    destinatario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    #: Se copia al encolar: si cambia de correo antes del envio, va a donde se dijo.
    destinatario_correo: Mapped[str] = mapped_column(String(180), nullable=False)

    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    llave: Mapped[str] = mapped_column(String(160), nullable=False)
    canal: Mapped[str] = mapped_column(String(20), nullable=False)

    #: Variables de la plantilla; se guardan porque el envio ocurre fuera de la peticion.
    contexto: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    #: Nulo mientras esta pendiente. El trabajador toma los nulos.
    enviado_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    error: Mapped[str | None] = mapped_column(Text)
    intentos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Mensaje(BaseMultiInquilino):
    __tablename__ = "mensaje"
    __table_args__ = (Index("ix_mensaje_alumna_enviado", "alumna_id", "enviado_en"), ARGS_DE_TABLA)

    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    autor: Mapped[str] = mapped_column(String(10), nullable=False)  # alumna | coach
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)
    adjunto_key: Mapped[str | None] = mapped_column(String(255))
    enviado_en: Mapped[datetime] = mapped_column(MARCA_DE_TIEMPO, nullable=False)
    leido_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)


class Anuncio(BaseMultiInquilino):
    """Titulo y cuerpo a varias alumnas a la vez, sin hilo. Tabla aparte de `Mensaje` para
    poder contar a cuantas llego y cuantas lo leyeron. Se borra al leerse (ver purga)."""

    __tablename__ = "anuncio"
    __table_args__ = (Index("ix_anuncio_coach_enviado", "coach_id", "enviado_en"), ARGS_DE_TABLA)

    titulo: Mapped[str] = mapped_column(String(80), nullable=False)
    #: 300 es lo que cabe en un push sin recortarse.
    cuerpo: Mapped[str] = mapped_column(String(300), nullable=False)
    enviado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    enviado_en: Mapped[datetime] = mapped_column(MARCA_DE_TIEMPO, nullable=False)


class Notificacion(BaseMultiInquilino):
    __tablename__ = "notificacion"
    __table_args__ = (
        Index("ix_notificacion_destinatario", "destinatario_id", "leida_en"),
        ARGS_DE_TABLA,
    )

    destinatario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    canal: Mapped[str] = mapped_column(String(20), default="push", nullable=False)
    enviada_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    leida_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    #: Nulo en las que no vienen de un anuncio.
    anuncio_id: Mapped[int | None] = mapped_column(ForeignKey("anuncio.id"))


class ClaveTemporal(BaseMultiInquilino):
    """En el MVP no hay autorrecuperacion por correo: la coach emite la clave a mano tras
    verificar identidad. Se guarda el hash, nunca la clave."""

    __tablename__ = "clave_temporal"
    __table_args__ = (ARGS_DE_TABLA,)

    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    emitida_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    hash: Mapped[str] = mapped_column(String(255), nullable=False)
    vence_en: Mapped[datetime] = mapped_column(MARCA_DE_TIEMPO, nullable=False)
    usada_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    motivo_verificacion: Mapped[str | None] = mapped_column(String(255))


class SuscripcionPush(BaseMultiInquilino):
    """Un navegador suscrito. La unicidad va por endpoint porque una persona puede tener
    varios; ante un 404 o 410 del servicio de push se borra en vez de reintentar."""

    __tablename__ = "suscripcion_push"
    __table_args__ = (
        UniqueConstraint("endpoint_hash", name="uq_suscripcion_endpoint"),
        Index("ix_suscripcion_usuario", "usuario_id"),
        ARGS_DE_TABLA,
    )

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    #: El endpoint es largo y MySQL no indexa 500 caracteres comodamente.
    endpoint_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    p256dh: Mapped[str] = mapped_column(String(255), nullable=False)
    auth: Mapped[str] = mapped_column(String(255), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ultimo_envio_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    fallos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Bitacora(BaseMultiInquilino):
    """Append-only, retencion de 5 anios. Al cancelar una cuenta el movimiento queda con
    identificador anonimizado."""

    __tablename__ = "bitacora"
    __table_args__ = (Index("ix_bitacora_coach_creado", "coach_id", "creado_en"), ARGS_DE_TABLA)

    actor_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(BigInteger)
    accion: Mapped[str] = mapped_column(String(60), nullable=False)
    entidad: Mapped[str] = mapped_column(String(60), nullable=False)
    entidad_id: Mapped[int | None] = mapped_column(BigInteger)
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class AccesoSensible(BaseMultiInquilino):
    """Quien vio fotos o historial clinico y cuando. Obligacion del Anexo Legal, seccion 6."""

    __tablename__ = "acceso_sensible"
    __table_args__ = (Index("ix_acceso_alumna_creado", "alumna_id", "creado_en"), ARGS_DE_TABLA)

    actor_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), nullable=False)
    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    recurso: Mapped[str] = mapped_column(String(60), nullable=False)


class SolicitudArco(BaseMultiInquilino):
    """Acceso, Rectificacion, Cancelacion, Oposicion. La reforma 2025 exige que la
    solicitud identifique con claridad cual derecho se ejerce."""

    __tablename__ = "solicitud_arco"
    __table_args__ = (
        CheckConstraint("derecho in ('A','R','C','O')", name="derecho_valido"),
        ARGS_DE_TABLA,
    )

    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    derecho: Mapped[str] = mapped_column(String(1), nullable=False)
    recibida_en: Mapped[datetime] = mapped_column(MARCA_DE_TIEMPO, nullable=False)
    respondida_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    resuelta_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    estado: Mapped[str] = mapped_column(String(20), default="recibida", nullable=False)
    #: Lo que pidio la alumna, con sus palabras.
    detalle: Mapped[str | None] = mapped_column(Text)
    #: Lo que le contesto la coach. Es la constancia de la respuesta.
    respuesta: Mapped[str | None] = mapped_column(Text)
    notas: Mapped[str | None] = mapped_column(Text)


class Vulneracion(Base):
    """Bitacora de vulneraciones de seguridad. No lleva coach_id: una vulneracion puede
    cruzar inquilinos, y es justo el caso que hay que poder ver completo."""

    __tablename__ = "vulneracion"
    __table_args__ = (ARGS_DE_TABLA,)

    detectada_en: Mapped[datetime] = mapped_column(MARCA_DE_TIEMPO, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    causa: Mapped[str | None] = mapped_column(Text)
    alcance: Mapped[str | None] = mapped_column(Text)
    notificado_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
    acciones_correctivas: Mapped[str | None] = mapped_column(Text)


class Trabajo(Base):
    """Cola en tabla: systemd dice cuando, esto dice que falta y que fallo. El trabajador la
    toma con SELECT ... FOR UPDATE SKIP LOCKED."""

    __tablename__ = "trabajo"
    __table_args__ = (Index("ix_trabajo_estado_correr", "estado", "correr_en"), ARGS_DE_TABLA)

    tipo: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    estado: Mapped[str] = mapped_column(String(20), default="pendiente", nullable=False)
    correr_en: Mapped[datetime] = mapped_column(MARCA_DE_TIEMPO, nullable=False)
    intentos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_intentos: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    ultimo_error: Mapped[str | None] = mapped_column(Text)
    terminado_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)


class IntentoDeAcceso(Base):
    """Lo que frena la fuerza bruta. Sin `coach_id`: al intentar todavia no se sabe de quien
    es el correo. En la base y no en memoria, para que el limite valga en todos los procesos.
    """

    __tablename__ = "intento_de_acceso"
    __table_args__ = (
        Index("ix_intento_correo_cuando", "correo", "creado_en"),
        Index("ix_intento_ip_cuando", "ip", "creado_en"),
        ARGS_DE_TABLA,
    )

    #: En minusculas y sin verificar que exista: probar correos al azar tambien se frena.
    correo: Mapped[str] = mapped_column(String(180), nullable=False)
    ip: Mapped[str | None] = mapped_column(String(45))
    exitoso: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PreguntaCuestionario(BaseMultiInquilino):
    """Una pregunta propia de la coach. El nucleo clinico no vive aqui: son columnas de
    `historial_clinico` porque el plan y los avisos las consultan por nombre."""

    __tablename__ = "pregunta_cuestionario"
    __table_args__ = (
        CheckConstraint(
            "tipo in ('texto','texto_largo','numero','opcion','si_no')", name="tipo_pregunta_valido"
        ),
        Index("ix_pregunta_coach_orden", "coach_id", "orden"),
        ARGS_DE_TABLA,
    )

    texto: Mapped[str] = mapped_column(String(300), nullable=False)
    ayuda: Mapped[str | None] = mapped_column(String(300))
    tipo: Mapped[str] = mapped_column(String(20), default="texto", nullable=False)
    #: Solo para `opcion`: las alternativas, en orden.
    opciones: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    obligatoria: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Apagar en vez de borrar: las respuestas ya dadas siguen teniendo su pregunta.
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RespuestaCuestionario(BaseMultiInquilino):
    """Lo que contesto la alumna. Una fila por pregunta."""

    __tablename__ = "respuesta_cuestionario"
    __table_args__ = (
        UniqueConstraint("alumna_id", "pregunta_id", name="uq_respuesta_alumna_pregunta"),
        ARGS_DE_TABLA,
    )

    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    pregunta_id: Mapped[int] = mapped_column(ForeignKey("pregunta_cuestionario.id"), nullable=False)
    valor: Mapped[str] = mapped_column(Text, default="", nullable=False)


class PresentacionCoach(BaseMultiInquilino):
    """Lo primero que ve una alumna nueva, antes del cuestionario: a quien le va a contar
    sus lesiones y su peso."""

    __tablename__ = "presentacion_coach"
    __table_args__ = (UniqueConstraint("coach_id", name="uq_presentacion_coach"), ARGS_DE_TABLA)

    #: Foto de la coach. Es la suya, no el logo: la alumna quiere ver una cara.
    foto_key: Mapped[str | None] = mapped_column(String(255))
    titulo: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    #: Texto libre, en parrafos. Lo escribe ella entero.
    texto: Mapped[str] = mapped_column(Text, default="", nullable=False)
    #: [{"rotulo": "Certificaciones", "valor": "..."}]. JSON porque ella nombra sus campos.
    ficha: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)
    #: Apagada no se muestra y la alumna pasa directo al cuestionario.
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# ---------------------------------------------------------------------------
# 10. La plataforma cobrando a sus coaches
# ---------------------------------------------------------------------------


class SuscripcionCoach(Base):
    """Lo que cada coach le paga a la plataforma. No hereda de `BaseMultiInquilino`: es un
    dato *sobre* el inquilino, y el superadmin —que no es coach de nadie— tiene que verlas
    todas. Sin pasarela: paga por transferencia y aqui se registra."""

    __tablename__ = "suscripcion_coach"
    __table_args__ = (
        UniqueConstraint("coach_id", name="uq_suscripcion_coach"),
        CheckConstraint(
            "estado in ('cortesia','al_corriente','por_vencer','vencida','cancelada')",
            name="estado_valido",
        ),
        CheckConstraint("periodicidad in ('mensual','anual')", name="periodicidad_valida"),
        ARGS_DE_TABLA,
    )

    coach_id: Mapped[int] = mapped_column(ForeignKey("coach.id"), nullable=False)
    plan: Mapped[str] = mapped_column(String(40), default="basico", nullable=False)
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    periodicidad: Mapped[str] = mapped_column(String(10), default="mensual", nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="cortesia", nullable=False)

    inicia_en: Mapped[date] = mapped_column(Date, nullable=False)
    #: Hasta cuando esta pagado. Es la fecha que decide si aparece en morosidad.
    vigente_hasta: Mapped[date | None] = mapped_column(Date)
    nota: Mapped[str | None] = mapped_column(Text)


class CobroCoach(Base):
    """Un pago recibido de una coach. Solo insercion: un cobro mal capturado se corrige con
    otro en negativo, no editando el anterior."""

    __tablename__ = "cobro_coach"
    __table_args__ = (Index("ix_cobro_coach_fecha", "coach_id", "fecha"), ARGS_DE_TABLA)

    coach_id: Mapped[int] = mapped_column(ForeignKey("coach.id"), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    metodo: Mapped[str] = mapped_column(String(40), default="transferencia", nullable=False)

    #: Que periodo cubre. Es lo que permite decir "pago hasta marzo" sin recalcular nada.
    periodo_inicia: Mapped[date | None] = mapped_column(Date)
    periodo_termina: Mapped[date | None] = mapped_column(Date)

    nota: Mapped[str | None] = mapped_column(Text)
    #: Quien lo capturo. Siempre un usuario con rol `admin_plataforma`.
    registrado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))


class CobroProgramado(BaseMultiInquilino):
    """La cuenta por cobrar, no el pago: separarlos permite ver adeudos antes de que exista
    ningun movimiento. Vencido y sin pagar pausa el plan de la alumna."""

    __tablename__ = "cobro_programado"
    __table_args__ = (
        CheckConstraint(
            "motivo in ('inscripcion','mensualidad','cita','material','otro')",
            name="motivo_valido",
        ),
        # `en_revision` tiene que estar aqui y no solo en la migracion 0005: una base creada
        # desde los modelos naceria con el CHECK viejo y rechazaria todo comprobante.
        CheckConstraint(
            "estado in ('pendiente','en_revision','pagado','cancelado')",
            name="estado_cobro_valido",
        ),
        CheckConstraint("monto > 0", name="monto_positivo"),
        Index("ix_cobro_alumna_fecha", "alumna_id", "fecha"),
        ARGS_DE_TABLA,
    )

    alumna_id: Mapped[int] = mapped_column(ForeignKey("alumna.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    motivo: Mapped[str] = mapped_column(String(20), default="mensualidad", nullable=False)
    #: Lo que la alumna lee. Si va vacio se arma con el motivo.
    concepto: Mapped[str | None] = mapped_column(String(180))
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="pendiente", nullable=False)

    #: El ingreso que lo salda. Nulo mientras esta pendiente.
    movimiento_id: Mapped[int | None] = mapped_column(ForeignKey("movimiento_financiero.id"))
    pagado_en: Mapped[date | None] = mapped_column(Date)
    nota: Mapped[str | None] = mapped_column(Text)

    # --- Comprobante que sube la alumna ---
    #: En el volumen cifrado. Ella elige contra que cobro, asi llega ya emparejado.
    comprobante_key: Mapped[str | None] = mapped_column(String(255))
    subido_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)

    #: Lo que el OCR entendio. No valida nada: un comprobante es una imagen editable.
    ocr: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    confianza: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))

    #: Lo lee la alumna tal cual.
    motivo_rechazo: Mapped[str | None] = mapped_column(Text)
    revisado_en: Mapped[datetime | None] = mapped_column(MARCA_DE_TIEMPO)
