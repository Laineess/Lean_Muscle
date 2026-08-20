"""Las partes puras de imágenes, almacenamiento, OCR y push.

Lo que no se puede probar sin tesseract ni sin un navegador queda fuera: `interpretar` se
prueba con texto, y el envío con el emisor en memoria.
"""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

import pytest

from app.dominio.avisos import Aviso, Canal, canales_de
from app.servicios import almacenamiento as alm
from app.servicios import ocr, push

# ---------------------------------------------------------------------------
# Llaves de almacenamiento
# ---------------------------------------------------------------------------


class TestLlaves:
    def test_la_llave_lleva_el_inquilino_al_frente(self) -> None:
        # Es la capa 4 del aislamiento: antes de servir, se compara este prefijo.
        llave = alm.llave_de_foto(7, 42, 100, "frontal")
        assert llave.startswith("coach/7/")

    def test_reconoce_su_propio_inquilino(self) -> None:
        llave = alm.llave_de_foto(7, 42, 100, "frontal")
        assert alm.pertenece_a(llave, 7)
        assert not alm.pertenece_a(llave, 8)

    def test_el_prefijo_no_se_confunde_con_otro_que_empieza_igual(self) -> None:
        # Sin la barra final, la coach 7 pasaría por dueña de lo de la coach 70.
        assert not alm.pertenece_a(alm.llave_de_foto(70, 1, 1, "frontal"), 7)

    @pytest.mark.parametrize(
        "llave",
        ["../../etc/passwd", "/etc/passwd", "coach/1/../../fuera.webp", "", "coach/1/a b.webp"],
    )
    def test_rechaza_llaves_que_salen_del_directorio(self, llave: str) -> None:
        with pytest.raises(alm.LlaveInvalida):
            alm.validar(llave)

    def test_acepta_una_llave_normal(self) -> None:
        assert alm.validar("coach/1/alumna/2/chequeo/3/frontal.webp")


class TestAlmacenEnMemoria:
    def test_guarda_lee_y_borra(self) -> None:
        a = alm.AlmacenEnMemoria()
        llave = alm.llave_de_foto(1, 2, 3, "perfil")
        a.guardar(llave, b"contenido")
        assert a.existe(llave)
        assert a.leer(llave) == b"contenido"
        a.borrar(llave)
        assert not a.existe(llave)

    def test_borrar_lo_que_no_existe_no_revienta(self) -> None:
        # El trabajo de purga borra en lote; que falle por uno ausente detendría el resto.
        alm.AlmacenEnMemoria().borrar(alm.llave_de_foto(1, 2, 3, "espalda"))


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

COMPROBANTE = """
BBVA México
Comprobante de transferencia SPEI

Monto: $1,200.00
Fecha: 14/07/2026
Clave de rastreo: SPEI4471982
Cuenta destino: 012180001234567890
Saldo disponible: 45,300.00
"""


class TestOcr:
    def test_extrae_los_cuatro_campos(self) -> None:
        r = ocr.interpretar(COMPROBANTE)
        assert r.monto == Decimal("1200.00")
        assert r.fecha == date(2026, 7, 14)
        assert r.referencia == "SPEI4471982"
        assert r.banco == "BBVA"

    def test_prefiere_el_numero_que_sigue_a_monto(self) -> None:
        # El saldo (45 300) es mayor que el importe: sin la pista, ganaría el saldo.
        assert ocr.interpretar(COMPROBANTE).monto == Decimal("1200.00")

    def test_ignora_la_cuenta_larga(self) -> None:
        assert ocr.interpretar(COMPROBANTE).monto != Decimal("12180001234567890")

    def test_lee_fecha_en_formato_iso(self) -> None:
        assert ocr.interpretar("Fecha 2026-08-13 monto $500.00").fecha == date(2026, 8, 13)

    def test_lee_fecha_escrita_con_letras(self) -> None:
        assert ocr.interpretar("14 de julio de 2026, monto $900").fecha == date(2026, 7, 14)

    def test_una_fecha_imposible_no_revienta(self) -> None:
        assert ocr.interpretar("Fecha: 31/02/2026 monto $100.00").fecha is None

    def test_un_texto_vacio_da_confianza_cero(self) -> None:
        r = ocr.interpretar("")
        assert r.confianza == Decimal(0)
        assert r.requiere_revision

    def test_solo_el_monto_no_alcanza_para_confiar(self) -> None:
        # Es deliberado: el monto solo no basta para dar por bueno un comprobante.
        r = ocr.interpretar("Monto: $1,200.00")
        assert r.monto == Decimal("1200.00")
        assert r.requiere_revision

    def test_un_comprobante_completo_no_pide_revision(self) -> None:
        assert not ocr.interpretar(COMPROBANTE).requiere_revision

    def test_el_json_es_serializable(self) -> None:
        import json

        json.dumps(ocr.interpretar(COMPROBANTE).como_json())

    def test_leer_sin_tesseract_no_revienta(self) -> None:
        # Un comprobante ilegible no debe impedir cobrar: la coach captura a mano.
        r = ocr.leer(b"esto no es una imagen")
        assert r.confianza == Decimal(0)


