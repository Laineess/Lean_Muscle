"""Arranque de FastAPI.

Un solo proceso sirve los dos frentes: la app de la alumna y el panel de la coach. La
modularidad se logra por carpetas y limites de dominio, no por procesos separados — con un
equipo y un presupuesto cerrado, partir en servicios solo agrega despliegues y latencia.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

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
    api_registro,
    api_reservas,
    auth,
)
from app.rutas.plataforma import api as api_plataforma
from app.rutas.traduccion import respuesta_para
from app.servicios import correo, push
from app.servicios.registro_archivo import (
    configurar_logs_de_archivo,
    etiqueta_actor,
    ip_del_cliente,
    registrar_actividad,
    registrar_error,
)

if TYPE_CHECKING:
    from app.trabajos.emisor_avisos import Resultado

RAIZ = Path(__file__).resolve().parent

_registro = logging.getLogger("myfittplan")

#: Cada cuánto se revisan las colas fuera del VPS. Corto a propósito: quien prueba un alta
#: está mirando su bandeja, no esperando cinco minutos.
ESPERA_DE_LA_COLA = 15


def _colas_a_vaciar() -> list[tuple[str, Callable[[], Resultado]]]:
    """Los canales que en esta instancia salen de verdad, y solo esos.

    Vaciar una cola con el emisor de memoria marcaría los avisos como enviados sin que
    salga nada, y un aviso marcado ya no vuelve.
    """
    from app.trabajos.emisor_avisos import enviar_pendientes, enviar_push_pendientes

    colas: list[tuple[str, Callable[[], Resultado]]] = []
    if correo.manda_de_verdad():
        colas.append(("correo", enviar_pendientes))
    if push.manda_de_verdad():
        colas.append(("push", enviar_push_pendientes))
    return colas


async def _vaciar_las_colas(colas: list[tuple[str, Callable[[], Resultado]]]) -> None:
    """Hace en local lo que en el VPS hace `myfittplan-correo.timer`."""
    while True:
        for canal, vaciar in colas:
            try:
                r = await asyncio.to_thread(vaciar)
                if r.enviados or r.fallidos:
                    _registro.info(
                        "cola de %s: enviados=%d fallidos=%d agotados=%d",
                        canal,
                        r.enviados,
                        r.fallidos,
                        r.agotados,
                    )
            except Exception:  # pragma: no cover - una cola no puede tumbar el servidor
                _registro.exception("falló el vaciado de la cola de %s", canal)
        await asyncio.sleep(ESPERA_DE_LA_COLA)


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
    """Fuera del VPS no hay systemd, así que las colas de avisos no las vacía nadie.

    Todo salvo el código de registro se encola y lo manda un trabajo aparte —correo y push
    en dos colas—. En el servidor lo dispara un temporizador cada cinco minutos; en local
    ese temporizador no existe y la bienvenida, la clave temporal o el recibo se quedan
    esperando para siempre: parece roto el envío cuando lo que falta es quien vacíe la cola.
    """
    # Los logs de actividad y de errores viven en archivos .txt bajo /logs; se atan al
    # arrancar (antes de que cualquier petición pueda querer escribir).
    configurar_logs_de_archivo()

    incoherencia = correo.remitente_incoherente()
    if incoherencia:
        _registro.warning("%s", incoherencia)

    colas = [] if ajustes().es_produccion else _colas_a_vaciar()
    tarea = asyncio.create_task(_vaciar_las_colas(colas)) if colas else None
    try:
        yield
    finally:
        if tarea is not None:
            tarea.cancel()


app = FastAPI(
    title="MyFittPlan",
    version="0.1.0",
    description="Plataforma de coaching físico y nutricional",
    # En producción la documentación interactiva no se publica: describe la superficie
    # completa de una API que maneja datos de salud.
    docs_url=None if ajustes().es_produccion else "/docs",
    redoc_url=None,
    lifespan=ciclo_de_vida,
)


@app.exception_handler(ErrorDeDominio)
async def traducir_error_de_dominio(peticion: Request, exc: ErrorDeDominio) -> JSONResponse:
    """Único puente entre las reglas de negocio y HTTP.

    El dominio nunca construye una respuesta; devuelve un código y aquí se traduce.
    """
    registrar_error(
        "error de dominio en %s | ip=%s | %s | codigo=%s detalle=%r",
        peticion.url.path,
        ip_del_cliente(peticion),
        etiqueta_actor(peticion),
        exc.codigo.value,
        exc.detalle,
    )
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
    registrar_error(
        "consulta sin alcance de inquilino en %s | ip=%s | %s",
        peticion.url.path,
        ip_del_cliente(peticion),
        etiqueta_actor(peticion),
        exc_info=True,
    )
    estado, mensaje = respuesta_para(exc.codigo)
    return JSONResponse(status_code=estado, content={"mensaje": mensaje})


@app.exception_handler(Exception)
async def traducir_no_controlado(peticion: Request, exc: Exception) -> JSONResponse:
    """Cualquier excepción que se le escapó a una ruta es un 500 del servidor.

    FastAPI por sí solo responde «Internal Server Error» en texto plano; aquí se registra la
    traza y se devuelve el mismo JSON que el resto, sin filtrar el detalle ni la pila.
    """
    _registro.exception("error no controlado en %s", peticion.url.path)
    registrar_error(
        "error no controlado en %s | ip=%s | %s",
        peticion.url.path,
        ip_del_cliente(peticion),
        etiqueta_actor(peticion),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500, content={"mensaje": "Error interno. Vuelve a intentarlo en un momento."}
    )


@app.middleware("http")
async def bitacora_de_actividad(
    request: Request, siguiente: Callable[[Request], Awaitable[object]]
) -> object:
    """Una línea por petición en `logs/actividad.txt`: IP, método, ruta y quién la hizo.

    Corre detrás de `cuerpo_maximo` (que corta antes) y su propia excepción es tolerante:
    una falla de logging no puede tumbar una petición valida.
    """
    inicio = asyncio.get_running_loop().time()
    try:
        respuesta = await siguiente(request)
        estado = respuesta.status_code  # type: ignore[attr-defined]
    except Exception:
        estado = 500
        raise
    finally:
        duracion_ms = int((asyncio.get_running_loop().time() - inicio) * 1000)
        try:
            registrar_actividad(
                f"ip={ip_del_cliente(request)} "
                f"metodo={request.method} ruta={request.url.path} "
                f"{etiqueta_actor(request)} estado={estado} ms={duracion_ms}"
            )
        except Exception:  # pragma: no cover - el log no tumba la peticion
            _registro.exception("no se pudo anotar la actividad de %s", request.url.path)
    return respuesta


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


@app.middleware("http")
async def cuerpo_maximo(
    request: Request, siguiente: Callable[[Request], Awaitable[object]]
) -> object:
    """Rechaza cuerpos que excedan el tope antes de leerlos: un megapaquete no ocupa memoria.

    Un GET sin `Content-Length` (poco habitual) se deja pasar: la falta de longitud no es
    una novedad aquí, y responder 411 lo único que haría es romper clientes que no la mandan.
    """
    tope = ajustes().cuerpo_maximo_bytes
    contenido = request.headers.get("content-length")
    if contenido is not None and contenido != "" and int(contenido) > tope:
        return JSONResponse(status_code=413, content={"mensaje": "La petición pesa demasiado."})
    return await siguiente(request)


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
app.include_router(api_reservas.ruteador)
app.include_router(api_registro.ruteador)


@app.get("/salud", tags=["sistema"])
async def salud() -> dict[str, str]:
    """Sonda para el monitoreo. No toca la base a propósito: si la base cae, esta ruta
    debe seguir respondiendo para distinguir 'proceso muerto' de 'base caída'."""
    return {"estado": "ok", "entorno": ajustes().entorno}


ESTATICOS = RAIZ / "estaticos"
if ESTATICOS.exists():
    # En el VPS los estáticos los sirve nginx; este montaje es para desarrollo local.
    app.mount("/estaticos", StaticFiles(directory=ESTATICOS), name="estaticos")
