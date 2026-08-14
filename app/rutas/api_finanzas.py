"""Finanzas de la coach: movimientos y tarifas.

Contabilidad de gestión, no fiscal. Sirve para que la coach sepa si su negocio gana dinero.

Los ingresos generados al validar un pago llegan marcados como automáticos y **no se editan
desde aquí**: corregirlos a mano separaría el ingreso del cobro que lo originó.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.datos.modelos import Alumna, Coach, MovimientoFinanciero, Tarifa
from app.datos.repos import consultas as q
from app.dominio import finanzas as f
from app.rutas.esquemas import (
    MovimientoNuevo,
    MovimientoPublico,
    PanelFinanciero,
    ResumenMes,
    TarifaNueva,
    TarifaPublica,
    TotalPorCategoria,
)
from app.rutas.sesion import Actor, datos, solo_coach

ruteador = APIRouter(prefix="/api/coach/finanzas", tags=["finanzas"])

#: Ventana por defecto del panel. Doce meses es lo que hace visible la estacionalidad del
#: negocio: enero y septiembre no se parecen a agosto.
MESES_POR_DEFECTO = 12


def _a_dominio(m: MovimientoFinanciero) -> f.Movimiento:
    return f.Movimiento(
        tipo=f.TipoMovimiento(m.tipo),
        categoria=m.categoria,
        monto=m.monto,
        fecha=m.fecha,
        concepto=m.concepto,
        alumna_id=m.alumna_id,
        automatico=m.automatico,
    )


def _publico(s: Session, m: MovimientoFinanciero) -> MovimientoPublico:
    nombre = None
    ulid = None
    if m.alumna_id is not None:
        alumna = s.get(Alumna, m.alumna_id)
        if alumna is not None:
            nombre = alumna.nombre
            ulid = alumna.ulid
    return MovimientoPublico(
        ulid=m.ulid,
        tipo=m.tipo,
        categoria=m.categoria,
        monto=m.monto,
        fecha=m.fecha,
        concepto=m.concepto,
        alumna_ulid=ulid,
        alumna_nombre=nombre,
        automatico=m.automatico,
        nota=m.nota,
    )


def _movimientos_entre(s: Session, desde: date, hasta: date) -> list[MovimientoFinanciero]:
    return list(
        s.scalars(
            select(MovimientoFinanciero)
            .where(MovimientoFinanciero.fecha >= desde, MovimientoFinanciero.fecha <= hasta)
            .order_by(MovimientoFinanciero.fecha.desc())
        ).all()
    )


@ruteador.get("", response_model=PanelFinanciero)
def panel(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
    meses: Annotated[int, Query(ge=1, le=36)] = MESES_POR_DEFECTO,
) -> PanelFinanciero:
    hasta = ahora_utc().date()
    desde = hasta - timedelta(days=meses * 31)

    filas = _movimientos_entre(s, desde, hasta)
    movimientos = [_a_dominio(m) for m in filas]

    resumen = f.resumir(movimientos)
    activas = sum(1 for a in q.cartera(s) if a.estado == "activa")

    coach = s.get(Coach, actor.coach_id)
    tarifa = f.Tarifa(
        codigo="base",
        nombre=coach.plan if coach else "base",
        precio=coach.precio_ciclo if coach else Decimal("0.00"),
    )

    return PanelFinanciero(
        ingresos=resumen.ingresos,
        gastos=resumen.gastos,
        utilidad=resumen.utilidad,
        margen=resumen.margen,
        ingreso_por_alumna=f.ingreso_por_alumna(resumen, activas),
        proyeccion_mensual=f.proyeccion_mensual(activas, tarifa),
        alumnas_activas=activas,
        por_mes=[
            ResumenMes(mes=mes, ingresos=r.ingresos, gastos=r.gastos, utilidad=r.utilidad)
            for mes, r in f.por_mes(movimientos).items()
        ],
        ingresos_por_categoria=[
            TotalPorCategoria(categoria=c, monto=v)
            for c, v in f.por_categoria(movimientos, f.TipoMovimiento.INGRESO).items()
        ],
        gastos_por_categoria=[
            TotalPorCategoria(categoria=c, monto=v)
            for c, v in f.por_categoria(movimientos, f.TipoMovimiento.GASTO).items()
        ],
        movimientos=[_publico(s, m) for m in filas],
    )


@ruteador.post("/movimientos", response_model=MovimientoPublico, status_code=201)
def crear_movimiento(
    cuerpo: MovimientoNuevo,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> MovimientoPublico:
    alumna_id = None
    if cuerpo.alumna_ulid:
        alumna = q.alumna_por_ulid(s, cuerpo.alumna_ulid)
        if alumna is None:
            raise HTTPException(404, "No existe esa alumna")
        alumna_id = alumna.id

    f.validar(
        f.Movimiento(
            tipo=f.TipoMovimiento(cuerpo.tipo),
            categoria=cuerpo.categoria,
            monto=cuerpo.monto,
            fecha=cuerpo.fecha,
            concepto=cuerpo.concepto,
            alumna_id=alumna_id,
        )
    )

    movimiento = MovimientoFinanciero(
        coach_id=actor.coach_id,
        tipo=cuerpo.tipo,
        categoria=cuerpo.categoria,
        monto=cuerpo.monto,
        fecha=cuerpo.fecha,
        concepto=cuerpo.concepto.strip(),
        alumna_id=alumna_id,
        nota=cuerpo.nota,
        automatico=False,
    )
    s.add(movimiento)
    s.flush()
    return _publico(s, movimiento)


def _buscar(s: Session, ulid: str) -> MovimientoFinanciero:
    movimiento = s.scalars(
        select(MovimientoFinanciero).where(MovimientoFinanciero.ulid == ulid)
    ).first()
    if movimiento is None:
        raise HTTPException(404, "No existe ese movimiento")
    return movimiento


@ruteador.put("/movimientos/{ulid}", response_model=MovimientoPublico)
def editar_movimiento(
    ulid: str,
    cuerpo: MovimientoNuevo,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> MovimientoPublico:
    movimiento = _buscar(s, ulid)
    f.exigir_editable(_a_dominio(movimiento))

    f.validar(
        f.Movimiento(
            tipo=f.TipoMovimiento(cuerpo.tipo),
            categoria=cuerpo.categoria,
            monto=cuerpo.monto,
            fecha=cuerpo.fecha,
            concepto=cuerpo.concepto,
        )
    )

    movimiento.tipo = cuerpo.tipo
    movimiento.categoria = cuerpo.categoria
    movimiento.monto = cuerpo.monto
    movimiento.fecha = cuerpo.fecha
    movimiento.concepto = cuerpo.concepto.strip()
    movimiento.nota = cuerpo.nota
    return _publico(s, movimiento)


@ruteador.delete("/movimientos/{ulid}", status_code=204)
def eliminar_movimiento(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    movimiento = _buscar(s, ulid)
    f.exigir_editable(_a_dominio(movimiento))
    s.delete(movimiento)


# ---------------------------------------------------------------------------
# Tarifas
# ---------------------------------------------------------------------------


@ruteador.get("/tarifas", response_model=list[TarifaPublica])
def tarifas(
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> list[TarifaPublica]:
    filas = s.scalars(select(Tarifa).order_by(Tarifa.precio)).all()
    return [TarifaPublica.model_validate(t) for t in filas]


@ruteador.post("/tarifas", response_model=TarifaPublica, status_code=201)
def crear_tarifa(
    cuerpo: TarifaNueva,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> TarifaPublica:
    f.validar_tarifa(
        f.Tarifa(
            codigo=cuerpo.codigo,
            nombre=cuerpo.nombre,
            precio=cuerpo.precio,
            dias=cuerpo.dias,
            activa=cuerpo.activa,
        )
    )

    if s.scalars(select(Tarifa).where(Tarifa.codigo == cuerpo.codigo)).first() is not None:
        raise ErrorDeDominio(Codigo.CATEGORIA_INVALIDA, categoria=cuerpo.codigo, tipo="tarifa")

    tarifa = Tarifa(
        coach_id=actor.coach_id,
        codigo=cuerpo.codigo.strip().upper(),
        nombre=cuerpo.nombre.strip(),
        descripcion=cuerpo.descripcion,
        precio=cuerpo.precio,
        dias=cuerpo.dias,
        activa=cuerpo.activa,
    )
    s.add(tarifa)
    s.flush()
    return TarifaPublica.model_validate(tarifa)


@ruteador.put("/tarifas/{ulid}", response_model=TarifaPublica)
def editar_tarifa(
    ulid: str,
    cuerpo: TarifaNueva,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> TarifaPublica:
    tarifa = s.scalars(select(Tarifa).where(Tarifa.ulid == ulid)).first()
    if tarifa is None:
        raise HTTPException(404, "No existe esa tarifa")

    f.validar_tarifa(
        f.Tarifa(
            codigo=cuerpo.codigo,
            nombre=cuerpo.nombre,
            precio=cuerpo.precio,
            dias=cuerpo.dias,
            activa=cuerpo.activa,
        )
    )

    # El precio no se propaga a los ciclos abiertos: cada ciclo guarda el suyo, para que
    # subir la tarifa no le cambie el cobro a quien ya empezó.
    tarifa.nombre = cuerpo.nombre.strip()
    tarifa.descripcion = cuerpo.descripcion
    tarifa.precio = cuerpo.precio
    tarifa.dias = cuerpo.dias
    tarifa.activa = cuerpo.activa
    return TarifaPublica.model_validate(tarifa)


@ruteador.delete("/tarifas/{ulid}", status_code=204)
def eliminar_tarifa(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_coach)],
    s: Annotated[Session, Depends(datos)],
) -> None:
    """Se desactiva en lugar de borrarse.

    Borrar una tarifa dejaría sin referencia a los ciclos históricos que la usaron, y con
    ella se va la explicación de por qué una alumna pagó lo que pagó.
    """
    tarifa = s.scalars(select(Tarifa).where(Tarifa.ulid == ulid)).first()
    if tarifa is None:
        raise HTTPException(404, "No existe esa tarifa")
    tarifa.activa = False
