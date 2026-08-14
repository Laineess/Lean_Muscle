"""Acceso a datos SIN filtro por inquilino.

Tres cosas legitimas lo necesitan: las migraciones, los trabajos programados y el panel de
plataforma.

**Nada dentro de `app/rutas` salvo `app/rutas/plataforma` puede importarlo.** Lo prohibe
`ruff` y lo verifica `pruebas/aislamiento/prueba_fronteras.py` sobre el arbol de imports,
porque una regla de linter se silencia con un `# noqa` y una prueba no.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.datos.alcance import EXENTA, FabricaDeSesion, motor


@contextmanager
def sesion_sin_alcance(motivo: str) -> Iterator[Session]:
    """Sesion que ve todos los inquilinos. `motivo` es obligatorio y se registra.

    Se pide el motivo por escrito para que al leer el codigo quede claro por que este
    acceso existe. Si no se puede explicar en una linea, probablemente no corresponde.
    """
    if not motivo.strip():
        raise ValueError("sesion_sin_alcance exige un motivo explicito")

    sesion = FabricaDeSesion(bind=motor())
    # La exencion viaja en la sesion. Ver la nota en `alcance.py`.
    sesion.info[EXENTA] = motivo
    try:
        yield sesion
        sesion.commit()
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()
