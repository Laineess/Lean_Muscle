"""Configuracion leida de variables de entorno (config.env en local, /etc/leanmuscle/config.env en el VPS)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LM_",
        # Se aceptan los dos nombres: `.env` es la convención y es lo que la gente escribe
        # por costumbre. El último de la lista gana, así que el archivo del VPS pisa a los
        # locales si por accidente quedara alguno en el servidor.
        env_file=(".env", "config.env", "/etc/myfittplan/config.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    entorno: Literal["local", "pruebas", "produccion"] = "local"

    bd_url: str = "mysql+pymysql://root@127.0.0.1:3306/leanmuscle?charset=utf8mb4"

    secreto_sesion: str = "inseguro-solo-para-local"
    sesion_horas: int = 720

    ruta_datos: Path = Path("./datos")
    nginx_prefijo_interno: str = "/protegido"

    zona_horaria: str = "America/Mexico_City"

    #: Manda correo de verdad aunque el entorno no sea produccion.
    #:
    #: Sin esto, en local el emisor solo guarda en memoria —un `pytest` que dispare correos
    #: a direcciones reales es un accidente esperando a ocurrir— y no habia forma de probar
    #: el envio sin poner `entorno=produccion`, que ademas marca la cookie de sesion como
    #: `secure` y deja de funcionar sobre http://localhost.
    correo_real: bool = False

    smtp_host: str = ""
    smtp_puerto: int = 587
    smtp_usuario: str = ""
    smtp_contrasena_app: str = ""
    smtp_remitente: str = ""

    vapid_publica: str = ""
    vapid_privada: str = ""
    vapid_contacto: str = ""

    conservar_foto_linea_base: bool = False
    retencion_fotos_meses: int = 4

    #: Con la que nace toda cuenta. Se configura para poder rotarla sin desplegar.
    contrasena_inicial: str = "Myfittplan2026"

    @property
    def es_produccion(self) -> bool:
        return self.entorno == "produccion"


@lru_cache
def ajustes() -> Ajustes:
    return Ajustes()
