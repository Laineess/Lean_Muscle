"""¿Alguien llega a donde no le toca? Cada endpoint contra cada rol que no es su dueño.

**Los cuerpos se arman válidos.** Mandar `{}` hacía que la respuesta fuera un 422 de
validación en lugar del 403 de la guarda, y un 422 no dice nada sobre permisos: el barrido
reportaba seis sospechas que solo eran cuerpos vacíos. Ahora el cuerpo pasa la validación y
lo que responde es la guarda, que es lo que se está midiendo.

**Al dueño no se le pide nada.** Con cuerpos válidos, probar el camino del dueño mandaría
avisos a todas sus alumnas y crearía filas de basura en cada corrida; que el dueño sí entra
lo comprueba `barrido_botones.py`. Aquí solo se pregunta quién **no** debería pasar.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from typing import Any

BASE = "http://127.0.0.1:8000"
CUENTAS = {
    "coach": "mariana@leanmuscle.mx",
    "alumna": "andrea.saenz@ejemplo.mx",
    "admin": "admin@myfittplan.com",
}

#: Rutas que a propósito no exigen sesión.
PUBLICAS = {"/api/documentos/{clave}", "/api/legal/{clave}", "/salud", "/api/auth/entrar"}

#: Prefijo -> quién debe poder entrar.
DUENO = {"/api/coach/": {"coach"}, "/api/mi/": {"alumna"}, "/api/plataforma/": {"admin"}}

#: Rutas abiertas a más de un rol **a propósito**, cada una con su motivo. Están fuera del
#: barrido porque aquí un 200 de otro rol no es una fuga: es lo que se quiere.
COMPARTIDAS = {
    "/api/mi/push": "la coach también recibe notificaciones; la suscripción cuelga del usuario",
}

#: Valores de ejemplo para los campos con patrón. Se prueban en orden contra el patrón del
#: propio OpenAPI, así que un patrón nuevo no se cuela: si ninguno encaja, el barrido lo dice.
PATRONES = ["01:00", "000000", "#c9a227", "A", "2026-08-19", "01" + "A" * 24, "x"]

ULID_FALSO = "01" + "A" * 24


def cliente(correo: str | None):
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    if correo:
        pedir(op, "/api/auth/login", "POST", {"correo": correo, "contrasena": "Demo1234!"})
    return op


def pedir(op, ruta: str, metodo: str = "GET", cuerpo: Any = None) -> int:
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    pet = urllib.request.Request(BASE + ruta, data=datos, method=metodo)
    if datos:
        pet.add_header("Content-Type", "application/json")
    try:
        with op.open(pet) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Cuerpos que pasan la validación
# ---------------------------------------------------------------------------


def _cadena(esquema: dict, sin_patron: list[str]) -> str:
    patron = esquema.get("pattern")
    if patron:
        for candidato in PATRONES:
            if re.fullmatch(patron, candidato):
                return candidato
        # Nadie encaja: se avisa en lugar de mandar algo que devolverá 422 y parecerá un
        # permiso bien puesto.
        sin_patron.append(patron)
        return "x"

    formato = esquema.get("format")
    if formato == "date":
        return "2026-08-19"
    if formato == "date-time":
        return "2026-08-19T10:00:00Z"
    if formato == "email":
        return "prueba.permisos@ejemplo.mx"
    return "x" * max(1, esquema.get("minLength", 1))


def _numero(esquema: dict, entero: bool) -> Any:
    minimo = esquema.get("minimum")
    if minimo is None:
        minimo = esquema.get("exclusiveMinimum")
        if minimo is not None:
            minimo = minimo + 1
    maximo = esquema.get("maximum", esquema.get("exclusiveMaximum"))

    valor: Any = minimo if minimo is not None else 1
    if maximo is not None and valor > maximo:
        valor = maximo
    return int(valor) if entero else valor


def valor_valido(esquema: dict, comp: dict, sin_patron: list[str], hondo: int = 0) -> Any:
    """Un valor que pasa la validación, del tipo y con las restricciones que declara."""
    if hondo > 6:  # pragma: no cover - defensivo contra un esquema recursivo
        return None
    if "$ref" in esquema:
        return cuerpo_valido(esquema["$ref"], comp, sin_patron, hondo + 1)
    if esquema.get("enum"):
        return esquema["enum"][0]
    if "const" in esquema:
        return esquema["const"]

    for clave in ("anyOf", "oneOf", "allOf"):
        if clave in esquema:
            opciones = [e for e in esquema[clave] if e.get("type") != "null"]
            if opciones:
                return valor_valido(opciones[0], comp, sin_patron, hondo)
            return None

    tipo = esquema.get("type")
    if tipo == "string":
        return _cadena(esquema, sin_patron)
    if tipo == "integer":
        return _numero(esquema, entero=True)
    if tipo == "number":
        return _numero(esquema, entero=False)
    if tipo == "boolean":
        return True
    if tipo == "array":
        # Vacío: el tope de la lista nunca es un mínimo, y así ningún endpoint recorre nada.
        return []
    if tipo == "object":
        return {}
    return "x"


def cuerpo_valido(ref: str, comp: dict, sin_patron: list[str], hondo: int = 0) -> dict:
    nombre = ref.split("/")[-1]
    esquema = comp.get(nombre, {})
    obligatorias = set(esquema.get("required", []))
    props = esquema.get("properties", {})
    # Solo lo obligatorio: lo opcional ya trae valor por defecto y agregarlo solo suma
    # superficie para equivocarse.
    return {
        k: valor_valido(v, comp, sin_patron, hondo)
        for k, v in props.items()
        if k in obligatorias or not obligatorias
    }


# ---------------------------------------------------------------------------


def main() -> None:
    with urllib.request.urlopen(f"{BASE}/openapi.json") as r:
        esp = json.load(r)

    comp = esp["components"]["schemas"]
    sesiones = {rol: cliente(c) for rol, c in CUENTAS.items()}
    sesiones["nadie"] = cliente(None)

    problemas: list[str] = []
    sin_patron: list[str] = []
    revisados = 0

    for ruta, ops in sorted(esp["paths"].items()):
        dueno = next((v for k, v in DUENO.items() if ruta.startswith(k)), None)
        if dueno is None or ruta in PUBLICAS or ruta in COMPARTIDAS:
            continue

        for metodo, op in ops.items():
            if metodo not in ("get", "post", "put", "delete"):
                continue

            cuerpo = None
            cont = (op.get("requestBody") or {}).get("content", {})
            ref = cont.get("application/json", {}).get("schema", {}).get("$ref")
            if ref:
                cuerpo = cuerpo_valido(ref, comp, sin_patron)
            elif "multipart/form-data" in cont:
                # Una subida sin archivo es un 422 de validación, no un permiso: la cubre
                # `barrido_get.py`, que sí manda archivos.
                continue

            concreta = ruta
            while "{" in concreta:
                antes, resto = concreta.split("{", 1)
                _, despues = resto.split("}", 1)
                concreta = antes + ULID_FALSO + despues

            for rol, sesion in sesiones.items():
                if rol in dueno:
                    # El camino del dueño lo prueba `barrido_botones.py`, y con cuerpo válido
                    # aquí sería destructivo.
                    continue

                estado = pedir(sesion, concreta, metodo.upper(), cuerpo)
                revisados += 1

                if rol == "nadie":
                    if estado != 401:
                        problemas.append(f"sin sesión {estado} {metodo.upper()} {ruta}")
                elif estado not in (401, 403, 404):
                    problemas.append(f"{rol} recibe {estado} en {metodo.upper()} {ruta}")

    print(f"{revisados} comprobaciones, {len(problemas)} sospechas\n")
    for p in problemas:
        print("  " + p)

    if sin_patron:
        print("\n  Patrones sin valor de ejemplo (agrégalo a PATRONES o el cuerpo no valida):")
        for patron in sorted(set(sin_patron)):
            print(f"    {patron}")


if __name__ == "__main__":
    main()
