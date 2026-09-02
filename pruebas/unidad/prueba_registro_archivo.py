"""Los logs de servidor escriben a `logs/actividad.txt` y `logs/errores.txt`.

Se prueba en directorios temporales a proposito: las rutas del modulo son constantes del repo
(`./logs`), y una prueba no debe ensuciar el arbol de desarrollo con actividad real.
"""

from __future__ import annotations

from pathlib import Path

from app.servicios import registro_archivo as m


def _limpiar_handlers() -> None:
    m.registro_actividad.handlers.clear()
    m.registro_errores.handlers.clear()


def test_actividad_solo_lleva_lineas_info(tmp_path: Path) -> None:
    _limpiar_handlers()
    m.ARCHIVO_ACTIVIDAD = tmp_path / "actividad.txt"
    m.ARCHIVO_ERRORES = tmp_path / "errores.txt"
    try:
        m.configurar_logs_de_archivo()
        m.registrar_actividad("ip=1.2.3.4 metodo=GET ruta=/salud estado=200 ms=3")
        # Un ERROR no debe colarse en el archivo de actividad aunque se emita al logger.
        m.registro_actividad.error("esto no deberia aparecer aqui")
    finally:
        _limpiar_handlers()

    contenido = (tmp_path / "actividad.txt").read_text(encoding="utf-8")
    assert "ruta=/salud estado=200" in contenido
    assert "esto no deberia aparecer" not in contenido


def test_errores_llevan_la_traza_completa(tmp_path: Path) -> None:
    _limpiar_handlers()
    m.ARCHIVO_ACTIVIDAD = tmp_path / "actividad.txt"
    m.ARCHIVO_ERRORES = tmp_path / "errores.txt"
    try:
        m.configurar_logs_de_archivo()
        try:
            raise ValueError("la pila del problema")
        except ValueError:
            m.registrar_error("error no controlado en /ruta | ip=9.9.9.9", exc_info=True)
    finally:
        _limpiar_handlers()

    contenido = (tmp_path / "errores.txt").read_text(encoding="utf-8")
    assert "error no controlado en /ruta" in contenido
    assert "ValueError" in contenido
    assert "la pila del problema" in contenido
    # Aunque el ERROR tambien se emita a nivel log, no debe ensuciar la actividad.
    assert (tmp_path / "actividad.txt").read_text(encoding="utf-8").strip() == ""


def test_configurar_es_idempotente(tmp_path: Path) -> None:
    """Llamar dos veces no duplica manejadores: en local con `--reload` se redispara."""
    _limpiar_handlers()
    m.ARCHIVO_ACTIVIDAD = tmp_path / "a.txt"
    m.ARCHIVO_ERRORES = tmp_path / "e.txt"
    try:
        m.configurar_logs_de_archivo()
        m.configurar_logs_de_archivo()
        assert len(m.registro_actividad.handlers) == 1
        assert len(m.registro_errores.handlers) == 1
    finally:
        _limpiar_handlers()
