# MyFittPlan

Plataforma SaaS de coaching físico y nutricional. Varias coaches, cada una con su cartera
de alumnas aislada, sobre un método de chequeo mensual estandarizado.

**MyFittPlan** es la plataforma; **LeanMuscle** es la marca comercial de una de las
coaches. En términos legales cada coach es Responsable del tratamiento y MyFittPlan es
su Encargada.

---

## Arrancar

```powershell
.\desarrollo.ps1        # entorno, base, migraciones y semilla, en un comando
```

Luego, en dos terminales:

```powershell
.\.venv\Scripts\uvicorn app.main:app --reload    # API en http://127.0.0.1:8000
cd web; npm run dev                               # Web en http://localhost:5173
```

La semilla crea dos coaches. Contraseña de todas las cuentas: `Demo1234!`

| Cuenta | Rol |
|---|---|
| `mariana@leanmuscle.mx` | Coach, 7 alumnas, historial completo |
| `andrea.saenz@ejemplo.mx` | Alumna con 4 chequeos |
| `regina@reginafit.mx` | Segunda coach — existe para que una fuga entre inquilinos se vea |

**Sin MySQL también se puede revisar el diseño**: en la pantalla de acceso hay dos botones
que entran con datos de ejemplo. Cuando la API no responde, cada pantalla lo dice en lugar
de fingir que los números son reales.

---

## Arquitectura

Monolito modular. FastAPI sirve la API; React compila a estáticos que sirve nginx.

```
┌──────────────────┐   ┌──────────────────┐
│  App de alumna   │   │ Panel de coach   │   React 19 + Vite + Tailwind v4
└────────┬─────────┘   └────────┬─────────┘
         └───────────┬──────────┘
                     ▼
              ┌─────────────┐
              │    nginx    │  TLS · estáticos · X-Accel
              └──────┬──────┘
                     ▼
        ┌────────────────────────────┐
        │  FastAPI sobre uvicorn     │
        │  rutas → dominio → datos   │
        └───┬──────────┬─────────┬───┘
            ▼          ▼         ▼
     ┌──────────┐ ┌────────┐ ┌─────────────┐
     │ MySQL 8.4│ │ Disco  │ │  Trabajador │
     └──────────┘ └────────┘ └─────────────┘
```

Python 3.12 · FastAPI · MySQL 8.4 · SQLAlchemy 2.0 + Alembic · Pydantic v2 · Argon2 ·
React 19 · TypeScript estricto · Tailwind v4 · Vite. Sin Docker y sin Node en producción.

### Por qué MySQL también en desarrollo

SQLite ahorraría la instalación, pero **la capa que sostiene el aislamiento entre coaches es
exclusiva de MySQL**: la variable de sesión `@app_coach_id` y las vistas por inquilino no
tienen equivalente. Sin CI, la prueba de fuga solo puede correr en tu máquina — y si MySQL
tiene que estar instalado igual, SQLite deja de ahorrar nada y solo suma un dialecto que
mantener. La velocidad tampoco es argumento: las pruebas de dominio ya corren sin base.

### Aislamiento entre coaches

MySQL no tiene Row Level Security, y el aislamiento es la base legal del modelo: una fuga
entre inquilinos es una infracción sancionable directamente a la coach. Esa red se repone
con cinco capas:

1. El `coach_id` sale de la sesión, nunca del cliente.
2. [`alcance.py`](app/datos/alcance.py) inyecta el filtro en cada `SELECT`, incluidos `JOIN`
   y carga diferida. Sin alcance lanza excepción: 500 antes que la fila de otra coach.
3. [`prueba_consultas.py`](pruebas/aislamiento/prueba_consultas.py) — cada consulta tiene su
   prueba de fuga, en los dos sentidos.
4. Llaves de almacenamiento con el inquilino en el prefijo.
5. Vistas `v_tabla`; el usuario de la aplicación no toca las tablas base.

Un ULID de otra coach **no existe** para la sesión: devuelve 404, no 403. Un 403 confirmaría
que existe en otro inquilino.

