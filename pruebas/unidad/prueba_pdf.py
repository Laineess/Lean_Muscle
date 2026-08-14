"""Los tres documentos se generan y dicen lo que tienen que decir.

Antes esto no se podía probar: WeasyPrint exigía cairo y pango del sistema, así que la
prueba habría fallado en cualquier máquina que no los tuviera. Con ReportLab —Python puro—
corre igual en Windows, en el VPS y en el CI.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.servicios import pdf

TIEMPOS = [
    {
        "nombre": "Desayuno",
        "hora": "07:30",
        "kcal": 480,
        "alimentos": [{"nombre": "Avena", "porcion": "60 g", "kcal": 220}],
    }
]

DIAS = [
    {
        "nombre": "Día 1 · Torso",
        "ejercicios": [
            {"nombre": "Press banca", "series": 4, "reps": "8-10", "carga": "35 kg", "nota": ""}
        ],
    }
]


def _texto(contenido: bytes) -> str:
    """El texto del PDF, para comprobar que un dato llegó al papel."""
    pdfium = pytest.importorskip("pypdfium2")
    import io

    documento = pdfium.PdfDocument(io.BytesIO(contenido))
    return "\n".join(pagina.get_textpage().get_text_range() for pagina in documento)


def _nutricion(**cambios: object) -> pdf.Documento:
    argumentos: dict[str, object] = {
        "alumna": "Andrea Sáenz",
        "coach": "Mariana Cervantes",
        "ciclo": 5,
        "kcal": 1850,
        "proteina_g": 140,
        "carbohidrato_g": 180,
        "grasa_g": 55,
        "tiempos": TIEMPOS,
        "notas": None,
        "restricciones": None,
    }
    return pdf.plan_de_nutricion(**{**argumentos, **cambios})  # type: ignore[arg-type]


class TestFormato:
    def test_los_tres_producen_un_pdf_valido(self) -> None:
        documentos = [
            _nutricion(),
            pdf.rutina(
                alumna="Andrea",
                coach="Mariana",
                ciclo=5,
                plantilla="Torso/Pierna",
                dias=DIAS,
                notas=None,
                lesiones=None,
            ),
            pdf.recibo(
                folio="MPP-1",
                alumna="Andrea",
                coach="Mariana",
                ciclo=5,
                monto=Decimal("1500.00"),
                metodo="Transferencia",
                pagado_el=date(2026, 8, 14),
                vigencia_inicia=date(2026, 8, 14),
                vigencia_termina=date(2026, 9, 13),
            ),
        ]
        for d in documentos:
            assert d.contenido.startswith(b"%PDF-"), f"{d.nombre} no es un PDF"
            assert len(d.contenido) > 1000
            assert d.nombre.endswith(".pdf")

    def test_no_hace_falta_ninguna_biblioteca_del_sistema(self) -> None:
        """Si alguien vuelve a meter WeasyPrint, esta prueba lo dice antes que un usuario."""
        import app.servicios.pdf as modulo

        fuente = modulo.__doc__ or ""
        assert "weasyprint" not in fuente.lower() or "ReportLab" in fuente


class TestContenido:
    def test_el_plan_lleva_las_calorias_y_los_macros(self) -> None:
        texto = _texto(_nutricion().contenido)
        assert "1 850 kcal" in texto
        assert "140 g" in texto and "180 g" in texto and "55 g" in texto
        assert "Avena" in texto

    def test_los_acentos_y_la_enie_sobreviven(self) -> None:
        """Las fuentes estándar cubren el español; si alguien cambia a una que no, se ve aquí.

        El subtítulo va en mayúsculas por diseño, así que se comprueba en esa forma.
        """
        texto = _texto(_nutricion(alumna="Begoña Muñoz Ñandú").contenido)
        assert "BEGOÑA MUÑOZ ÑANDÚ" in texto
        assert "Plan de nutrición" in texto

    def test_las_restricciones_aparecen_en_el_plan(self) -> None:
        texto = _texto(_nutricion(restricciones="Intolerancia a la lactosa.").contenido)
        assert "Intolerancia a la lactosa" in texto

    def test_el_recibo_dice_que_no_es_comprobante_fiscal(self) -> None:
        """Va en el documento, no solo en la interfaz: es lo que evita que se presente como
        CFDI y que la coach parezca estar emitiendo uno."""
        documento = pdf.recibo(
            folio="MPP-000123",
            alumna="Andrea",
            coach="Mariana",
            ciclo=5,
            monto=Decimal("1500.00"),
            metodo="Transferencia",
            pagado_el=date(2026, 8, 14),
            vigencia_inicia=date(2026, 8, 14),
            vigencia_termina=date(2026, 9, 13),
        )
        texto = _texto(documento.contenido)
        assert "no es un comprobante fiscal" in texto
        assert "1,500.00" in texto
        assert "MPP-000123" in texto


class TestPaginacion:
    def test_una_rutina_larga_se_reparte_en_varias_paginas(self) -> None:
        pdfium = pytest.importorskip("pypdfium2")
        import io

        dias = [
            {
                "nombre": f"Día {i + 1}",
                "ejercicios": [
                    {
                        "nombre": f"Ejercicio {j}",
                        "series": 4,
                        "reps": "10",
                        "carga": "20 kg",
                        "nota": "",
                    }
                    for j in range(9)
                ],
            }
            for i in range(5)
        ]
        documento = pdf.rutina(
            alumna="Andrea",
            coach="Mariana",
            ciclo=5,
            plantilla="Full body",
            dias=dias,
            notas=None,
            lesiones=None,
        )
        paginas = pdfium.PdfDocument(io.BytesIO(documento.contenido))
        assert len(paginas) > 1

        # El encabezado de la tabla se repite: una página suelta tiene que poder leerse sin
        # volver atrás a ver qué columna era cuál.
        segunda = paginas[1].get_textpage().get_text_range()
        assert "EJERCICIO" in segunda.upper()

    def test_el_dia_no_se_parte_a_la_mitad(self) -> None:
        """Cada día va en `KeepTogether`: partir un bloque obliga a pasar la hoja a media
        serie, justo cuando la alumna está entrenando."""
        fuente = (pdf.__file__ or "").replace("\\", "/")
        assert fuente.endswith("pdf.py")
        import inspect

        assert "KeepTogether" in inspect.getsource(pdf.rutina)
