"""¿Alguien llega a donde no le toca? Cada endpoint contra cada rol y sin sesión."""

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

#: Rutas que a propósito no exigen sesión.
PUBLICAS = {"/api/documentos/{clave}", "/api/legal/{clave}", "/salud", "/api/auth/entrar"}

#: Prefijo -> quién debe poder entrar.
DUENO = {"/api/coach/": {"coach"}, "/api/mi/": {"alumna"}, "/api/plataforma/": {"admin"}}


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
    except Exception:  # noqa: BLE001
        return 0


def main() -> None:
    with urllib.request.urlopen(f"{BASE}/openapi.json") as r:
        esp = json.load(r)

    sesiones = {rol: cliente(c) for rol, c in CUENTAS.items()}
    sesiones["nadie"] = cliente(None)

    problemas: list[str] = []
    revisados = 0

    for ruta, ops in sorted(esp["paths"].items()):
        dueno = next((v for k, v in DUENO.items() if ruta.startswith(k)), None)
        if dueno is None or ruta in PUBLICAS:
            continue
        for metodo in ops:
            if metodo not in ("get", "post", "put", "delete"):
                continue
            concreta = ruta
            while "{" in concreta:
                antes, resto = concreta.split("{", 1)
                _, despues = resto.split("}", 1)
                concreta = antes + "01" + "A" * 24 + despues

            for rol, sesion in sesiones.items():
                estado = pedir(sesion, concreta, metodo.upper(), {} if metodo in ("post", "put") else None)
                revisados += 1
                permitido = rol in dueno
                if rol == "nadie":
                    if estado != 401:
                        problemas.append(f"sin sesión {estado} {metodo.upper()} {ruta}")
                elif not permitido and estado not in (401, 403, 404):
                    problemas.append(f"{rol} recibe {estado} en {metodo.upper()} {ruta}")

    print(f"{revisados} comprobaciones, {len(problemas)} sospechas\n")
    for p in problemas:
        print("  " + p)


if __name__ == "__main__":
    main()