### La regla que sostiene todo

**`app/dominio` no importa nada de `app/datos`.** Las reglas de negocio se prueban sin
levantar una base. Lo verifica `ruff` y también
[`prueba_fronteras.py`](pruebas/aislamiento/prueba_fronteras.py), porque una regla de linter
se silencia con un `# noqa` y una prueba no.

---

## La calculadora metabólica

`Calculadora del Fitness.xlsm` es la herramienta con la que la clienta arma los planes hoy,
y **no aparece en ningún documento de requerimientos**. Está traducida a
[`calculadora.py`](app/dominio/calculadora.py) preservando fórmulas y constantes exactas;
cada una lleva anotada su celda de origen.

```
MG  = peso × %grasa                     MLG = peso − MG
TMB = 13.587×MLG + 9.613×MG + 198(solo hombre) − 3.351×edad + 674
Mantenimiento = TMB × actividad × 1.1         ← el 1.1 es el efecto térmico
Ajustadas     = Mantenimiento × (1 + %ajuste)
Carbos g = Ajustadas × %C / 4    Proteína g = × %P / 4    Grasa g = × %G / 9
```

Dos verificaciones la vigilan, y ambas comparan **celda por celda** contra el archivo
original: [`prueba_calculadora.py`](pruebas/unidad/prueba_calculadora.py) para el motor de
Python, y [`calculadora.mjs`](web/pruebas/calculadora.mjs) para el espejo en TypeScript que
usa la pantalla. Si los dos se separan, la coach vería un plan en pantalla y otro guardado.

**Una diferencia deliberada con la hoja**: ahí el déficit del día bajo (`G14`) y el ajuste
calórico (`C17`) son campos independientes que pueden quedar descuadrados sin que nada
avise. Aquí el día bajo *es* el ajuste capturado, y la pantalla muestra el promedio semanal
resultante.

---

## Verificar

```powershell
.\.venv\Scripts\python -m pytest pruebas -q        # 1014 pruebas
.\.venv\Scripts\python -m ruff check app pruebas
.\.venv\Scripts\python -m mypy app

cd web
npm run lint                   # estilo y errores que el compilador no ve
npm run build                  # tipos estrictos y compilación
node pruebas/clases.mjs        # que ningún color se pierda contra un tamaño
node pruebas/calculadora.mjs   # que el motor de la interfaz coincida con la hoja
```

Las pruebas corren contra `leanmuscle_pruebas`, no contra la base de trabajo: las de
aislamiento hacen DROP de todas las tablas. `.\desarrollo.ps1` crea las dos. Si la de
pruebas no existe, las 32 que necesitan MySQL se saltan y el aviso lo dice.

Sin MySQL se saltan las de aislamiento e integración. **Correrlas borra y recrea la base
local**, así que después hay que volver a sembrar:

```powershell
.\.venv\Scriptslembic stamp base; .\.venv\Scriptslembic upgrade head
.\.venv\Scripts\python -m app.semilla --reiniciar
```

Los PDF no necesitan nada del sistema: **ReportLab es Python puro**, así que se generan
igual en Windows que en el VPS y sus pruebas corren en cualquier máquina.
[GitHub Actions](.github/workflows/ci.yml) sí las corre, y **si la prueba de fuga falla no
se fusiona**.

---

## Estructura

```
app/
  dominio/          reglas puras, sin base de datos ni HTTP
    medidas.py      rangos antropométricos, varianza, promedio de pesajes
    chequeo.py      máquina de estados y sus guardas
    calculadora.py  la hoja de la clienta, traducida
    agenda.py       solape de citas y estados
    plan.py         guardas de publicación
    ciclo.py        vigencia de 30 días y bloqueos por pago
    huecos.py       horas libres para reservar consulta
    registro.py     el recorrido de una solicitud y sus plazos
    baja.py         los quince días de lectura y la confirmación por nombre
  datos/            modelos, alcance por inquilino, consultas
  rutas/            auth, API de alumna, captura del chequeo, API de coach, medios
    plataforma/     panel del superadmin: único paquete que puede consultar sin inquilino
  servicios/        Argon2, tokens, imágenes, almacenamiento, OCR, push, correo, bitácora
  semilla.py        dos coaches, a propósito
web/src/
  alumna/           inicio, chequeo, mi plan, evolución, mensajes, cuenta
  coach/            panel, cartera, calendario, validación, constructor, finanzas, conversación
  plataforma/       coaches, facturación, salud
  componentes/      primitivas, diálogo, gráfica, estados, hilo, notificaciones
  lib/              api, calculadora, formato, sesión, tipos, push
```