# ---------------------------------------------------------------------------
# Push
# ---------------------------------------------------------------------------

CONTEXTO = {
    "coach": "Mariana",
    "nombre": "Andrea",
    "fecha": "17 de agosto",
    "hora_inicio": "09:00",
    "vence": "14/09/2026",
    "motivo": "Se empalmó una urgencia.",
    "titulo": "Lunes de arranque",
    "cuerpo": "No tiene que ser perfecto, tiene que ser hoy.",
    "alumna": "Andrea Sáenz",
}

POR_PUSH = [a for a in Aviso if Canal.PUSH in canales_de(a)]

#: El único cuyo texto no escribimos nosotros: lo teclea la coach y llega tal cual, así que
#: no se le puede exigir que quepa en una pantalla de bloqueo.
REDACTADOS = [a for a in POR_PUSH if a is not Aviso.MENSAJE_DE_COACH]


class TestPush:
    def test_hay_avisos_por_push(self) -> None:
        assert POR_PUSH

    @pytest.mark.parametrize("aviso", POR_PUSH, ids=lambda a: a.value)
    def test_cada_aviso_por_push_tiene_texto(self, aviso: Aviso) -> None:
        assert aviso in push.TEXTOS, f"{aviso.value} sale por push y no tiene texto"

    @pytest.mark.parametrize("aviso", POR_PUSH, ids=lambda a: a.value)
    def test_los_textos_se_rellenan_sin_huecos(self, aviso: Aviso) -> None:
        n = push.redactar(aviso, CONTEXTO)
        assert "{" not in n.titulo and "{" not in n.cuerpo
        assert n.titulo and n.cuerpo

    @pytest.mark.parametrize("aviso", REDACTADOS, ids=lambda a: a.value)
    def test_caben_en_la_pantalla_de_bloqueo(self, aviso: Aviso) -> None:
        # Lo que no cabe se corta a media palabra en el teléfono.
        n = push.redactar(aviso, CONTEXTO)
        assert len(n.titulo) <= 42, n.titulo
        assert len(n.cuerpo) <= 90, n.cuerpo

    def test_lo_que_escribe_la_coach_llega_sin_tocarse(self) -> None:
        # Es el único aviso sin plantilla: reescribirle una palabra sería inaceptable.
        n = push.redactar(Aviso.MENSAJE_DE_COACH, CONTEXTO)
        assert n.titulo == CONTEXTO["titulo"]
        assert n.cuerpo == CONTEXTO["cuerpo"]

    def test_las_llaves_de_lo_que_escribe_la_coach_no_se_interpretan(self) -> None:
        """Un `{peso}` en su frase es texto, no una plantilla a rellenar: si se interpretara,
        escribir una llave le reventaría el envío a todas sus alumnas."""
        n = push.redactar(Aviso.MENSAJE_DE_COACH, {**CONTEXTO, "cuerpo": "Sube tu {peso} de hoy"})
        assert n.cuerpo == "Sube tu {peso} de hoy"

    def test_la_etiqueta_evita_avisos_apilados(self) -> None:
        # Etiqueta igual reemplaza el anterior en la bandeja en vez de sumarse.
        n = push.redactar(Aviso.RECORDATORIO_CHEQUEO, CONTEXTO)
        assert n.etiqueta == Aviso.RECORDATORIO_CHEQUEO.value

    def test_dos_frases_distintas_no_se_pisan_en_la_bandeja(self) -> None:
        """Un recordatorio repetido debe reemplazar al anterior; dos frases suyas, no."""
        una = push.redactar(Aviso.MENSAJE_DE_COACH, {**CONTEXTO, "etiqueta": "anuncio:A"})
        otra = push.redactar(Aviso.MENSAJE_DE_COACH, {**CONTEXTO, "etiqueta": "anuncio:B"})
        assert una.etiqueta != otra.etiqueta

    def test_el_payload_respeta_el_tope_del_estandar(self) -> None:
        larga = push.Notificacion(titulo="t", cuerpo="x" * 5000)
        assert len(larga.como_json()) <= push.BYTES_MAXIMOS

    def test_no_hay_textos_de_push_huerfanos(self) -> None:
        assert not set(push.TEXTOS) - set(Aviso)

    def test_el_emisor_en_memoria_no_manda_nada(self) -> None:
        emisor = push.EmisorEnMemoria()
        r = emisor.enviar(
            push.Suscripcion("https://ejemplo/x", "clave", "auth"),
            push.redactar(Aviso.PLAN_PUBLICADO, CONTEXTO),
        )
        assert r.entregada and not r.caducada
        assert len(emisor.enviadas) == 1


