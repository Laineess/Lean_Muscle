"""Las pruebas nunca tocan la base de desarrollo.

Las de aislamiento hacen `drop_all` sobre el motor configurado. Con la configuración local
eso es la base con la que se está trabajando: correr la suite la dejaba vacía y había que
volver a migrar y sembrar. Aquí se redirige a `<base>_pruebas` antes de que nada lea la
configuración, porque `ajustes()` queda cacheada en la primera llamada.

En CI el entorno ya es `pruebas` contra una base desechable, así que no se toca nada.
"""

from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit

SUFIJO = "_pruebas"


def _url_de_pruebas(url: str) -> str:
    partes = urlsplit(url)
    nombre = partes.path.lstrip("/")
    if nombre.endswith(SUFIJO):
        return url
    return urlunsplit(partes._replace(path=f"/{nombre}{SUFIJO}"))


def _sin_base(url: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path="/"))


if os.environ.get("LM_ENTORNO") != "pruebas":
    from app.config import Ajustes

    os.environ["LM_BD_URL"] = _url_de_pruebas(Ajustes().bd_url)
    os.environ["LM_ENTORNO"] = "pruebas"

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from app.config import ajustes  # noqa: E402
from app.datos.base import Base  # noqa: E402

_URL = ajustes().bd_url
_NOMBRE = urlsplit(_URL).path.lstrip("/")

if ajustes().entorno != "pruebas":  # pragma: no cover - defensivo
    raise SystemExit(f"La suite borra tablas y el entorno es {ajustes().entorno}. Abortado.")


def pytest_configure(config: object) -> None:
    """Prepara la base de pruebas. Sin MySQL las que lo piden se saltan solas."""
    del config
    try:
        with create_engine(_sin_base(_URL)).begin() as c:
            c.execute(
                text(
                    f"create database if not exists `{_NOMBRE}` "
                    "character set utf8mb4 collate utf8mb4_0900_ai_ci"
                )
            )
    except OperationalError:
        # La cuenta de la aplicación no puede crear bases, y así debe ser. Si tampoco
        # existe, las pruebas con MySQL se saltan y el aviso dice cómo crearla.
        pass

    try:
        from app.datos.alcance import motor

        Base.metadata.create_all(motor())
    except OperationalError as causa:  # pragma: no cover - depende del entorno
        print(
            f"\nNo se pudo abrir `{_NOMBRE}` ({causa.orig}).\n"
            "Las pruebas con MySQL se van a saltar. Para crearla:\n"
            "    .\\desarrollo.ps1\n"
        )
