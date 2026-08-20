"""Un aviso encolado tiene que traer todo lo que su plantilla pide.

Esto existe por un fallo real: `PAGO_VALIDADO` se encolaba sin `folio` ni `concepto`, así
que el correo moría con un `KeyError` en el trabajo de las tres de la mañana. La coach
validaba el pago, la alumna no recibía su recibo, y el único rastro era una columna `error`
que nadie mira. **Ningún barrido lo veía**: encolar respondía 200 y el fallo ocurría horas
después, fuera de la petición.

Se lee el árbol sintáctico de las rutas y los trabajos, y se resuelven las tres formas en
que se encola en este código:

1. Con el aviso escrito ahí mismo: `encolar(s, Aviso.X, ..., contexto={...})`.
2. Desde un ayudante que lo recibe como parámetro —que es justo donde vivía el fallo—:
   se buscan las llamadas al ayudante para saber qué avisos le llegan.
3. Desde el trabajo diario, que encola lo que devuelve `toca_*`: qué aviso construye cada
   una de esas funciones se saca del propio `app/dominio/avisos.py`.

No necesita base de datos.
"""

from __future__ import annotations

import ast
import string
from pathlib import Path

import pytest

from app.dominio.avisos import Aviso, Canal, canales_de
from app.servicios import push
from app.servicios.plantillas_correo import PLANTILLAS

RAIZ = Path(__file__).resolve().parents[2]
FUENTES = [RAIZ / "app" / "rutas", RAIZ / "app" / "trabajos"]
DOMINIO = RAIZ / "app" / "dominio" / "avisos.py"

#: Llaves que el emisor necesita para armar el PDF adjunto. No salen de la plantilla —no
#: aparecen en el texto— y sin ellas el envío falla igual.
DEL_ADJUNTO: dict[Aviso, set[str]] = {
    Aviso.PAGO_VALIDADO: {
        "folio",
        "alumna",
        "concepto",
        "monto_numero",
        "metodo",
        "pagado_el",
        "vigencia_inicia",
        "vigencia_termina",
    },
    Aviso.BAJA_CONFIRMADA: {"alumna_id"},
}

#: Llaves que pone el emisor, no quien encola.
DEL_EMISOR = {"etiqueta"}


def _huecos(texto: str) -> set[str]:
    """Los `{nombres}` de una plantilla, que es lo que `format` va a exigir."""
    return {campo for _, campo, _, _ in string.Formatter().parse(texto) if campo}


def exigidas(aviso: Aviso) -> set[str]:
    llaves: set[str] = set()
    if Canal.CORREO in canales_de(aviso) and aviso in PLANTILLAS:
        plantilla = PLANTILLAS[aviso]
        llaves |= _huecos(plantilla.asunto) | _huecos(plantilla.texto)
    if Canal.PUSH in canales_de(aviso) and aviso in push.TEXTOS:
        titulo, cuerpo, _ = push.TEXTOS[aviso]
        llaves |= _huecos(titulo) | _huecos(cuerpo)
    return (llaves | DEL_ADJUNTO.get(aviso, set())) - DEL_EMISOR


def _aviso_literal(nodo: ast.expr) -> Aviso | None:
    """`Aviso.X`, `AvisoDominio.X` o `av.Aviso.X` -> el valor."""
    if not isinstance(nodo, ast.Attribute):
        return None
    try:
        return Aviso[nodo.attr]
    except KeyError:
        return None


def _claves(nodo: ast.expr | None) -> set[str] | None:
    if not isinstance(nodo, ast.Dict):
        return None
    return {k.value for k in nodo.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}


def avisos_por_funcion_del_dominio() -> dict[str, Aviso]:
    """Qué aviso construye cada `toca_*`. Sale del dominio para que no haya una tabla que
    mantener a mano."""
    arbol = ast.parse(DOMINIO.read_text(encoding="utf-8"))
    salida: dict[str, Aviso] = {}
    for nodo in arbol.body:
        if not isinstance(nodo, ast.FunctionDef) or not nodo.name.startswith("toca_"):
            continue
        for hijo in ast.walk(nodo):
            aviso = _aviso_literal(hijo) if isinstance(hijo, ast.Attribute) else None
            if aviso is not None:
                salida[nodo.name] = aviso
                break
    return salida


DEL_DOMINIO = avisos_por_funcion_del_dominio()


def _nombre_llamado(nodo: ast.Call) -> str:
    """`cola.encolar(...)` y `_encolar(...)` son la misma cosa vista distinto."""
    if isinstance(nodo.func, ast.Attribute):
        return nodo.func.attr
    if isinstance(nodo.func, ast.Name):
        return nodo.func.id
    return ""


def _llamadas_encolar(arbol: ast.AST) -> list[ast.Call]:
    return [
        n
        for n in ast.walk(arbol)
        if isinstance(n, ast.Call) and _nombre_llamado(n) in ("encolar", "_encolar")
    ]


def _argumento(llamada: ast.Call, nombre: str, posicion: int) -> ast.expr | None:
    for k in llamada.keywords:
        if k.arg == nombre:
            return k.value
    return llamada.args[posicion] if len(llamada.args) > posicion else None


