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

**Y mirar la columna `error` de `aviso_enviado`.** Ahí es donde se esconde lo que falla
*después* de responder. Así vivió meses un `KeyError` que impedía enviar **todos** los
recibos de pago: encolar respondía 200, el correo moría a las 3 de la mañana y ningún
barrido lo veía. Ahora lo vigila `pruebas/aislamiento/prueba_contexto_de_avisos.py`, pero la
consulta sigue valiendo:

```sql
select tipo, canal, error, count(*) from aviso_enviado
where error is not null and enviado_en is null group by 1, 2, 3;
```

El `enviado_en is null` importa: un push a quien nunca activó las notificaciones deja
«sin suscripciones» en `error` **y** se marca como enviado, porque no hay nada que
reintentar. Sin ese filtro, veinticinco no-fallos tapan el que sí lo es.

**Apaga el correo antes de correrlos.** `barrido_botones` crea una solicitud de registro,
y el código de seis dígitos sale **en el momento**, sin pasar por la cola. Con
`LM_CORREO_REAL=true` cada corrida manda un correo de verdad a una dirección inventada,
que rebota contra la cuenta de la coach:

```bash
LM_CORREO_REAL=false .venv\Scripts\uvicorn app.main:app --port 8000
```

**Los cuatro salen en cero.** `barrido_permisos` reportaba seis sospechas que no lo eran:
mandaba `{}` como cuerpo, así que la respuesta era un 422 de validación en lugar del 403 de
la guarda, y un 422 no dice nada sobre permisos. Ahora arma los cuerpos válidos desde el
propio OpenAPI y lo que responde es la guarda. `/api/mi/push` quedó declarado en
`COMPARTIDAS`, con su motivo: está abierto a todos los roles a propósito porque la coach
también recibe notificaciones.

Dos cosas de ese barrido que conviene saber antes de tocarlo:

- **No prueba el camino del dueño.** Con cuerpos válidos eso mandaría un aviso a todas las
  alumnas en cada corrida. Que el dueño sí entra lo comprueba `barrido_botones.py`.
- **Un patrón nuevo sin valor de ejemplo se avisa al final.** Si un campo declara un
  `pattern` que ningún candidato de `PATRONES` satisface, el cuerpo no validaría y el 422
  parecería un permiso bien puesto; por eso se reporta en vez de callarse.

Corren contra la base de desarrollo y dejan basura. Después: `python -m app.semilla --reiniciar`.