---

## Diseño

Negro y gris son la estructura; el dorado es el acento. Estilo editorial: espacio en blanco,
tipografía grande, pocas cajas.

**El dorado nunca lleva texto largo** — sobre blanco da 2.4:1 y el mínimo legible es 4.5:1.
Hay dos tokens: `--acento` para marcar (filetes, bordes, estado activo) y `--acento-texto`
para las pocas palabras que sí van en acento. El acento es **una sola variable**: cuando una
coach ponga su color, se reemplaza y no se toca ninguna pantalla.

Modo oscuro obligatorio, siguiendo al sistema: la alumna hace su chequeo recién despierta, a
menudo a oscuras.

Navegación: tres pestañas para la alumna (tres y no cinco — cada pestaña es una decisión
más); topbar y hamburguesa para la coach, más un buscador global con `⌘K`.

---

## Decisiones cerradas

| Punto | Decisión |
|---|---|
| Rostro en las fotos | Encuadre sin rostro, recortado en servidor. El original se elimina |
| Retención de fotos | 4 meses, conservando la de línea base con consentimiento aparte |
| Medidas | Busto y pecho separados: 8 perímetros + estatura |
| Calculadora | Integrada al constructor de planes |
| % de grasa | Lo estima la coach al validar el chequeo |
| Proyección | Solo la ve la coach: una fecha exacta convertiría una estimación en promesa |
| Refeeds | 1 o 2 días por semana; el refeed va a mantenimiento por defecto |
| Parámetros del ciclo | Por ciclo, heredando del anterior |
| Pesajes | Hasta 3 fechas por ciclo, con promedio |
| Día calendario | En la zona horaria de la alumna |
| Contraseña | Recuperación manual con clave temporal que emite la coach |
| «Recordarme» | Guarda el correo y alarga la cookie. **Nunca la contraseña** |
| Registro abierto | Liga propia por coach (`/r/{slug}`) con interruptor. La solicitud no es alumna |
| Precio de inscripción | El único `Servicio` con motivo `inscripcion`. Con cero o dos, la liga no enciende |
| Registro a medias | Se borra solo a los 7 días, con recordatorio dos días antes |
| Solicitud descartada | Pierde el acceso hoy; su expediente se borra a los 7 días |
| Imagen del comprobante | 12 meses. Se borra la imagen, **no** el registro del pago |
| Baja de una alumna | Fuera de la cartera hoy; 15 días de lectura; borrado total después |
| Confirmar la baja | Tecleando su nombre. No tiene deshacer |
| Almacenamiento | Disco del VPS. Sin transferencia internacional que declarar |

---

## Correo: por qué hace falta el dominio, no solo para HTTPS

El sistema manda invitaciones de alta, claves temporales, avisos de seguridad, confirmaciones
de cita, recibos de pago y avisos de purga de fotos. **Gmail no aguanta ese volumen**: corta
alrededor de 500 destinatarios diarios, y correo automático desde una cuenta personal a
decenas de destinatarios distintos es exactamente el patrón que los filtros marcan como
spam. El proveedor puede suspender la cuenta, y esa cuenta suele ser la personal de la coach.

Con **myfittplan.com** la solución cuesta tres registros DNS —SPF, DKIM y DMARC— y
resuelve entrega y reputación. Mientras tanto:

- El correo sale detrás de una interfaz ([`correo.py`](app/servicios/correo.py)): cambiar de
  proveedor es una clase.
