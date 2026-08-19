"""PDF de plan, rutina, evolución y recibo. Todos salen con la marca de la coach.

ReportLab y no WeasyPrint: es Python puro y no arrastra cairo ni pango del sistema. Se
compone con Platypus, así una rutina larga reparte sus páginas sola.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

#: Paleta del sistema, apagada para papel. El dorado sobre blanco casi no se ve, así que en
#: impresión el acento es una línea, nunca texto.
TINTA = colors.HexColor("#111111")
TINTA_MEDIA = colors.HexColor("#4a4a4a")
TINTA_SUAVE = colors.HexColor("#767676")
LINEA = colors.HexColor("#d8d8d8")
LINEA_TENUE = colors.HexColor("#eeeeee")
ACENTO = colors.HexColor("#c9a227")
FONDO_AVISO = colors.HexColor("#f6f6f5")

MARGEN_X = 16 * mm
MARGEN_ARRIBA = 18 * mm
MARGEN_ABAJO = 20 * mm

ANCHO_UTIL = letter[0] - 2 * MARGEN_X


def _estilo(nombre: str, **kw: Any) -> ParagraphStyle:
    base = {"fontName": "Helvetica", "fontSize": 10, "leading": 15, "textColor": TINTA}
    return ParagraphStyle(nombre, **{**base, **kw})


TITULO = _estilo("titulo", fontName="Helvetica-Bold", fontSize=20, leading=24, spaceAfter=2)
ETIQUETA = _estilo("etiqueta", fontSize=7.5, leading=11, textColor=TINTA_SUAVE)
CIFRA_GRANDE = _estilo("cifra", fontName="Helvetica-Bold", fontSize=26, leading=30)
SECCION = _estilo("seccion", fontName="Helvetica-Bold", fontSize=12, leading=16)
CUERPO = _estilo("cuerpo")
APOYO = _estilo("apoyo", fontSize=9, leading=13, textColor=TINTA_MEDIA)
NOTA = _estilo("nota", fontSize=9, leading=13, textColor=TINTA_MEDIA, leftIndent=8)
AVISO = _estilo("aviso", fontSize=8.5, leading=12, textColor=TINTA_MEDIA)
PIE = _estilo("pie", fontSize=8, leading=11, textColor=TINTA_SUAVE)
MARCA = _estilo("marca", fontName="Helvetica-Bold", fontSize=10.5, leading=14)
ENCABEZADO_TABLA = _estilo("th", fontSize=7.5, leading=10, textColor=TINTA_SUAVE)
CELDA = _estilo("td", fontSize=9.5, leading=13)
CELDA_DER = _estilo("td-der", fontSize=9.5, leading=13, alignment=TA_RIGHT)


@dataclass(frozen=True, slots=True)
class Documento:
    nombre: str
    contenido: bytes


@dataclass(frozen=True, slots=True)
class Marca:
    """Identidad de la coach en el papel. `logo` son bytes, no una ruta: quien arma el PDF
    no tiene por qué saber dónde vive el archivo."""

    nombre: str
    logo: bytes | None = None
    #: Su color de acento en hexadecimal. Se usa para los filetes, nunca para texto.
    color: str | None = None

    @property
    def acento(self) -> colors.Color:
        if not self.color:
            return ACENTO
        try:
            return colors.HexColor(self.color)
        except ValueError:  # pragma: no cover - defensivo ante un hex mal guardado
            return ACENTO


ALTO_LOGO = 11 * mm


class Filete(Flowable):
    """Una línea horizontal. Separa secciones sin gastar una tabla vacía."""

    def __init__(self, grosor: float = 0.5, color: colors.Color = LINEA) -> None:
        super().__init__()
        self.grosor = grosor
        self.color = color
        self.width = ANCHO_UTIL
        self.height = grosor

    def draw(self) -> None:
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.grosor)
        self.canv.line(0, 0, self.width, 0)


def _e(valor: Any) -> str:
    """Escapa para el mini-HTML de Paragraph, que interpreta `<b>`, `&` y compañía."""
    texto = str(valor if valor is not None else "")
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _logo(marca: Marca) -> Flowable | None:
    """El logo, escalado a lo alto. Si la imagen viene rota, el documento sale sin ella."""
    if not marca.logo:
        return None
    try:
        imagen = Image(io.BytesIO(marca.logo))
        proporcion = imagen.imageWidth / imagen.imageHeight
        imagen.drawHeight = ALTO_LOGO
        imagen.drawWidth = ALTO_LOGO * proporcion
        imagen.hAlign = "RIGHT"
        return imagen
    except Exception:  # pragma: no cover - una imagen ilegible no debe tumbar el PDF
        return None


def _encabezado(titulo: str, subtitulo: str, marca: Marca) -> list[Flowable]:
    """Encabezado con la marca de la coach arriba y el título del documento debajo."""
    logo = _logo(marca)
    ancho_marca = ANCHO_UTIL * (0.6 if logo else 1)
    cabecera = Table(
        [[Paragraph(_e(marca.nombre).upper(), MARCA), logo or ""]],
        colWidths=[ancho_marca, ANCHO_UTIL - ancho_marca],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        ),
    )
    return [
        cabecera,
        Filete(0.75, LINEA),
        Spacer(1, 14),
        Paragraph(_e(titulo), TITULO),
        Paragraph(_e(subtitulo).upper(), ETIQUETA),
        Spacer(1, 5),
        Filete(1.5, marca.acento),
        Spacer(1, 12),
    ]


def _seccion(texto: str, derecha: str = "") -> list[Flowable]:
    """Título de sección con su filete. `derecha` alinea un dato al margen opuesto."""
    fila: Flowable
    if derecha:
        fila = Table(
            [[Paragraph(_e(texto), SECCION), Paragraph(_e(derecha), CELDA_DER)]],
            colWidths=[ANCHO_UTIL * 0.7, ANCHO_UTIL * 0.3],
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            ),
        )
    else:
        fila = Paragraph(_e(texto), SECCION)
    return [Spacer(1, 10), fila, Filete(), Spacer(1, 4)]


#: Encabezado alineado a la derecha, para las columnas numéricas.
ENCABEZADO_DER = _estilo(
    "th-der", fontSize=7.5, leading=10, textColor=TINTA_SUAVE, alignment=TA_RIGHT
)


def _tabla(
    encabezados: list[str] | None,
    filas: list[list[Any]],
    anchos: list[float],
    alinear_derecha_desde: int = 1,
) -> Table:
    """Tabla de datos. Si lleva encabezado, se repite al cortarse entre páginas."""
    datos: list[list[Any]] = []
    if encabezados:
        datos.append(
            [
                Paragraph(
                    _e(h).upper(),
                    ENCABEZADO_DER if i >= alinear_derecha_desde else ENCABEZADO_TABLA,
                )
                for i, h in enumerate(encabezados)
            ]
        )
    for fila in filas:
        datos.append(
            [
                celda
                if isinstance(celda, Flowable)
                else Paragraph(_e(celda), CELDA_DER if i >= alinear_derecha_desde else CELDA)
                for i, celda in enumerate(fila)
            ]
        )

    primera_fila = 1 if encabezados else 0
    tabla = Table(datos, colWidths=anchos, repeatRows=primera_fila, hAlign="LEFT")
    estilo: list[Any] = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, primera_fila), (-1, -2), 0.25, LINEA_TENUE),
    ]
    if encabezados:
        estilo.append(("LINEBELOW", (0, 0), (-1, 0), 0.5, LINEA))
    tabla.setStyle(TableStyle(estilo))
    return tabla


def _bloque_aviso(texto: str) -> Table:
    """Recuadro gris. Se usa para lo que la alumna no debe pasar por alto."""
    return Table(
        [[Paragraph(texto, AVISO)]],
        colWidths=[ANCHO_UTIL],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), FONDO_AVISO),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        ),
    )


def _bloque_nota(texto: str) -> Table:
    """Cita con filete dorado a la izquierda."""
    return Table(
        [[Paragraph(_e(texto), NOTA)]],
        colWidths=[ANCHO_UTIL],
        style=TableStyle(
            [
                ("LINEBEFORE", (0, 0), (0, -1), 1.5, ACENTO),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        ),
    )


def _construir(bloques: list[Flowable], nombre: str, coach: str) -> Documento:
    """Arma el PDF en memoria. El pie va en cada página, no solo en la última."""
    buffer = io.BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=MARGEN_X,
        rightMargin=MARGEN_X,
        topMargin=MARGEN_ARRIBA,
        bottomMargin=MARGEN_ABAJO,
        title=nombre.replace(".pdf", "").replace("-", " ").capitalize(),
        author="MyFittPlan",
    )

    aviso = f"{coach} · MyFittPlan — uso personal; no sustituye atención médica."

    def pie(lienzo: Any, doc: Any) -> None:
        lienzo.saveState()
        y = MARGEN_ABAJO - 6 * mm
        lienzo.setStrokeColor(LINEA)
        lienzo.setLineWidth(0.5)
        lienzo.line(MARGEN_X, y + 10, letter[0] - MARGEN_X, y + 10)
        lienzo.setFont("Helvetica", 7.5)
        lienzo.setFillColor(TINTA_SUAVE)
        lienzo.drawString(MARGEN_X, y, aviso)
        lienzo.drawRightString(letter[0] - MARGEN_X, y, f"Página {doc.page}")
        lienzo.restoreState()

    documento.build(bloques, onFirstPage=pie, onLaterPages=pie)
    return Documento(nombre=nombre, contenido=buffer.getvalue())


# ---------------------------------------------------------------------------
# Plan de nutrición
# ---------------------------------------------------------------------------


def plan_de_nutricion(
    *,
    alumna: str,
    coach: str,
    marca: Marca,
    ciclo: int,
    kcal: int,
    proteina_g: int,
    carbohidrato_g: int,
    grasa_g: int,
    tiempos: list[dict[str, Any]],
    notas: str | None,
    restricciones: str | None,
) -> Documento:
    bloques: list[Flowable] = _encabezado(
        "Plan de nutrición", f"{alumna} · ciclo {ciclo} · {date.today():%d/%m/%Y}", marca
    )
    bloques += [
        Paragraph(f"{kcal:,}".replace(",", " ") + " kcal", CIFRA_GRANDE),
        Paragraph(
            f"Proteína {proteina_g} g · Carbohidratos {carbohidrato_g} g · Grasa {grasa_g} g",
            APOYO,
        ),
    ]

    anchos = [ANCHO_UTIL * 0.56, ANCHO_UTIL * 0.24, ANCHO_UTIL * 0.20]
    for t in tiempos:
        filas = [
            [a.get("nombre"), a.get("porcion"), f"{a.get('kcal')} kcal"]
            for a in t.get("alimentos", [])
        ]
        # Cada tiempo de comida se mantiene junto: partir «Desayuno» a media tabla obliga a
        # pasar la hoja para saber qué se come.
        bloques.append(
            KeepTogether(
                [
                    *_seccion(
                        f"{t.get('nombre')}  {t.get('hora') or ''}".strip(),
                        f"{t.get('kcal')} kcal",
                    ),
                    _tabla(["Alimento", "Porción", "Calorías"], filas, anchos),
                ]
            )
        )

    if notas:
        bloques += [*_seccion(f"Notas de {coach}"), _bloque_nota(notas)]
    if restricciones:
        bloques += [
            Spacer(1, 10),
            _bloque_aviso(f"<b>Tus restricciones:</b> {_e(restricciones)}"),
        ]

    return _construir(bloques, f"plan-nutricion-ciclo-{ciclo}.pdf", coach)


# ---------------------------------------------------------------------------
# Rutina
# ---------------------------------------------------------------------------


def rutina(
    *,
    alumna: str,
    coach: str,
    marca: Marca,
    ciclo: int,
    plantilla: str | None,
    dias: list[dict[str, Any]],
    notas: str | None,
    lesiones: str | None,
) -> Documento:
    bloques: list[Flowable] = _encabezado(
        "Rutina de entrenamiento", f"{alumna} · ciclo {ciclo} · {date.today():%d/%m/%Y}", marca
    )
    if plantilla:
        bloques.append(Paragraph(f"{_e(plantilla)} · {len(dias)} días por semana", APOYO))

    anchos = [
        ANCHO_UTIL * 0.42,
        ANCHO_UTIL * 0.12,
        ANCHO_UTIL * 0.14,
        ANCHO_UTIL * 0.16,
        ANCHO_UTIL * 0.16,
    ]

    for d in dias:
        filas: list[list[Any]] = []
        for e in d.get("ejercicios", []):
            nombre: Any = Paragraph(_e(e.get("nombre")), CELDA)
            if e.get("nota"):
                nombre = Table(
                    [[Paragraph(_e(e.get("nombre")), CELDA)], [Paragraph(_e(e.get("nota")), NOTA)]],
                    colWidths=[anchos[0]],
                    style=TableStyle(
                        [
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ("TOPPADDING", (0, 0), (-1, -1), 0),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                        ]
                    ),
                )
            # La última columna va vacía a propósito: es para palomear a mano en el gimnasio.
            filas.append([nombre, e.get("series"), e.get("reps"), e.get("carga"), ""])

        tabla = _tabla(["Ejercicio", "Series", "Reps", "Carga", "Hecho"], filas, anchos)
        tabla.setStyle(TableStyle([("LINEBELOW", (4, 1), (4, -1), 0.25, TINTA_SUAVE)]))
        bloques.append(KeepTogether([*_seccion(str(d.get("nombre"))), tabla]))

    if notas:
        bloques += [*_seccion(f"Notas de {coach}"), _bloque_nota(notas)]
    if lesiones:
        bloques += [
            Spacer(1, 10),
            _bloque_aviso(f"<b>Cuidado:</b> {_e(lesiones)} Si duele, para."),
        ]

    return _construir(bloques, f"rutina-ciclo-{ciclo}.pdf", coach)


# ---------------------------------------------------------------------------
# Evolución
# ---------------------------------------------------------------------------


def _delta(actual: Decimal | None, previo: Decimal | None, decimales: int = 1) -> str:
    """Diferencia con signo. Es lo que la alumna busca primero al abrir el documento."""
    if actual is None or previo is None:
        return "—"
    d = actual - previo
    signo = "+" if d > 0 else ""
    return f"{signo}{d:.{decimales}f}"


def evolucion(
    *,
    alumna: str,
    coach: str,
    marca: Marca,
    chequeos: list[dict[str, Any]],
    medidas: list[str],
    feedback: str | None,
) -> Documento:
    """Historial de chequeos, del más viejo al más nuevo. Sin fotografías: un PDF sale de
    la plataforma y las imágenes tienen que quedarse donde se pueden purgar."""
    bloques: list[Flowable] = _encabezado("Evolución", f"{alumna} · {date.today():%d/%m/%Y}", marca)

    if not chequeos:
        bloques.append(Paragraph("Todavía no hay chequeos validados.", APOYO))
        return _construir(bloques, "evolucion.pdf", coach)

    primero, ultimo = chequeos[0], chequeos[-1]
    bloques += [
        Paragraph(f"{_e(ultimo.get('peso_kg'))} kg", CIFRA_GRANDE),
        Paragraph(
            f"{_delta(ultimo.get('peso_kg'), primero.get('peso_kg'))} kg desde el primer "
            f"chequeo · {len(chequeos)} registros",
            APOYO,
        ),
    ]

    anchos = [ANCHO_UTIL * 0.16, ANCHO_UTIL * 0.12, ANCHO_UTIL * 0.16, ANCHO_UTIL * 0.14]
    resto = ANCHO_UTIL - sum(anchos)
    anchos += [resto / 2, resto / 2]

    filas: list[list[Any]] = []
    for i, c in enumerate(chequeos):
        previo = chequeos[i - 1] if i else None
        grasa = c.get("porcentaje_grasa")
        filas.append(
            [
                c.get("fecha"),
                c.get("numero"),
                c.get("peso_kg"),
                f"{grasa:.1f} %" if grasa is not None else "—",
                _delta(c.get("peso_kg"), previo.get("peso_kg") if previo else None),
                _delta(
                    c.get("porcentaje_grasa"),
                    previo.get("porcentaje_grasa") if previo else None,
                ),
            ]
        )

    bloques += [
        *_seccion("Peso y composición"),
        _tabla(["Fecha", "Ciclo", "Peso", "% grasa", "Δ peso", "Δ grasa"], filas, anchos),
    ]

    if medidas:
        anchos_m = [ANCHO_UTIL * 0.28] + [(ANCHO_UTIL * 0.72) / max(len(chequeos), 1)] * len(
            chequeos
        )
        filas_m: list[list[Any]] = []
        for tipo in medidas:
            filas_m.append(
                [tipo.capitalize()] + [c.get("medidas", {}).get(tipo, "—") for c in chequeos]
            )
        bloques += [
            *_seccion("Medidas", "cm"),
            _tabla(["Medida"] + [str(c.get("fecha")) for c in chequeos], filas_m, anchos_m),
        ]

    if feedback:
        bloques += [*_seccion(f"Último comentario de {coach}"), _bloque_nota(feedback)]

    return _construir(bloques, "evolucion.pdf", coach)


# ---------------------------------------------------------------------------
# Recibo de pago
# ---------------------------------------------------------------------------


def recibo(
    *,
    folio: str,
    alumna: str,
    coach: str,
    marca: Marca,
    concepto: str,
    monto: Decimal,
    metodo: str,
    pagado_el: date,
    vigencia_inicia: date | None = None,
    vigencia_termina: date | None = None,
) -> Documento:
    """Recibo de gestión, no comprobante fiscal. Va dicho en el propio documento para que
    nadie lo presente como CFDI.

    El concepto entra tal cual y la vigencia es opcional: no todo lo que se cobra es un
    ciclo. Una inscripción se paga antes de que exista ninguno, y un recibo que dijera
    «Ciclo 0 de acompañamiento» sería mentira impresa.
    """
    bloques: list[Flowable] = _encabezado("Recibo", f"Folio {folio} · {coach}", marca)
    filas = [["Alumna", alumna], ["Concepto", concepto]]
    if vigencia_inicia is not None and vigencia_termina is not None:
        filas.append(
            ["Vigencia", f"{vigencia_inicia:%d/%m/%Y} al {vigencia_termina:%d/%m/%Y}"]
        )
    filas += [["Método de pago", metodo], ["Fecha de pago", f"{pagado_el:%d/%m/%Y}"]]

    bloques += [
        Paragraph(f"${monto:,.2f} MXN", CIFRA_GRANDE),
        Spacer(1, 12),
        _tabla(None, filas, [ANCHO_UTIL * 0.35, ANCHO_UTIL * 0.65]),
        Spacer(1, 14),
        _bloque_aviso(
            "<b>Este recibo no es un comprobante fiscal.</b> Es constancia de que tu pago fue "
            "validado y de la vigencia de tu acceso. Si necesitas factura, pídesela a tu coach."
        ),
    ]
    return _construir(bloques, f"recibo-{folio}.pdf", coach)
