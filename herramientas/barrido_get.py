"""Lecturas y subidas: parámetros hostiles y archivos que no son imágenes."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from http.cookiejar import CookieJar
from typing import Any

BASE = "http://127.0.0.1:8000"
CUENTAS = {
    "coach": "mariana@leanmuscle.mx",
    "alumna": "andrea.saenz@ejemplo.mx",
    "admin": "admin@myfittplan.com",
}

HOSTILES = [
    "",
    "0",
    "-1",
    "999999999999999",
    "-999999999999999",
    "a" * 3000,
    "'; drop table alumna; --",
    "../../etc/passwd",
    "%00",
    "NaN",
    "1e400",
    "01" + "A" * 24,
]


def cliente(correo: str):
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    pedir(op, "/api/auth/login", "POST", {"correo": correo, "contrasena": "Demo1234!"})
    return op


def pedir(op, ruta: str, metodo: str = "GET", cuerpo: Any = None) -> tuple[int, str]:
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    pet = urllib.request.Request(BASE + ruta, data=datos, method=metodo)
    if datos:
        pet.add_header("Content-Type", "application/json")
    try:
        with op.open(pet) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except Exception as causa:
        return 0, f"{type(causa).__name__}: {causa}"


def subir(op, ruta: str, contenido: bytes, nombre: str, metodo: str = "PUT") -> tuple[int, str]:
    borde = uuid.uuid4().hex
    cuerpo = (
        (
            f"--{borde}\r\n"
            f'Content-Disposition: form-data; name="archivo"; filename="{nombre}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        + contenido
        + f"\r\n--{borde}--\r\n".encode()
    )
    pet = urllib.request.Request(BASE + ruta, data=cuerpo, method=metodo)
    pet.add_header("Content-Type", f"multipart/form-data; boundary={borde}")
    try:
        with op.open(pet) as r:
            return r.status, r.read().decode(errors="replace")[:120]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:200]
    except Exception as causa:
        return 0, f"{type(causa).__name__}: {causa}"


def main() -> None:
    with urllib.request.urlopen(f"{BASE}/openapi.json") as r:
        esp = json.load(r)
    sesiones = {rol: cliente(c) for rol, c in CUENTAS.items()}

    fallos: list[tuple[str, str, str, int, str]] = []
    probados = 0

    # --- Lecturas: cada parámetro de ruta y de consulta, con basura ---
    for ruta, ops in sorted(esp["paths"].items()):
        op_def = ops.get("get")
        if not op_def or "/auth/" in ruta:
            continue
        params = [p for p in op_def.get("parameters", []) if p["in"] in ("path", "query")]
        nombres = [p["name"] for p in params] or ([] if "{" not in ruta else ["x"])

        for hostil in HOSTILES:
            concreta = ruta
            consulta = []
            for p in params:
                if p["in"] == "path":
                    concreta = concreta.replace(
                        "{" + p["name"] + "}", urllib.parse.quote(hostil, safe="")
                    )
                else:
                    consulta.append(f"{p['name']}={urllib.parse.quote(hostil, safe='')}")
            if "{" in concreta:
                continue
            destino = concreta + ("?" + "&".join(consulta) if consulta else "")
            if not nombres and hostil != HOSTILES[0]:
                continue
            for rol, sesion in sesiones.items():
                estado, texto = pedir(sesion, destino)
                probados += 1
                if estado >= 500 or estado == 0:
                    fallos.append(("GET", destino, rol, estado, texto[:160]))
                    break

    # --- Subidas: lo que no es una imagen ---
    subidas = [
        ("/api/coach/logo", "coach", "PUT"),
        ("/api/coach/presentacion/foto", "coach", "PUT"),
        ("/api/mi/fotos-comida", "alumna", "POST"),
    ]
    basura = [
        (b"", "vacio.png"),
        (b"no soy una imagen", "texto.png"),
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 50, "png-truncado.png"),
        (b"%PDF-1.4 falso", "documento.pdf"),
        (b"\xff" * 200_000, "ruido.jpg"),
    ]
    for ruta, rol, metodo in subidas:
        for contenido, nombre in basura:
            estado, texto = subir(sesiones[rol], ruta, contenido, nombre, metodo)
            probados += 1
            if estado >= 500 or estado == 0:
                fallos.append((metodo, ruta + f" [{nombre}]", rol, estado, texto))

    print(f"{probados} peticiones, {len(fallos)} con error del servidor\n")
    for m, r, rol, estado, texto in fallos:
        print(f"  {estado} {m} {r}  [{rol}]")
        print(f"      {texto[:150]}")


if __name__ == "__main__":
    import urllib.parse

    main()