- Se envía **con espaciado**, nunca en ráfaga.
- Solo va por correo lo que no puede perderse: acceso, dinero y privacidad. El día a día del
  método vive en notificación dentro de la plataforma. El reparto está en
  [`avisos.py`](app/dominio/avisos.py) y hay pruebas que lo vigilan.
- En desarrollo el emisor **no manda correo de verdad**: un `pytest` que dispare mensajes a
  direcciones reales es un accidente esperando a ocurrir.

## Pendientes

**Bloqueante para desplegar**: Let's Encrypt no emite certificados para una dirección IP.
Hace falta apuntar **myfittplan.com** al VPS; sin HTTPS no se pueden manejar datos de
salud.

**Legal**: los cuatro documentos están alineados a MyFittPlan y **pendientes de revisión
por abogado mexicano**. Los tres plazos de conservación dicen lo mismo en los tres, que es lo
que hay que mantener al tocar cualquiera:

| Documento | Sección de plazos |
|---|---|
| [Aviso de Privacidad v2](docs/Aviso_de_Privacidad_Alumnos_MyFittPlan_v2.md) | §8 |
| [Términos y Condiciones v2](docs/Terminos_y_Condiciones_Alumnos_MyFittPlan_v2.md) | §5 |
| [Contrato SaaS de Coaches v2](docs/Contrato_SaaS_Coaches_MyFittPlan_v2.md) | Anexo A.7 |
| [Anexo Legal v2](docs/Anexo_Legal_ProteccionDatos_MyFittPlan_v2.md) | §10 |

Los `.docx` de la versión 1.0 siguen en `docs/` como referencia histórica.

**Producto**: instalar `tesseract-ocr` con el paquete de idioma español en el VPS —sin él el
OCR devuelve una lectura vacía y la coach captura el comprobante a mano, que es el
comportamiento previsto, no un fallo— y generar el par de llaves VAPID
(`LM_VAPID_PUBLICA` / `LM_VAPID_PRIVADA`) sin el cual el interruptor de notificaciones lo dice
en claro en lugar de fingir que funciona.

**Infraestructura**: los scripts están escritos y **falta correrlos en el VPS**. El
instructivo completo está en [Operación del VPS](docs/Operacion_VPS.md):

```bash
sudo bash despliegue/endurecer.sh              # ufw, fail2ban, SSH solo con llave
sudo bash despliegue/volumen-cifrado.sh crear 20
sudo bash despliegue/respaldo.sh preparar
sudo bash despliegue/respaldo.sh verificar     # la prueba de restauración
```

Dos cosas de ahí que conviene tener claras antes de confiar en ellas:

- **El volumen LUKS protege el disco apagado**, no el servidor encendido. La llave vive en el
  propio servidor para que un reinicio de madrugada no deje la plataforma caída esperando que
  alguien teclee una frase. Contra un acceso con el sistema en marcha sirven el endurecimiento
  y la bitácora, no el cifrado. Es un intercambio consciente y reversible.
- **Los respaldos rotan a 30 días y ese número es legal, no técnico.** El Anexo Legal §10
  promete que las fotografías se borran a los 4 meses y que la purga alcanza a los respaldos
  al rotarlos. Guardarlos un año haría falsa esa promesa. En el peor caso una fotografía
  purgada sobrevive 30 días más dentro de un respaldo cifrado, y ese es el número que se
  puede afirmar ante una solicitud ARCO.

## Fotografías: el recorte ocurre antes del disco

El archivo que sube la alumna **nunca se guarda**. Se lee en memoria, se endereza según el
EXIF, se recorta el 18 % superior —cabeza y cuello—, se reescala y se convierte a WebP sin
metadatos. Lo que llega al disco ya viene recortado: no existe un instante en el que un
original identificable esté en el servidor, ni siquiera mientras se procesa.

El orden importa y por eso está escrito así en [`imagenes.py`](app/servicios/imagenes.py):
enderezar antes de recortar, porque en una foto tomada de lado el recorte se llevaría un
costado en lugar de la cabeza. Del EXIF solo se lee la fecha; **la geolocalización se
descarta**, que es un dato bastante más peligroso que la foto.