# ---------------------------------------------------------------------------
# Imágenes
# ---------------------------------------------------------------------------


def _png(ancho: int, alto: int, color: tuple[int, int, int] = (120, 120, 120)) -> bytes:
    from PIL import Image

    salida = io.BytesIO()
    Image.new("RGB", (ancho, alto), color).save(salida, format="PNG")
    return salida.getvalue()


class TestImagenes:
    def test_recorta_la_cabeza(self) -> None:
        from app.servicios import imagenes

        # El punto entero del módulo: la parte de arriba desaparece antes de guardar.
        r = imagenes.procesar(_png(800, 1000))
        assert r.alto < 1000
        assert abs(r.alto - int(1000 * (1 - imagenes.FRACCION_CABEZA))) <= 2

    def test_reescala_lo_grande(self) -> None:
        from app.servicios import imagenes

        r = imagenes.procesar(_png(4000, 5000))
        assert max(r.ancho, r.alto) <= imagenes.LADO_MAXIMO

    def test_una_imagen_plana_se_rechaza_por_borrosa(self) -> None:
        from app.servicios import imagenes

        # Un color liso no tiene bordes: su varianza del laplaciano es cero.
        r = imagenes.procesar(_png(800, 1000))
        assert r.estado_auto == "rechazada"
        assert r.motivo_rechazo is not None and "borrosa" in r.motivo_rechazo

    def test_una_imagen_oscura_se_rechaza_por_luz(self) -> None:
        from app.servicios import imagenes

        r = imagenes.procesar(_png(800, 1000, (12, 12, 12)))
        assert r.estado_auto == "rechazada"

    def test_lo_que_no_es_imagen_se_rechaza(self) -> None:
        from app.servicios import imagenes

        with pytest.raises(imagenes.ImagenInvalida):
            imagenes.procesar(b"no soy una imagen")

    def test_un_archivo_vacio_se_rechaza(self) -> None:
        from app.servicios import imagenes

        with pytest.raises(imagenes.ImagenInvalida):
            imagenes.procesar(b"")

    def test_una_imagen_diminuta_se_rechaza(self) -> None:
        from app.servicios import imagenes

        with pytest.raises(imagenes.ImagenInvalida):
            imagenes.procesar(_png(50, 50))

    def test_la_salida_es_webp_sin_metadatos(self) -> None:
        from PIL import Image

        from app.servicios import imagenes

        r = imagenes.procesar(_png(800, 1000))
        salida = Image.open(io.BytesIO(r.contenido))
        assert salida.format == "WEBP"
        # Sin EXIF: la geolocalización de una foto corporal es más peligrosa que la foto.
        assert not salida.getexif()


def test_bajo_pruebas_el_correo_nunca_sale_de_verdad(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un `.env` con el envío encendido no debe convertir la suite en un emisor de correo:
    aquí se dan de alta alumnas con direcciones que parecen reales."""
    from app.servicios import correo as mod

    monkeypatch.setattr(mod, "_emisor", None)
    assert isinstance(mod.emisor(), mod.EmisorEnMemoria)
