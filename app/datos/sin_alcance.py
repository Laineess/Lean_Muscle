"""Acceso a datos SIN filtro por inquilino.

Existe porque tres cosas legitimas necesitan cruzar inquilinos: las migraciones, los
trabajos programados (purga de fotos, ciclos vencidos, recordatorios) y el panel de
administracion de plataforma.

**Nada dentro de `app/rutas/alumna`, `app/rutas/coach` ni `app/dominio` puede importar
este modulo.** `ruff` lo prohibe con una regla de imports prohibidos (ver
`app/dominio/.ruff.toml`) y `pruebas/aislamiento/prueba_fronteras.py` lo verifica sobre
el arbol completo, porque una regla de linter se puede silenciar con un `# noqa` y una
prueba no.

Toda lectura hecha aqui que toque datos sensibles deja fila en `acceso_sensible`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.datos.alcance import SIN_ALCANCE, FabricaDeSesion, motor


@contextmanager
def sesion_sin_alcance(motivo: str) -> Iterator[Session]:
    """Sesion que ve todos los inquilinos. `motivo` es obligatorio y se registra.

    Se pide el motivo por escrito para que al leer el codigo quede claro por que este
    acceso existe. Si no se puede explicar en una linea, probablemente no corresponde.
    """
    if not motivo.strip():
        raise ValueError("sesion_sin_alcance exige un motivo explicito")

    sesion = FabricaDeSesion(bind=motor())
    # `execution_options` sobre la sesión existe en SQLAlchemy 2.0 pero no está en los
    # stubs; devuelve la misma sesión con la opción puesta.
    sesion = sesion.execution_options(**{SIN_ALCANCE: True})  # type: ignore[attr-defined]
    try:
        yield sesion
        sesion.commit()
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()