def casos() -> list[tuple[str, Aviso, set[str]]]:
    """(archivo, aviso, llaves del contexto) por cada forma de encolar que se puede leer."""
    salida: list[tuple[str, Aviso, set[str]]] = []
    pendientes_por_ayudante: dict[str, tuple[str, str, set[str]]] = {}

    arboles = {
        archivo: ast.parse(archivo.read_text(encoding="utf-8"))
        for carpeta in FUENTES
        for archivo in sorted(carpeta.rglob("*.py"))
    }

    for archivo, arbol in arboles.items():
        for funcion in [n for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef)]:
            # Qué variable guarda el resultado de un `toca_*`, y desde qué línea. Importa
            # la línea: `correr()` reutiliza el mismo nombre cinco veces con avisos
            # distintos, y quedarse con la última asignación revisaría el aviso equivocado.
            asignaciones = sorted(
                (
                    asignacion.lineno,
                    asignacion.targets[0].id,
                    DEL_DOMINIO[asignacion.value.func.attr],
                )
                for asignacion in ast.walk(funcion)
                if isinstance(asignacion, ast.Assign)
                and asignacion.targets
                and isinstance(asignacion.targets[0], ast.Name)
                and isinstance(asignacion.value, ast.Call)
                and isinstance(asignacion.value.func, ast.Attribute)
                and asignacion.value.func.attr in DEL_DOMINIO
            )

            def de_toca(
                nombre: str, linea: int, _asignaciones: list = asignaciones
            ) -> Aviso | None:
                previas = [a for ln, n, a in _asignaciones if n == nombre and ln < linea]
                return previas[-1] if previas else None

            # Y qué variable guarda un diccionario de contexto, con su línea.
            contextos = sorted(
                (asignacion.lineno, asignacion.targets[0].id, _claves(asignacion.value) or set())
                for asignacion in ast.walk(funcion)
                if isinstance(asignacion, ast.Assign)
                and asignacion.targets
                and isinstance(asignacion.targets[0], ast.Name)
                and isinstance(asignacion.value, ast.Dict)
            )

            def contexto_de(
                nombre: str, linea: int, _contextos: list = contextos
            ) -> set[str] | None:
                previos = [c for ln, n, c in _contextos if n == nombre and ln < linea]
                return previos[-1] if previos else None

            parametros = [a.arg for a in funcion.args.args]

            for llamada in _llamadas_encolar(funcion):
                crudo = _argumento(llamada, "contexto", 5)
                claves = _claves(crudo)
                if claves is None and isinstance(crudo, ast.Name):
                    claves = contexto_de(crudo.id, llamada.lineno)
                if claves is None:
                    continue

                # Forma 1: el aviso está escrito ahí mismo.
                cual = _argumento(llamada, "aviso", 1)
                if cual is None:
                    continue
                aviso = _aviso_literal(cual)
                if aviso is not None:
                    salida.append((archivo.name, aviso, claves))
                    continue

                if isinstance(cual, ast.Name):
                    # Forma 3: encola lo que devolvió un `toca_*` de este mismo cuerpo.
                    del_dominio = de_toca(cual.id, llamada.lineno)
                    if del_dominio is not None:
                        salida.append((f"{archivo.name}:{llamada.lineno}", del_dominio, claves))
                        continue
                    # Forma 2: lo recibe como parámetro; se resuelve por quien lo llama.
                    if cual.id in parametros:
                        pendientes_por_ayudante[funcion.name] = (
                            archivo.name,
                            cual.id,
                            claves,
                        )
                elif isinstance(cual, ast.Attribute) and isinstance(cual.value, ast.Name):
                    # `pendiente.aviso`: el aviso lo trae el objeto del dominio.
                    del_dominio = de_toca(cual.value.id, llamada.lineno)
                    if del_dominio is not None:
                        salida.append((f"{archivo.name}:{llamada.lineno}", del_dominio, claves))

    # Forma 2, segunda mitad: qué avisos le llegan a cada ayudante.
    for archivo, arbol in arboles.items():
        for llamada in [n for n in ast.walk(arbol) if isinstance(n, ast.Call)]:
            nombre = _nombre_llamado(llamada)
            if nombre not in pendientes_por_ayudante:
                continue
            donde, _, claves = pendientes_por_ayudante[nombre]
            for arg in list(llamada.args) + [k.value for k in llamada.keywords]:
                aviso = _aviso_literal(arg)
                if aviso is not None:
                    salida.append((f"{archivo.name} -> {donde}:{nombre}", aviso, claves))
    return salida


CASOS = casos()


def test_se_encontraron_las_llamadas() -> None:
    # Guarda contra un refactor que renombre `encolar` y deje la prueba sin casos.
    assert len(CASOS) >= 12, f"solo se resolvieron {len(CASOS)} llamadas a encolar"


def test_el_dominio_declara_sus_avisos() -> None:
    assert len(DEL_DOMINIO) >= 4, "no se pudo leer qué aviso construye cada `toca_*`"


@pytest.mark.parametrize(
    ("donde", "aviso", "claves"),
    CASOS,
    ids=lambda v: v.value if isinstance(v, Aviso) else str(v)[:40],
)
def test_el_contexto_trae_lo_que_la_plantilla_pide(
    donde: str, aviso: Aviso, claves: set[str]
) -> None:
    faltan = exigidas(aviso) - claves
    assert not faltan, (
        f"{donde} encola {aviso.value} sin {sorted(faltan)}: el envío moriría con un "
        "KeyError fuera de la petición, donde nadie lo ve."
    )


def test_todo_aviso_que_se_manda_esta_cubierto() -> None:
    """Un aviso con plantilla que nadie encola desde un sitio legible es un aviso que nadie
    está comprobando."""
    cubiertos = {aviso for _, aviso, _ in CASOS}
    #: Los que se encolan desde una prueba o desde la semilla, no desde la aplicación.
    SIN_ENCOLAR = {Aviso.BIENVENIDA, Aviso.CLAVE_TEMPORAL, Aviso.CODIGO_DE_REGISTRO}
    huerfanos = set(PLANTILLAS) - cubiertos - SIN_ENCOLAR
    assert not huerfanos, f"plantillas que nadie encola de forma legible: {sorted(huerfanos)}"
