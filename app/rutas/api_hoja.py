"""La calculadora del expediente, con la forma de la hoja original.

El cálculo lo hace el servidor y no el navegador. La coach quiere garantía de que sale el
mismo número que su Excel, y esa garantía no puede depender de qué versión de la interfaz
tenga cargada: hay un solo lugar donde se calcula, `app/dominio/calculadora.py`, y una prueba
que lo compara contra el archivo celda por celda.

Peso y porcentaje de grasa son datos de salud, así que abrir la hoja queda registrado.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compartido.errores import ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.datos.modelos import ParametrosCiclo
from app.datos.repos import consultas as q
from app.dominio.calculadora import (
    BaseProteina,
    NivelActividad,
    RelacionGanancia,
    RepartoMacros,
    Sexo,
    calcular,
    proyectar_ganancia,
    proyectar_perdida,
)
from app.rutas.esquemas import BloqueDeHoja, CeldaDeHoja, HojaDeCalculo, TablaDeHoja
from app.rutas.sesion import Actor, datos, solo_coach
from app.servicios import bitacora, hoja

ruteador = APIRouter(prefix="/api/coach", tags=["hoja"])

#: Horizonte de la proyección de ganancia, celda H20.
SEMANAS_GANANCIA = 20


def _edad(nacimiento: date, hoy: date) -> int:
    cumplio = (hoy.month, hoy.day) >= (nacimiento.month, nacimiento.day)
    return hoy.year - nacimiento.year - (0 if cumplio else 1)


def _vacia(alumna: str, falta: str) -> HojaDeCalculo:
    return HojaDeCalculo(alumna=alumna, bloques=[], tablas=[], falta=falta)


@ruteador.get("/hoja/{alumna_ulid}", response_model=HojaDeCalculo)
def hoja_de_alumna(
    alumna_ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> HojaDeCalculo:
    alumna = q.alumna_por_ulid(s, alumna_ulid)
    if alumna is None:
        raise HTTPException(404, "No existe esa alumna")

    bitacora.registrar_acceso(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        alumna_id=alumna.id,
        recurso=bitacora.Recurso.EXPEDIENTE,
    )

    if alumna.estatura_cm is None:
        return _vacia(alumna.nombre, "Falta su estatura en la ficha.")

    chequeos = q.chequeos_de(s, alumna.id)
    ultimo = chequeos[-1] if chequeos else None
    if ultimo is None:
        return _vacia(alumna.nombre, "Todavía no hay ningún chequeo.")

    peso = q.peso_de_chequeo(s, [ultimo.id]).get(ultimo.id)
    if peso is None or ultimo.porcentaje_grasa is None:
        return _vacia(
            alumna.nombre,
            "Falta el peso o el porcentaje de grasa del último chequeo. El porcentaje se "
            "estima al validarlo.",
        )

    ciclo = q.ciclo_vigente(s, alumna.id)
    guardados = (
        s.scalars(select(ParametrosCiclo).where(ParametrosCiclo.ciclo_id == ciclo.id)).first()
        if ciclo
        else None
    )
    if guardados is None:
        return _vacia(alumna.nombre, "Todavía no se guardan los parámetros de su ciclo.")

    actividad = NivelActividad(guardados.nivel_actividad)
    base = BaseProteina(guardados.base_proteina)

    try:
        r = calcular(
            peso_kg=peso,
            porcentaje_grasa=ultimo.porcentaje_grasa,
            estatura_cm=alumna.estatura_cm,
            edad=_edad(alumna.fecha_nacimiento, ahora_utc().date()),
            sexo=Sexo.MASCULINO if alumna.sexo == "M" else Sexo.FEMENINO,
            actividad=actividad,
            porcentaje_ajuste=guardados.porcentaje_ajuste,
            reparto=RepartoMacros(
                carbohidrato=guardados.reparto_carbohidrato,
                proteina=guardados.reparto_proteina,
                grasa=guardados.reparto_grasa,
            ),
            base_proteina=base,
            dias_refeed=guardados.dias_refeed,
            porcentaje_dia_refeed=guardados.porcentaje_dia_refeed,
        )
    except ErrorDeDominio as causa:  # pragma: no cover - depende de datos capturados
        return _vacia(alumna.nombre, f"No se puede calcular: {causa.codigo.value}")

    perdida = None
    ganancia = None
    objetivo = alumna.porcentaje_grasa_objetivo
    if r.energia.es_deficit and objetivo is not None and objetivo < ultimo.porcentaje_grasa:
        perdida = proyectar_perdida(r.composicion, objetivo, r.energia)
    elif not r.energia.es_deficit:
        ganancia = proyectar_ganancia(
            r.composicion,
            r.energia,
            SEMANAS_GANANCIA,
            RelacionGanancia(guardados.relacion_ganancia),
        )

    armada = hoja.construir(
        alumna=alumna.nombre,
        edad=_edad(alumna.fecha_nacimiento, ahora_utc().date()),
        sexo="Masculino" if alumna.sexo == "M" else "Femenino",
        prescripcion=r,
        actividad=actividad,
        porcentaje_ajuste=guardados.porcentaje_ajuste,
        base_proteina=base,
        dia_bajo=abs(guardados.porcentaje_ajuste),
        dias_refeed=guardados.dias_refeed,
        perdida=perdida,
        ganancia=ganancia,
    )

    return HojaDeCalculo(
        alumna=armada.alumna,
        bloques=[
            BloqueDeHoja(
                titulo=b.titulo,
                rango=b.rango,
                celdas=[
                    CeldaDeHoja(
                        celda=c.celda,
                        rotulo=c.rotulo,
                        valor=c.valor,
                        unidad=c.unidad,
                        formula=c.formula,
                        capturado=c.capturado,
                    )
                    for c in b.celdas
                ],
            )
            for b in armada.bloques
        ],
        tablas=[
            TablaDeHoja(titulo=t.titulo, rango=t.rango, encabezados=t.encabezados, filas=t.filas)
            for t in armada.tablas
        ],
        falta=None,
    )