La nitidez se mide con la varianza del laplaciano y la luminancia con la media del canal gris.
Sirven para prefiltrar, no para decidir: la coach revisa igual. La postura y la vestimenta las
juzga ella, y el módulo no finge lo contrario.

Las imágenes **no las sirve Python**. La aplicación comprueba sesión, inquilino y permiso,
anota el acceso y responde con `X-Accel-Redirect`; nginx entrega el archivo desde una
`location internal;`, que es la que impide leer una foto adivinando su ruta. La configuración
está en [`nginx-myfittplan.conf`](despliegue/nginx-myfittplan.conf).

## Comprobantes: el OCR sugiere, la coach confirma


`pytesseract` corre contra el binario del sistema: sin costo por documento y, sobre todo, **el
comprobante nunca sale del servidor**. Mandarlo a un servicio externo sería una transferencia
de datos financieros que habría que declarar en el aviso de privacidad.

Lo que devuelve es una sugerencia. Un comprobante es una imagen que cualquiera puede editar,
así que ningún grado de confianza automática sustituye a que alguien mire su estado de cuenta:
el pago queda pendiente hasta que la coach lo valida. Si tesseract no está instalado, la
lectura sale vacía y el flujo sigue — un comprobante ilegible no debe impedir cobrar.

**La imagen se borra a los 12 meses; el cobro no.** Es lo que más pesa por alumna después de
las fotos, y lo que sostiene la contabilidad es el monto, la fecha y el concepto de la fila,
no la captura de pantalla. Queda `comprobante_purgado_en`, que distingue «nunca subió nada»
de «lo subió y su imagen ya venció»: al pedirla se responde 410 y no 404, porque llevan a la
coach a hacer cosas distintas. El plazo es `LM_RETENCION_COMPROBANTES_MESES` y **está
pendiente de que lo confirme un contador**: los cuatro documentos legales dicen 12 meses
para la imagen y remiten a la ley fiscal para el registro del pago.

## Notificaciones push

Es el canal del día a día: no depende de la reputación de un dominio de correo recién
comprado. El permiso se pide **al tocar el interruptor**, nunca al cargar la aplicación: un
navegador que ve el diálogo sin contexto lo bloquea, y bloqueado no se puede volver a pedir
desde la aplicación — se acabaría el canal para siempre en ese dispositivo.

Una suscripción que responde 404 o 410 **se borra, no se reintenta**: ese navegador murió
—desinstaló la app, limpió datos, cambió de teléfono— y seguir insistiendo solo gasta llamadas.

El service worker ([`web/public/sw.js`](web/public/sw.js)) **no cachea nada**. Un caché ahí
guardaría respuestas con datos de salud en el almacenamiento del navegador, fuera del control
de la sesión: seguirían disponibles después de cerrar sesión.

## El panel del superadmin no ve datos de alumnas

Administra coaches: altas, planes, límites, suscripciones y cobros. Y solo eso.

**De las tablas con datos de alumnas ahí únicamente salen COUNT, SUM, MIN y MAX.** Nunca una
fila, nunca un nombre, nunca un peso, nunca una fotografía. El panel dice cuántas alumnas
tiene cada coach, no quiénes son.

No es una preferencia de producto: frente a la LFPDPPP la plataforma es **Encargado** y la
coach es **Responsable**. Esa posición —la que sostienen los cuatro documentos legales— solo
se aguanta si el acceso técnico coincide con lo que dice el contrato. Un panel que puede
abrir el expediente de cualquiera convierte a la plataforma en corresponsable de todo.

Se impone con código, no con disciplina:

- Las consultas viven aisladas en [`repos/plataforma.py`](app/datos/repos/plataforma.py).
- [`prueba_plataforma.py`](pruebas/aislamiento/prueba_plataforma.py) lee su árbol sintáctico y
  falla ante un `select(Alumna)` o ante cualquier columna que identifique a una persona. Las
  columnas admitidas se declaran una por una **con su razón escrita**.
