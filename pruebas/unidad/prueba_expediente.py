"""El paquete que se lleva la alumna.

Es lo que sostiene los avisos de purga y de baja: si el ZIP sale vacío o le falta una foto,
el aviso que le dice «descarga lo tuyo antes» está mintiendo.
"""

from __future__ import annotations

import io
import zipfile

from app.servicios.expediente import Pieza, carpeta_de_chequeo, empaquetar


def _leer(paquete: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(paquete)) as z:
        return {n: z.read(n) for n in z.namelist()}


class TestEmpaquetar:
    def test_cada_pieza_sale_con_su_contenido_intacto(self) -> None:
        dentro = _leer(
            empaquetar(
                [
                    Pieza("historial.pdf", b"%PDF-1.4 lo que sea"),
                    Pieza("chequeo-01-2026-01-15/frontal.webp", b"RIFF....WEBP"),
                ]
            )
        )
        assert dentro["historial.pdf"] == b"%PDF-1.4 lo que sea"
        assert dentro["chequeo-01-2026-01-15/frontal.webp"] == b"RIFF....WEBP"

    def test_las_carpetas_se_arman_con_las_barras_de_la_ruta(self) -> None:
        dentro = _leer(empaquetar([Pieza("chequeo-02-2026-02-15/perfil.webp", b"x")]))
        assert list(dentro) == ["chequeo-02-2026-02-15/perfil.webp"]

    def test_una_ruta_repetida_entra_una_sola_vez(self) -> None:
        # Un ZIP admite dos entradas con el mismo nombre, pero al abrirlo solo se ve una.
        dentro = _leer(empaquetar([Pieza("a.webp", b"primera"), Pieza("a.webp", b"segunda")]))
        assert dentro == {"a.webp": b"primera"}

    def test_un_paquete_vacio_sigue_siendo_un_zip_valido(self) -> None:
        # Una alumna sin chequeos validados no recibe un archivo roto.
        assert _leer(empaquetar([])) == {}

    def test_el_orden_de_entrada_se_respeta(self) -> None:
        piezas = [Pieza(f"{i}.txt", b"x") for i in range(5)]
        with zipfile.ZipFile(io.BytesIO(empaquetar(piezas))) as z:
            assert z.namelist() == [f"{i}.txt" for i in range(5)]


class TestCarpetaDeChequeo:
    def test_el_numero_lleva_cero_delante_para_que_ordene_solo(self) -> None:
        assert carpeta_de_chequeo(3, "2026-04-15") == "chequeo-03-2026-04-15"

    def test_pasados_los_nueve_no_se_rompe_el_orden(self) -> None:
        nombres = sorted(carpeta_de_chequeo(i, "2026-01-01") for i in (2, 10, 1))
        assert nombres == [
            "chequeo-01-2026-01-01",
            "chequeo-02-2026-01-01",
            "chequeo-10-2026-01-01",
        ]
