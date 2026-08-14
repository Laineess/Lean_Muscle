"""Generación de PDF: plan de nutrición, rutina y recibo de pago.

Con **WeasyPrint**: convierte HTML y CSS a PDF sin navegador. En un VPS sin Docker pesa
muchísimo menos que arrastrar un Chromium para imprimir tres páginas.

El HTML se escribe pensando en papel, no en pantalla: sin modo oscuro, sin interacción, con
la unidad en milímetros y saltos de página explícitos. La alumna imprime esto y se lo lleva
al gimnasio.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from html import escape
from typing import Any

#: Hoja de estilo compartida. Los colores son los del sistema, pero apagados: el dorado
#: sobre papel blanco casi no se ve, así que en impresión el acento es una línea, no texto.
ESTILO = """
@page { size: Letter; margin: 18mm 16mm 20mm; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", sans-serif; font-size: 10pt;
       color: #111; line-height: 1.5; margin: 0; }
h1 { font-size: 20pt; margin: 0 0 4pt; letter-spacing: -0.4pt; }
h2 { font-size: 12pt; margin: 18pt 0 6pt; padding-bottom: 3pt;
     border-bottom: 0.5pt solid #d8d8d8; }
h3 { font-size: 10pt; margin: 12pt 0 4pt; }
.encabezado { border-bottom: 1.5pt solid #111; padding-bottom: 8pt; margin-bottom: 4pt; }
.etiqueta { font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.8pt;
            color: #767676; font-weight: 600; }
.cifra { font-variant-numeric: tabular-nums; }
.grande { font-size: 26pt; font-weight: 700; letter-spacing: -1pt; }
table { width: 100%; border-collapse: collapse; margin-top: 4pt; }
th { font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.6pt; color: #767676;
     text-align: left; padding: 3pt 0; border-bottom: 0.5pt solid #d8d8d8; }
td { padding: 4pt 0; border-bottom: 0.25pt solid #eee; vertical-align: top; }
td.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.nota { border-left: 1.5pt solid #c9a227; padding-left: 8pt; margin: 4pt 0 0;
        font-size: 9pt; color: #4a4a4a; }
.pie { margin-top: 20pt; padding-top: 8pt; border-top: 0.5pt solid #d8d8d8;
       font-size: 8pt; color: #767676; }
.dia { page-break-inside: avoid; margin-bottom: 14pt; }
.aviso { background: #f6f6f5; padding: 8pt; font-size: 8.5pt; margin-top: 12pt; }
"""


@dataclass(frozen=True, slots=True)
class Documento:
    nombre: str
    contenido: bytes


def _a_pdf(html: str, nombre: str) -> Documento:
    """Convierte a PDF.

    WeasyPrint se importa aquí y no arriba a propósito: arrastra bibliotecas del sistema
    (cairo, pango) y tarda en cargar. Importarlo al inicio haría lento el arranque de la
    API entera para una función que se usa poco.
    """
    from weasyprint import HTML

    documento = "<!doctype html><html lang='es-MX'><head><meta charset='utf-8'>"
    documento += f"<style>{ESTILO}</style></head><body>{html}</body></html>"
    return Documento(nombre=nombre, contenido=HTML(string=documento).write_pdf())


def _e(valor: Any) -> str:
    return escape(str(valor if valor is not None else ""))


def _pie(coach: str) -> str:
    return (
        f'<div class="pie">Generado por MyProgressPlan para {_e(coach)}. '
        "Este documento es para tu uso personal; no sustituye la atención médica profesional."
        "</div>"
    )


# ---------------------------------------------------------------------------
# Plan de nutrición
# ---------------------------------------------------------------------------


def plan_de_nutricion(
    *,
    alumna: str,
    coach: str,
    ciclo: int,
    kcal: int,
    proteina_g: int,
    carbohidrato_g: int,
    grasa_g: int,
    tiempos: list[dict[str, Any]],
    notas: str | None,
    restricciones: str | None,
) -> Documento:
    partes = [
        '<div class="encabezado">',
        "<h1>Plan de nutrición</h1>",
        f'<p class="etiqueta">{_e(alumna)} · ciclo {ciclo} · {date.today():%d/%m/%Y}</p>',
        "</div>",
        f'<p class="grande cifra">{kcal} <span style="font-size:11pt;font-weight:400;'
        f'color:#767676">kcal al día</span></p>',
        f'<p class="cifra" style="color:#4a4a4a">Proteína {proteina_g} g · '
        f"Carbohidratos {carbohidrato_g} g · Grasa {grasa_g} g</p>",
    ]

    for t in tiempos:
        filas = "".join(
            f"<tr><td>{_e(a.get('nombre'))}</td>"
            f"<td class='num'>{_e(a.get('porcion'))}</td>"
            f"<td class='num'>{_e(a.get('kcal'))} kcal</td></tr>"
            for a in t.get("alimentos", [])
        )
        partes.append(
            f'<div class="dia"><h2>{_e(t.get("nombre"))} '
            f'<span style="font-weight:400;color:#767676">{_e(t.get("hora"))}</span> '
            f'<span class="cifra" style="float:right;font-weight:400">{_e(t.get("kcal"))} kcal</span></h2>'
            f"<table><thead><tr><th>Alimento</th><th class='num'>Porción</th>"
            f"<th class='num'>Calorías</th></tr></thead><tbody>{filas}</tbody></table></div>"
        )

    if notas:
        partes.append(f'<h2>Notas de {_e(coach)}</h2><p class="nota">{_e(notas)}</p>')
    if restricciones:
        partes.append(
            f'<div class="aviso"><strong>Tus restricciones:</strong> {_e(restricciones)}</div>'
        )

    partes.append(_pie(coach))
    return _a_pdf("".join(partes), f"plan-nutricion-ciclo-{ciclo}.pdf")


# ---------------------------------------------------------------------------
# Rutina
# ---------------------------------------------------------------------------


def rutina(
    *,
    alumna: str,
    coach: str,
    ciclo: int,
    plantilla: str | None,
    dias: list[dict[str, Any]],
    notas: str | None,
    lesiones: str | None,
) -> Documento:
    partes = [
        '<div class="encabezado">',
        "<h1>Rutina de entrenamiento</h1>",
        f'<p class="etiqueta">{_e(alumna)} · ciclo {ciclo} · {date.today():%d/%m/%Y}</p>',
        "</div>",
    ]
    if plantilla:
        partes.append(f'<p style="color:#4a4a4a">{_e(plantilla)} · {len(dias)} días por semana</p>')

    for d in dias:
        filas = "".join(
            f"<tr><td>{_e(e.get('nombre'))}"
            + (f'<p class="nota">{_e(e.get("nota"))}</p>' if e.get("nota") else "")
            + f"</td><td class='num'>{_e(e.get('series'))}</td>"
            f"<td class='num'>{_e(e.get('reps'))}</td>"
            f"<td class='num'>{_e(e.get('carga'))}</td>"
            # Columna en blanco a propósito: es para anotar a mano en el gimnasio.
            f"<td class='num' style='width:60pt;border-bottom:0.25pt solid #999'>&nbsp;</td></tr>"
            for e in d.get("ejercicios", [])
        )
        partes.append(
            f'<div class="dia"><h2>{_e(d.get("nombre"))}</h2>'
            f"<table><thead><tr><th>Ejercicio</th><th class='num'>Series</th>"
            f"<th class='num'>Reps</th><th class='num'>Carga</th>"
            f"<th class='num'>Hecho</th></tr></thead><tbody>{filas}</tbody></table></div>"
        )

    if notas:
        partes.append(f'<h2>Notas de {_e(coach)}</h2><p class="nota">{_e(notas)}</p>')
    if lesiones:
        partes.append(
            f'<div class="aviso"><strong>Cuidado:</strong> {_e(lesiones)} Si duele, para.</div>'
        )

    partes.append(_pie(coach))
    return _a_pdf("".join(partes), f"rutina-ciclo-{ciclo}.pdf")


# ---------------------------------------------------------------------------
# Recibo de pago
# ---------------------------------------------------------------------------


def recibo(
    *,
    folio: str,
    alumna: str,
    coach: str,
    ciclo: int,
    monto: Decimal,
    metodo: str,
    pagado_el: date,
    vigencia_inicia: date,
    vigencia_termina: date,
) -> Documento:
    """Recibo de gestión, **no comprobante fiscal**.

    Decirlo en el propio documento evita que la alumna lo presente como CFDI y evita que la
    coach parezca estar emitiendo uno.
    """
    filas = [
        ("Alumna", alumna),
        ("Concepto", f"Ciclo {ciclo} de acompañamiento"),
        ("Vigencia", f"{vigencia_inicia:%d/%m/%Y} al {vigencia_termina:%d/%m/%Y}"),
        ("Método de pago", metodo),
        ("Fecha de pago", f"{pagado_el:%d/%m/%Y}"),
    ]
    cuerpo = "".join(
        f"<tr><td style='color:#767676'>{_e(k)}</td><td class='num'>{_e(v)}</td></tr>"
        for k, v in filas
    )

    html = (
        '<div class="encabezado"><h1>Recibo</h1>'
        f'<p class="etiqueta">Folio {_e(folio)} · {coach and _e(coach)}</p></div>'
        f'<p class="grande cifra">${monto:,.2f} <span style="font-size:11pt;font-weight:400;'
        'color:#767676">MXN</span></p>'
        f"<table><tbody>{cuerpo}</tbody></table>"
        '<div class="aviso"><strong>Este recibo no es un comprobante fiscal.</strong> '
        "Es constancia de que tu pago fue validado y de la vigencia de tu acceso. Si "
        "necesitas factura, pídesela a tu coach.</div>"
        f"{_pie(coach)}"
    )
    return _a_pdf(html, f"recibo-{folio}.pdf")
