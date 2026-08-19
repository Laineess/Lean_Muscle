# Barridos

Cuatro pruebas que necesitan la API en pie, así que no van con `pytest`. Encuentran lo que
una prueba unitaria no ve: 500 contra MySQL, guardas que faltan, botones rotos y —lo peor—
respuestas que dicen «guardado» sin guardar nada.

```bash
.venv\Scripts\uvicorn app.main:app --port 8000
.venv\Scripts\python herramientas\barrido_500.py
```

| Barrido | Qué hace |
|---|---|
| `barrido_500.py` | Mete valores absurdos en cada cuerpo JSON, armados desde el propio OpenAPI. Un 4xx está bien; un 500 es un fallo. |
| `barrido_get.py` | Parámetros hostiles en cada lectura y archivos que no son imágenes en cada subida. |
| `barrido_permisos.py` | Cada endpoint contra cada rol y sin sesión. |
| `barrido_botones.py` | El camino feliz de cada botón de la interfaz, con datos como los que teclearía alguien. |

**Mirar también el log del servidor.** La sesión hace commit *después* de responder, así que
un guardado que revienta sale como 204 en el cliente y como traza en el log. Los barridos no
lo ven; `grep Traceback` sí.

`barrido_permisos` reporta seis sospechas que no lo son: un 422 por cuerpo vacío antes de la
guarda —con cuerpo válido responde 403— y `/api/mi/push`, que está abierto a todos los roles
a propósito porque la coach también recibe notificaciones.

Corren contra la base de desarrollo y dejan basura. Después: `python -m app.semilla --reiniciar`.
