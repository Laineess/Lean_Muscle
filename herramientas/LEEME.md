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

**Mirar también el log del servidor.** Un guardado que revienta puede salir como 204 en el
cliente y como traza en el log. Los barridos no lo ven; `grep Traceback` sí. (El commit ya
corre **antes** de responder, así que un fallo se ve como 500; el hábito de mirar el log
sigue valiendo para lo que ocurre fuera de la petición: trabajos, correo y purga.)

**Apaga el correo antes de correrlos.** `barrido_botones` crea una solicitud de registro,
y el código de seis dígitos sale **en el momento**, sin pasar por la cola. Con
`LM_CORREO_REAL=true` cada corrida manda un correo de verdad a una dirección inventada,
que rebota contra la cuenta de la coach:

```bash
LM_CORREO_REAL=false .venv\Scripts\uvicorn app.main:app --port 8000
```

`barrido_permisos` reporta seis sospechas que no lo son: un 422 por cuerpo vacío antes de la
guarda —con cuerpo válido responde 403— y `/api/mi/push`, que está abierto a todos los roles
a propósito porque la coach también recibe notificaciones.

Corren contra la base de desarrollo y dejan basura. Después: `python -m app.semilla --reiniciar`.
