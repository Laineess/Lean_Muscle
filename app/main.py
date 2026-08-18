"""Arranque de FastAPI.

Un solo proceso sirve los dos frentes: la app de la alumna y el panel de la coach. La
modularidad se logra por carpetas y limites de dominio, no por procesos separados — con un
equipo y un presupuesto cerrado, partir en servicios solo agrega despliegues y latencia.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.compartido.errores import ErrorDeDominio, SinAlcanceDeInquilino
from app.config import ajustes
from app.rutas import (
    api_alumna,
    api_anuncios,
    api_arco,
    api_biblioteca,
    api_chequeo,
    api_coach,
    api_cobros,
    api_comprobantes,
    api_cuestionario,
    api_documentos,
    api_finanzas,
    api_fotos_comida,
    api_hoja,
    api_legales,
    api_medios,
    api_presentacion,
    auth,
)
from app.rutas.plataforma import api as api_plataforma
from app.rutas.traduccion import respuesta_para

RAIZ = Path(__file__).resolve().parent

_registro = logging.getLogger("myfittplan")

app = FastAPI(
    title="MyFittPlan",
    version="0.1.0",
    description="Plataforma de coaching físico y nutricional",
    # En producción la documentación interactiva no se publica: describe la superficie
    # completa de una API que maneja datos de salud.
    docs_url=None if ajustes().es_produccion else "/docs",
    redoc_url=None,
)


@app.exception_handler(ErrorDeDominio)
async def traducir_error_de_dominio(_: Request, exc: ErrorDeDominio) -> JSONResponse:
    """Único puente entre las reglas de negocio y HTTP.

    El dominio nunca construye una respuesta; devuelve un código y aquí se traduce.
    """
    estado, mensaje = respuesta_para(exc.codigo)
    return JSONResponse(
        status_code=estado,
        content={"codigo": exc.codigo.value, "mensaje": mensaje, "detalle": exc.detalle},
    )


@app.exception_handler(SinAlcanceDeInquilino)
async def traducir_sin_alcance(peticion: Request, exc: SinAlcanceDeInquilino) -> JSONResponse:
    """Una consulta sin inquilino es un error del programador, no de la usuaria.

    Se responde 500 sin detalle y **se registra completo con su traza**: preferimos caer
    ruidoso antes que devolver la fila de otra coach, pero caer en silencio no ayuda a nadie.
    Sin la traza, este error se ve en el navegador como «Error interno» y en el servidor como
    nada, que es la peor combinación posible para encontrarlo.
    """
    _registro.exception("consulta sin alcance de inquilino en %s", peticion.url.path)
    estado, mensaje = respuesta_para(exc.codigo)
    return JSONResponse(status_code=estado, content={"mensaje": mensaje})


@app.middleware("http")
async def cabeceras_de_seguridad(
    request: Request, siguiente: Callable[[Request], Awaitable[object]]
) -> object:
    respuesta = await siguiente(request)
    cabeceras = respuesta.headers  # type: ignore[attr-defined]
    cabeceras["X-Content-Type-Options"] = "nosniff"
    cabeceras["X-Frame-Options"] = "DENY"
    cabeceras["Referrer-Policy"] = "same-origin"
    if ajustes().es_produccion:
        cabeceras["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return respuesta


app.include_router(auth.ruteador)
app.include_router(api_alumna.ruteador)
app.include_router(api_chequeo.ruteador)
app.include_router(api_coach.ruteador)
app.include_router(api_cobros.ruteador)
app.include_router(api_comprobantes.ruteador)
app.include_router(api_biblioteca.ruteador)
app.include_router(api_finanzas.ruteador)
app.include_router(api_documentos.ruteador)
app.include_router(api_legales.ruteador)
app.include_router(api_medios.ruteador)
app.include_router(api_plataforma.ruteador)
app.include_router(api_presentacion.ruteador)
app.include_router(api_cuestionario.ruteador)
app.include_router(api_hoja.ruteador)
app.include_router(api_fotos_comida.ruteador)
app.include_router(api_anuncios.ruteador)
app.include_router(api_arco.ruteador)


@app.get("/salud", tags=["sistema"])
async def salud() -> dict[str, str]:
    """Sonda para el monitoreo. No toca la base a propósito: si la base cae, esta ruta
    debe seguir respondiendo para distinguir 'proceso muerto' de 'base caída'."""
    return {"estado": "ok", "entorno": ajustes().entorno}


ESTATICOS = RAIZ / "estaticos"
if ESTATICOS.exists():
    # En el VPS los estáticos los sirve nginx; este montaje es para desarrollo local.
    app.mount("/estaticos", StaticFiles(directory=ESTATICOS), name="estaticos")
