"""Aislamiento entre coaches, capa 2 de cinco (Propuesta Backend, seccion 4).

MySQL no tiene Row Level Security, y una fuga entre inquilinos es una infraccion
sancionable a la coach: la red hay que reponerla con ingenieria explicita.

Las otras cuatro: el `coach_id` sale del token; prueba de fuga en `pruebas/aislamiento`;
llaves de almacenamiento por inquilino; vistas `v_tabla` en MySQL.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import ORMExecuteState, Session, sessionmaker, with_loader_criteria

from app.compartido.errores import BorradoDeEsquemaProhibido, SinAlcanceDeInquilino
from app.config import ajustes
from app.datos.base import BaseMultiInquilino

_registro = logging.getLogger("myfittplan.datos")

#: Exime del filtro **una sentencia suelta**. Solo para las consultas que por definicion
#: preceden al inquilino: buscar el usuario al entrar, comprobar que un correo no este
#: repetido en toda la plataforma.
SIN_ALCANCE = "sin_alcance"

#: Claves que cada sesion lleva en su `info`. El alcance vive en la sesion y no en un
#: ContextVar: FastAPI abre las dependencias generadoras en un hilo distinto del endpoint,
#: asi que lo fijado al abrir la sesion no se veria al usarla.
ALCANCE = "alcance_de_inquilino"
EXENTA = "sesion_sin_alcance"


#: Lo que nunca corre contra una base que no sea la de pruebas.
_DDL_DESTRUCTIVO = re.compile(r"^\s*(drop\s+(table|database|schema)|truncate)\b", re.I)


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

    @event.listens_for(maquina, "before_cursor_execute")
    def _sin_tirar_tablas(
        _conexion: Any, _cursor: Any, sentencia: str, *_resto: Any, **_llaves: Any
    ) -> None:
        """Frena un `DROP TABLE` cuando la base no es la de pruebas.

        No es defensivo de más: la suite tira el esquema en cada corrida, y un script suelto
        que importe el motor sin pasar por el `conftest` apunta a la base de desarrollo. Se
        para en la primera sentencia, con la base todavía entera, en vez de descubrirlo
        cuando la aplicación responde 500 porque falta una tabla.
        """
        if ajustes().entorno == "pruebas":
            return
        if _DDL_DESTRUCTIVO.match(sentencia):
            raise BorradoDeEsquemaProhibido(
                f"Se intentó «{sentencia.strip()[:60]}» sobre la base «{ajustes().entorno}». "
                "Solo se tiran tablas con LM_ENTORNO=pruebas. Si de verdad quieres "
                "reconstruir esta base, usa alembic."
            )

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
    """Inyecta `WHERE coach_id = :actual` en toda lectura multi-inquilino. Va sobre
    `with_loader_criteria` para alcanzar tambien los JOIN y la carga diferida."""
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

    # `coach_id` va como cierre: `with_loader_criteria` cachea la lambda por objeto de
    # codigo, y llamar a una funcion dentro lanza `InvalidRequestError`.
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
        try:
            sesion.commit()
        except Exception:
            # Corre despues de responder, asi que el cliente ya tiene su 200. Se registra
            # completo: un guardado que revienta y responde «listo» es lo peor posible.
            _registro.exception("el commit falló tras responder; se pierde el guardado")
            raise
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
