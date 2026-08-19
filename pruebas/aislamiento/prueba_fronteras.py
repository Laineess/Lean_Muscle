"""Fronteras de import que sostienen el aislamiento entre coaches.

`ruff` ya prohibe estos imports, pero una regla de linter se silencia con un `# noqa` y una
prueba no. Como el aislamiento es la base legal del modelo — una fuga entre inquilinos es
una infraccion sancionable directamente a la coach — la frontera se verifica dos veces.

Esta prueba no necesita base de datos: lee el arbol sintactico de los archivos.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

RAIZ = Path(__file__).resolve().parents[2]
APP = RAIZ / "app"

#: Carpeta -> prefijos de modulo que no puede importar, y por que.
PROHIBICIONES: dict[str, dict[str, str]] = {
    "dominio": {
        "app.datos": "las reglas de negocio se prueban sin base de datos",
        "app.rutas": "el dominio no conoce el transporte",
        "sqlalchemy": "el dominio no conoce el ORM",
        "fastapi": "el dominio no conoce HTTP",
    },
    "rutas": {
        "app.datos.sin_alcance": "una ruta jamas consulta sin alcance de inquilino",
    },
    "servicios": {
        "app.datos.sin_alcance": "los servicios operan dentro del alcance de la peticion",
    },
}

#: `trabajos` y `plataforma` si pueden cruzar inquilinos: es justo para lo que existen.
EXENTOS = {APP / "trabajos", APP / "rutas" / "plataforma"}


def modulos_importados(archivo: Path) -> set[str]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            nombres.add(nodo.module)
    return nombres


def archivos_de(carpeta: str) -> list[Path]:
    base = APP / carpeta
    if not base.exists():
        return []
    return [
        p for p in base.rglob("*.py") if not any(p.is_relative_to(exento) for exento in EXENTOS)
    ]


def casos() -> list[tuple[Path, str, str]]:
    salida: list[tuple[Path, str, str]] = []
    for carpeta, prohibidos in PROHIBICIONES.items():
        for archivo in archivos_de(carpeta):
            for prefijo, motivo in prohibidos.items():
                salida.append((archivo, prefijo, motivo))
    return salida


@pytest.mark.aislamiento
@pytest.mark.parametrize(
    ("archivo", "prohibido", "motivo"),
    casos(),
    ids=lambda v: v.name if isinstance(v, Path) else str(v),
)
def test_no_cruza_la_frontera(archivo: Path, prohibido: str, motivo: str) -> None:
    importados = modulos_importados(archivo)
    culpables = {m for m in importados if m == prohibido or m.startswith(prohibido + ".")}
    assert not culpables, f"{archivo.relative_to(RAIZ)} importa {sorted(culpables)}: {motivo}."


@pytest.mark.aislamiento
def test_toda_entidad_con_datos_de_alumnas_lleva_coach_id() -> None:
    """Una tabla nueva que herede de `Base` en lugar de `BaseMultiInquilino` es
    exactamente como se escapan los datos. Las excepciones se declaran aqui a mano,
    para que agregar una obligue a pensarlo."""
    sin_inquilino_a_proposito = {
        "Coach",  # es la raiz del aislamiento
        "Alimento",  # coach_id nulo = base publica compartida
        "Ejercicio",  # idem
        "Vulneracion",  # una vulneracion puede cruzar inquilinos
        "Trabajo",  # cola de trabajos del sistema
        # Lo que la coach le paga a la plataforma. Es un dato *sobre* el inquilino, no *del*
        # inquilino: pertenece a la relacion comercial, igual que la fila de `coach`. Si
        # llevaran el filtro, el superadmin —que no es coach de nadie— no veria ninguna.
        "SuscripcionCoach",
        "CobroCoach",
        # Al intentar entrar todavia no se sabe de que coach es el correo, y uno inventado
        # no es de nadie. Filtrarla por inquilino dejaria sin frenar justo el caso que
        # importa: probar correos al azar.
        "IntentoDeAcceso",
    }

    fuente = (APP / "datos" / "modelos.py").read_text(encoding="utf-8")
    arbol = ast.parse(fuente)

    huerfanas = [
        nodo.name
        for nodo in arbol.body
        if isinstance(nodo, ast.ClassDef)
        and any(isinstance(b, ast.Name) and b.id == "Base" for b in nodo.bases)
        and nodo.name not in sin_inquilino_a_proposito
    ]

    assert not huerfanas, (
        f"{huerfanas} hereda de Base y no de BaseMultiInquilino. Si es a proposito, "
        "declararlo en `sin_inquilino_a_proposito` con el motivo."
    )


def test_el_modelo_y_las_migraciones_declaran_los_mismos_estados() -> None:
    """Un CHECK que diverge no se nota hasta que alguien recrea la base desde los modelos.

    Pasó con `cobro_programado`: la migración agregó `en_revision` y el modelo se quedó con
    los tres estados viejos, así que cualquier base creada con `--reiniciar` rechazaba los
    comprobantes con un 500 del motor.
    """
    modelos = (APP / "datos" / "modelos.py").read_text(encoding="utf-8")
    migraciones = chr(10).join(
        a.read_text(encoding="utf-8")
        for a in (APP.parent / "migraciones" / "versions").glob("*.py")
    )

    for estado in ("en_revision",):
        assert estado in modelos, f"«{estado}» está en una migración y no en los modelos"
        assert estado in migraciones


def _rutas_de(nodo: object) -> Iterator[APIRoute]:
    """Recorre el arbol de ruteadores. FastAPI ya no copia las rutas al incluirlas: las
    anida, asi que quedan a dos niveles de `app.routes`."""
    if isinstance(nodo, APIRoute):
        yield nodo
        return
    hijos = getattr(nodo, "routes", None) or getattr(
        getattr(nodo, "original_router", None), "routes", []
    )
    for hijo in hijos:
        yield from _rutas_de(hijo)


def test_toda_ruta_de_api_confirma_antes_de_responder() -> None:
    """El cierre de una dependencia con `yield` corre despues de responder, asi que sin
    `RutaQueConfirma` el commit queda fuera de la peticion y la siguiente lectura no ve lo
    recien guardado. Un ruteador nuevo que olvide la clase lo revive en silencio."""
    from app.main import app
    from app.rutas.sesion import RutaQueConfirma

    de_api = [r for r in _rutas_de(app) if r.path.startswith("/api")]
    assert len(de_api) > 100, "no se encontraron las rutas: el recorrido quedo vacio"

    sueltas = [r.path for r in de_api if not isinstance(r, RutaQueConfirma)]
    assert not sueltas, f"rutas sin RutaQueConfirma: {sorted(set(sueltas))}"
