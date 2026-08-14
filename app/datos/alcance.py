"""Aislamiento entre coaches.

**MySQL no tiene Row Level Security.** PostgreSQL deja declarar politicas que la base
aplica aunque el programador olvide el `WHERE`; MySQL no ofrece ese seguro. Como el
aislamiento entre coaches es la base legal del modelo — una fuga entre inquilinos es una
infraccion sancionable directamente a la coach — hay que reponer esa red con ingenieria
explicita.

Este modulo es la capa 2 de cinco (Propuesta Backend, seccion 4):

1. Sesion: el `coach_id` sale del token, nunca del cliente.
2. **Sesion de base con alcance obligatorio (este archivo).**
3. Prueba automatizada de fuga en CI (`pruebas/aislamiento`).
4. Llaves de almacenamiento por inquilino.
5. Vistas `v_tabla` en MySQL, con el usuario de la aplicacion sin permiso sobre las
   tablas base.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import ORMExecuteState, Session, sessionmaker, with_loader_criteria

from app.compartido.errores import SinAlcanceDeInquilino
from app.config import ajustes
from app.datos.base import BaseMultiInquilino

#: Alcance de la peticion en curso. Es un ContextVar y no una global precisamente para que
#: dos peticiones concurrentes no se pisen el inquilino.
alcance_actual: ContextVar[int | None] = ContextVar("alcance_actual", default=None)

#: Marca de ejecucion que exime del filtro. Solo la usan migraciones, trabajos programados
#: y el panel de plataforma, siempre a traves de `app/datos/sin_alcance.py`.
SIN_ALCANCE = "sin_alcance"


def crear_motor(url: str | None = None) -> Engine:
    return create_engine(
        url or ajustes().bd_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
    )


_motor: Engine | None = None


def motor() -> Engine:
    global _motor
    if _motor is None:
        _motor = crear_motor()
    return _motor


FabricaDeSesion = sessionmaker(class_=Session, expire_on_commit=False, future=True)


@event.listens_for(Session, "do_orm_execute")
def _aplicar_alcance(estado: ORMExecuteState) -> None:
    """Inyecta `WHERE coach_id = :actual` en toda lectura de una entidad multi-inquilino.

    Va sobre `with_loader_criteria` y no sobre un `WHERE` a mano porque asi el filtro
    tambien alcanza los JOIN y la carga diferida de relaciones — que es justo donde se
    escapan los datos cuando el filtro se escribe endpoint por endpoint.
    """
    if not estado.is_select or estado.is_column_load or estado.is_relationship_load:
        # Las cargas de columna/relacion heredan el criterio del SELECT que las origino.
        if not estado.is_select:
            return

    if estado.execution_options.get(SIN_ALCANCE):
        return

    coach_id = alcance_actual.get()
    if coach_id is None:
        # Falla ruidoso, nunca silencioso: preferimos un 500 a devolver la fila de otra coach.
        raise SinAlcanceDeInquilino(
            "Se intento leer sin alcance de inquilino. Usa sesion_con_alcance() o, si de "
            "verdad corresponde, app.datos.sin_alcance."
        )

    estado.statement = estado.statement.options(
        with_loader_criteria(
            BaseMultiInquilino,
            lambda cls: cls.coach_id == alcance_actual.get(),
            include_aliases=True,
        )
    )


@contextmanager
def sesion_con_alcance(coach_id: int) -> Iterator[Session]:
    """Abre una sesion atada a un inquilino. Es la unica puerta del codigo de dominio.

    Fija tambien `@app_coach_id` en la conexion, que es lo que leen las vistas `v_tabla`
    de la capa 5. Esa variable vive en la conexion y el pool las reutiliza, asi que se
    limpia siempre al devolverla — hacerlo a mano en cada endpoint es exactamente el
    olvido que este envoltorio existe para evitar.
    """
    if coach_id is None:  # pragma: no cover - defensivo
        raise SinAlcanceDeInquilino("coach_id no puede ser None")

    ficha: Token[int | None] = alcance_actual.set(coach_id)
    sesion = FabricaDeSesion(bind=motor())
    try:
        sesion.execute(text("SET @app_coach_id = :cid"), {"cid": coach_id})
        yield sesion
        sesion.commit()
    except Exception:
        sesion.rollback()
        raise
    finally:
        try:
            sesion.execute(text("SET @app_coach_id = NULL"))
            sesion.commit()
        except Exception:  # pragma: no cover - la conexion ya murio
            pass
        sesion.close()
        alcance_actual.reset(ficha)


def alcance_vigente() -> int:
    """`coach_id` de la peticion en curso, o falla. Para repos que necesitan escribirlo."""
    coach_id = alcance_actual.get()
    if coach_id is None:
        raise SinAlcanceDeInquilino("No hay alcance de inquilino en este contexto")
    return coach_id


def marcar_nuevo(entidad: Any) -> Any:
    """Estampa el inquilino en una entidad nueva. El `coach_id` jamas viene del cliente."""
    if isinstance(entidad, BaseMultiInquilino):
        entidad.coach_id = alcance_vigente()
    return entidad
