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
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import ORMExecuteState, Session, sessionmaker, with_loader_criteria

from app.compartido.errores import SinAlcanceDeInquilino
from app.config import ajustes
from app.datos.base import BaseMultiInquilino

#: Exime del filtro **una sentencia suelta**. Solo para las consultas que por definicion
#: preceden al inquilino: buscar el usuario al entrar, comprobar que un correo no este
#: repetido en toda la plataforma.
SIN_ALCANCE = "sin_alcance"

#: Claves que cada sesion lleva en su `info`. El alcance vive en la sesion y no en un
#: ContextVar: FastAPI abre las dependencias generadoras en un hilo distinto del endpoint,
#: asi que lo fijado al abrir la sesion no se veria al usarla.
ALCANCE = "alcance_de_inquilino"
EXENTA = "sesion_sin_alcance"


def crear_motor(url: str | None = None) -> Engine:
    maquina = create_engine(
        url or ajustes().bd_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
    )

    @event.listens_for(maquina, "connect")
    def _zona_utc(conexion: Any, _: Any) -> None:
        """UTC también para los `DEFAULT now(3)` que calcula el servidor."""
        with conexion.cursor() as cursor:
            cursor.execute("SET time_zone = '+00:00'")

    return maquina


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

    if estado.execution_options.get(SIN_ALCANCE) or estado.session.info.get(EXENTA):
        return

    coach_id = estado.session.info.get(ALCANCE)
    if coach_id is None:
        # Falla ruidoso, nunca silencioso: preferimos un 500 a devolver la fila de otra coach.
        raise SinAlcanceDeInquilino(
            "Se intento leer sin alcance de inquilino. Usa sesion_con_alcance() o, si de "
            "verdad corresponde, app.datos.sin_alcance."
        )

    # `coach_id` entra como variable de cierre y no se lee dentro de la lambda:
    # `with_loader_criteria` la cachea por objeto de codigo y extrae los valores enlazados
    # sin volver a ejecutarla. Llamar a una funcion dentro lanza `InvalidRequestError`.
    estado.statement = estado.statement.options(
        with_loader_criteria(
            BaseMultiInquilino,
            lambda cls: cls.coach_id == coach_id,
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

    sesion = FabricaDeSesion(bind=motor())
    sesion.info[ALCANCE] = coach_id
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


def alcance_de(sesion: Session) -> int:
    """`coach_id` de esa sesion, o falla. Para repos que necesitan escribirlo."""
    coach_id = sesion.info.get(ALCANCE)
    if coach_id is None:
        raise SinAlcanceDeInquilino("Esta sesion no tiene alcance de inquilino")
    return int(coach_id)


def marcar_nuevo(sesion: Session, entidad: Any) -> Any:
    """Estampa el inquilino en una entidad nueva. El `coach_id` jamas viene del cliente."""
    if isinstance(entidad, BaseMultiInquilino):
        entidad.coach_id = alcance_de(sesion)
    return entidad
