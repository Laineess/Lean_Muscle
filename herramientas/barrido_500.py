"""Le mete basura a cada endpoint con cuerpo JSON y reporta los que devuelven 500.

Construye los cuerpos desde el propio OpenAPI, así que cubre lo que haya, no lo que yo
recuerde. Un 4xx es correcto —el servidor rechaza y dice por qué—; un 500 es un fallo.
"""

from __future__ import annotations

import json
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

LARGO = "Ā" * 5000
ENORME = 10**12
NEGATIVO = -(10**12)


def cliente(correo: str):
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    pedir(op, "/api/auth/login", "POST",
          {"correo": correo, "contrasena": "Demo1234!", "recordarme": False})
    return op


def pedir(op, ruta: str, metodo: str, cuerpo: Any = None) -> tuple[int, str]:
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    pet = urllib.request.Request(BASE + ruta, data=datos, method=metodo)
    if datos:
        pet.add_header("Content-Type", "application/json")
    try:
        with op.open(pet) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as causa:
        return 0, f"{type(causa).__name__}: {causa}"


def valor(esquema: dict, comp: dict, extremo: str) -> Any:
    """Un valor absurdo pero del tipo correcto, para que llegue hasta la base."""
    if "$ref" in esquema:
        return cuerpo_de(esquema["$ref"], comp, extremo)
    for clave in ("anyOf", "oneOf", "allOf"):
        if clave in esquema:
            opciones = [e for e in esquema[clave] if e.get("type") != "null"]
            if opciones:
                return valor(opciones[0], comp, extremo)
            return None
    tipo = esquema.get("type")
    if tipo == "string":
        formato = esquema.get("format")
        if formato == "date":
            return "9999-12-31" if extremo == "alto" else "0001-01-01"
        if formato == "date-time":
            return "9999-12-31T23:59:59Z"
        return LARGO if extremo == "alto" else ""
    if tipo == "integer":
        return ENORME if extremo == "alto" else NEGATIVO
    if tipo == "number":
        return ENORME if extremo == "alto" else NEGATIVO
    if tipo == "boolean":
        return True
    if tipo == "array":
        item = esquema.get("items", {})
        return [valor(item, comp, extremo)] * (60 if extremo == "alto" else 0)
    if tipo == "object":
        return {LARGO[:100]: LARGO[:100]} if extremo == "alto" else {}
    return LARGO if extremo == "alto" else None


def cuerpo_de(ref: str, comp: dict, extremo: str) -> dict:
    nombre = ref.split("/")[-1]
    props = comp.get(nombre, {}).get("properties", {})
    return {k: valor(v, comp, extremo) for k, v in props.items()}


def main() -> None:
    with urllib.request.urlopen(f"{BASE}/openapi.json") as r:
        esp = json.load(r)

    comp = esp["components"]["schemas"]
    sesiones = {rol: cliente(correo) for rol, correo in CUENTAS.items()}

    # ULIDs reales, para llegar más allá del 404.
    _, crudo = pedir(sesiones["coach"], "/api/coach/alumnas", "GET")
    alumnas = json.loads(crudo)
    _, crudo_c = pedir(sesiones["admin"], "/api/plataforma/coaches", "GET")
    coaches = json.loads(crudo_c)
    reales = {
        "ulid": alumnas[0]["ulid"] if alumnas else "01" + "A" * 24,
        "alumna_ulid": alumnas[0]["ulid"] if alumnas else "01" + "A" * 24,
    }
    de_coach = {"ulid": coaches[0]["ulid"] if coaches else "01" + "A" * 24}

    fallos = []
    probados = 0

    for ruta, ops in sorted(esp["paths"].items()):
        for metodo, op in ops.items():
            if metodo not in ("post", "put"):
                continue
            cont = (op.get("requestBody") or {}).get("content", {})
            if "application/json" not in cont:
                continue
            ref = cont["application/json"]["schema"].get("$ref")
            if not ref:
                continue
            if "/auth/" in ruta:
                continue

            concreta = ruta
            tabla = de_coach if "/plataforma/coaches" in ruta else reales
            for nombre, v in tabla.items():
                concreta = concreta.replace("{" + nombre + "}", v)
            if "{" in concreta:
                concreta = concreta.split("{")[0] + "01" + "A" * 24

            for extremo in ("alto", "bajo"):
                payload = cuerpo_de(ref, comp, extremo)
                for rol, op_sesion in sesiones.items():
                    estado, texto = pedir(op_sesion, concreta, metodo.upper(), payload)
                    probados += 1
                    if estado >= 500 or estado == 0:
                        fallos.append((metodo.upper(), concreta, rol, extremo, estado, texto))
                        break

    print(f"{probados} peticiones, {len(fallos)} con error del servidor\n")
    for m, r, rol, extremo, estado, texto in fallos:
        print(f"  {estado} {m} {r}  [{rol}, {extremo}]")
        print(f"      {texto[:180]}")


if __name__ == "__main__":
    main()