- Es el único paquete de rutas al que
  [`prueba_fronteras.py`](pruebas/aislamiento/prueba_fronteras.py) le permite importar
  `sin_alcance`; a todos los demás se lo prohíbe sobre el árbol de imports.

La auditoría que sí ve —qué acción, en qué cuenta, cuándo— llega **sin `detalle` y sin el
identificador de la entidad**. Sirve para responder «¿qué pasó en esta cuenta?» ante un
reclamo, y sigue siendo imposible reconstruir a qué alumna corresponde cada movimiento.

Las coaches pagan por transferencia y el panel registra quién está al corriente. Sin pasarela
por ahora: `suscripcion_coach` y `cobro_coach` ya describen el estado que un cobro automático
tendría que sincronizar el día que se conecte. Los cobros son **solo inserción** — corregir
uno mal capturado se hace con otro en negativo, porque un historial reescribible no sirve
para cuadrar cuentas.

## Registro abierto: una solicitud no es una alumna

Cada coach tiene su liga, `/r/{slug}`, con un interruptor. Quien la abre se registra sola:
correo, contraseña suya, código de seis dígitos, y de ahí el recorrido —presentación,
cuestionario con el plan que pide, reserva de su primera consulta y comprobante de
inscripción—. Al final espera a que la coach la acepte.

**Hasta entonces no es alumna.** La fila de `alumna` existe desde el primer paso, porque de
ella cuelgan el cuestionario, la cita y el cobro; lo que la distingue es `estado='solicitud'`,
y eso la deja fuera de la cartera, del límite de alumnas y del chequeo. Que el chequeo venga
después no es un detalle de orden: **son fotografías corporales, y no se le piden a alguien
con quien todavía no existe una relación**.

La guarda es una dependencia —`solo_alumna_aceptada`— y una dependencia se olvida con no
escribirla, así que [`prueba_fronteras.py`](pruebas/aislamiento/prueba_fronteras.py) recorre
los endpoints de `/api/mi` uno por uno y falla si aparece alguno que una solicitud alcanzaría.
Las excepciones —su propio recorrido, sus derechos ARCO— se declaran ahí con su motivo.

**Lo que deja a medias se borra solo a los siete días**, con recordatorio dos días antes: la
cuenta, el correo, los consentimientos, la cita, el cobro y el archivo del comprobante. Que
el borrado siga siendo completo lo vigila una prueba que compara contra las llaves foráneas
de la base, y no contra la memoria de quien agregue la siguiente tabla.

El código de seis dígitos **no pasa por la cola**: quien lo espera está mirando la pantalla y
la cola sale cada cinco minutos. Se manda dentro de la transacción, así que un correo que no
sale deshace el registro entero en lugar de dejar una cuenta que nadie puede verificar.

**Aceptar hace tres cosas de un golpe**: confirma su consulta, abre su primer ciclo con el
plan que la coach confirme —que puede no ser el que ella pidió— y le deja el chequeo
disponible. El límite de alumnas se cuenta aquí y no al registrarse, que es lo que permite
dejar la liga abierta con el cupo lleno. Puede aceptarla sin validar el pago: quien pagó en
efectivo no tiene comprobante que subir, y el adeudo sigue visible en su expediente.

**Descartar le corta el acceso hoy** y su expediente se borra a los siete días, con el
motivo por correo escrito para ella. La consulta que había reservado se borra en lugar de
cancelarse: es un hueco que otra puede tomar hoy.

## La baja borra de verdad, quince días después

Dar de baja a una alumna son dos momentos, y separarlos es lo que hace que ninguno de
los dos sea injusto:

- **Hoy** sale de la cartera y deja de tener servicio. Se le manda su expediente en PDF
  —lo que capturó es suyo, y la baja no puede ser la forma de quedárselo— y conserva
  **quince días de solo lectura** para descargar lo que quiera.
- **A los quince días** se borra todo: fotos, medidas, pesos, historial clínico,
  respuestas, mensajes, y la cuenta con su correo. Puede volver a registrarse después,
  porque ese correo vuelve a estar libre.

