"""Lectura de comprobantes de pago.

Con **pytesseract** sobre el binario del sistema: sin costo por documento y, sobre todo, el
comprobante nunca sale del servidor. Mandarlo a un servicio externo sería una transferencia
de datos financieros que habría que declarar en el aviso de privacidad.

**El OCR no valida nada: sugiere.** La coach confirma siempre. Un comprobante es una imagen
que cualquiera puede editar, así que ningún grado de confianza automática sustituye a que
alguien mire su estado de cuenta.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

#: Por debajo de esto, la pantalla le pide a la coach revisar el comprobante a ojo.
CONFIANZA_BAJA = Decimal("0.85")

#: Montos con separador de miles opcional y dos decimales opcionales.
MONTO = re.compile(r"\$?\s*([0-9]{1,3}(?:[, ][0-9]{3})*(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)")

FECHAS = [
    (re.compile(r"\b([0-3]?\d)[/-]([01]?\d)[/-](20\d{2})\b"), ("d", "m", "a")),
    (re.compile(r"\b(20\d{2})[/-]([01]?\d)[/-]([0-3]?\d)\b"), ("a", "m", "d")),
]

MESES = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}
FECHA_TEXTO = re.compile(r"\b([0-3]?\d)\s+de\s+([a-z]{3})[a-z]*\.?\s+(?:de\s+)?(20\d{2})\b")

REFERENCIA = re.compile(
    r"(?:referencia|folio|clave de rastreo|autorizaci[oó]n|no\.?\s*operaci[oó]n)"
    r"\s*[:\-#]?\s*([A-Z0-9-]{4,30})",
    re.IGNORECASE,
)

BANCOS = [
    "BBVA",
    "Banorte",
    "Santander",
    "Banamex",
    "Citibanamex",
    "HSBC",
    "Scotiabank",
    "Inbursa",
    "Azteca",
    "BanCoppel",
    "Nu",
    "Hey Banco",
    "Klar",
    "Mercado Pago",
    "SPEI",
]

#: Palabras que suelen acompañar al importe. Si el monto sale cerca de una, es más probable
#: que sea el importe y no un número de cuenta.
PISTAS_MONTO = ("monto", "importe", "total", "cantidad", "transferiste", "enviaste")


@dataclass(frozen=True, slots=True)
class Lectura:
    monto: Decimal | None
    fecha: date | None
    referencia: str | None
    banco: str | None
    #: 0 a 1. Es cuántos campos se reconocieron, no una promesa de que sean correctos.
    confianza: Decimal
    texto: str

    @property
    def requiere_revision(self) -> bool:
        return self.confianza < CONFIANZA_BAJA

    def como_json(self) -> dict[str, object]:
        return {
            "monto": str(self.monto) if self.monto is not None else None,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "referencia": self.referencia,
            "banco": self.banco,
        }


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower()


def _monto(texto: str) -> Decimal | None:
    """El importe más probable.

    Se prefiere un número cercano a una palabra como «monto» o «total»; si no hay ninguna,
    el mayor de los candidatos. Un comprobante trae varios números —cuenta, referencia,
    saldo— y quedarse con el primero acierta poco.
    """
    normal = _normalizar(texto)
    candidatos: list[tuple[int, Decimal]] = []

    for coincidencia in MONTO.finditer(texto):
        bruto = coincidencia.group(1).replace(",", "").replace(" ", "")
        try:
            valor = Decimal(bruto)
        except InvalidOperation:
            continue
        # Descarta lo que casi seguro no es dinero: años, folios cortos, cuentas largas.
        if valor <= 0 or valor > Decimal("1000000"):
            continue

        ventana = normal[max(0, coincidencia.start() - 40) : coincidencia.start()]
        prioridad = 1 if any(p in ventana for p in PISTAS_MONTO) else 0
        candidatos.append((prioridad, valor))

    if not candidatos:
        return None
    con_pista = [v for p, v in candidatos if p == 1]
    return max(con_pista) if con_pista else max(v for _, v in candidatos)


def _fecha(texto: str) -> date | None:
    for patron, orden in FECHAS:
        m = patron.search(texto)
        if m:
            partes = dict(zip(orden, m.groups(), strict=True))
            try:
                return date(int(partes["a"]), int(partes["m"]), int(partes["d"]))
            except ValueError:
                continue

    m = FECHA_TEXTO.search(_normalizar(texto))
    if m:
        mes = MESES.get(m.group(2))
        if mes:
            try:
                return date(int(m.group(3)), mes, int(m.group(1)))
            except ValueError:
                return None
    return None


def _banco(texto: str) -> str | None:
    normal = _normalizar(texto)
    for banco in BANCOS:
        if _normalizar(banco) in normal:
            return banco
    return None


def interpretar(texto: str) -> Lectura:
    """Extrae los campos de un texto ya reconocido. Puro: se prueba sin tesseract."""
    monto = _monto(texto)
    fecha = _fecha(texto)
    referencia_m = REFERENCIA.search(texto)
    referencia = referencia_m.group(1).strip() if referencia_m else None
    banco = _banco(texto)

    # La confianza pesa el monto sobre lo demás: es el campo que la coach realmente compara
    # contra su estado de cuenta.
    puntos = Decimal("0.5") if monto is not None else Decimal(0)
    puntos += Decimal("0.2") if fecha is not None else Decimal(0)
    puntos += Decimal("0.2") if referencia is not None else Decimal(0)
    puntos += Decimal("0.1") if banco is not None else Decimal(0)

    return Lectura(
        monto=monto,
        fecha=fecha,
        referencia=referencia,
        banco=banco,
        confianza=puntos,
        texto=texto[:2000],
    )


def leer(contenido: bytes) -> Lectura:
    """Reconoce el texto de la imagen y lo interpreta.

    Si tesseract no está instalado, devuelve una lectura vacía en lugar de reventar: la
    coach captura a mano y el flujo sigue. Un comprobante que no se puede leer no debe
    impedir cobrar.
    """
    try:
        import io

        import pytesseract
        from PIL import Image

        imagen = Image.open(io.BytesIO(contenido))
        # `spa` mejora mucho con acentos y nombres de banco; si no está el paquete de
        # idioma, tesseract cae a inglés solo.
        texto = pytesseract.image_to_string(imagen, lang="spa+eng")
    except Exception:
        return Lectura(None, None, None, None, Decimal(0), "")

    return interpretar(texto)