La regla de la lectura es **el método de la petición**, no una lista de rutas: se le
corta escribir, y una lista de rutas se queda corta en cuanto alguien agrega un endpoint.

**Lo único que sobrevive es el dinero y lo que la ley obliga a guardar.** La ficha de
`alumna` no se borra: se vacía. Sin ella no habría dónde colgar los consentimientos, la
bitácora de accesos y los movimientos —cinco años los tres— y con ella vacía ninguno
identifica ya a nadie: la coach lee «Alumna dada de baja» en sus finanzas de hace dos
años y su contabilidad sigue cuadrando. Sus propias lecturas sí se van con ella: la
bitácora existe para responder «¿quién **más** vio mi expediente?».

Que ese «todo» siga siendo cierto lo vigila una prueba que compara contra las llaves
foráneas de la base. Lo que sobrevive se declara con el motivo por el que la ley lo pide,
y una tabla nueva que cuelgue de la alumna falla hasta que alguien decida cuál de las dos
cosas es.

**Se confirma tecleando su nombre**, y antes se le enseña lo que debe: darla de baja no
cobra ni cancela sus adeudos, así que esa decisión se toma mirándolos. La baja no está en
el formulario de edición como un estado más —lo estuvo, y ahí era un cambio de campo
cualquiera—: tiene su propio endpoint porque arranca un plazo que no se deshace.

## Bitácora: quién vio qué y quién cambió qué

Son dos registros distintos, y el Anexo Legal §6 exige ambos:

- **`acceso_sensible`** anota *lecturas*: abrir las fotos de un chequeo, leer un historial
  clínico, descargar un PDF. Es lo que permite responder a una alumna que pregunta quién ha
  visto su expediente.
- **`bitacora`** anota *escrituras* sobre datos sensibles, es de solo inserción y se conserva
  cinco años. Guarda **qué campos cambiaron, no sus valores**: copiarlos duplicaría el dato
  sensible en una tabla que sobrevive a la cancelación.

Todo pasa por [`servicios/bitacora.py`](app/servicios/bitacora.py) — una sola implementación,
porque dos versiones de la misma obligación legal terminan con una desactualizada.

**Registrar no queda a criterio de quien programe el endpoint.**
[`prueba_bitacora.py`](pruebas/aislamiento/prueba_bitacora.py) lee el árbol sintáctico de las
rutas y falla si aparece un endpoint que toca `Foto`, `HistorialClinico`, `Chequeo`, `Medida`,
`Pesaje` o `Consentimiento` sin registrar. Las excepciones se declaran con su motivo, y hay
una prueba que borra las que ya no corresponden a ningún endpoint.

## Trabajos programados

| Unidad | Cuándo | Qué hace |
|---|---|---|
| [`myfittplan-recordatorios.timer`](despliegue/myfittplan-recordatorios.timer) | 07:00 diario | Calcula y **encola** avisos de pago próximo, pago vencido, cita de mañana, inactividad y purga de fotos |
| [`myfittplan-purga.timer`](despliegue/myfittplan-purga.timer) | cada 30 min | **Borra** lo vencido: fotos de comida a las 36 h, fotos de chequeo al cumplir su retención, imágenes de comprobantes a los 12 meses, registros abandonados a los 7 días y expedientes de bajas a los 15 |
| [`myfittplan-correo.timer`](despliegue/myfittplan-correo.timer) | cada 5 min | **Envía** lo encolado —correo y push—, con espaciado y hasta 5 reintentos |
| [`myfittplan-respaldo.timer`](despliegue/myfittplan-respaldo.timer) | 03:30 diario | Volcado de la base y de los archivos, cifrado con GPG, rotación de 30 días |

Están separados a propósito: si el SMTP se cae a las 6 de la mañana, los recordatorios se
siguen calculando y nada se pierde. Y como cada aviso lleva una llave única construida por el
dominio, ejecutar el trabajo dos veces no manda el correo dos veces.
