/** Diccionario español → inglés de la interfaz.
 *
 *  Las claves son SIEMPRE la cadena en español tal cual aparece en el código; `t()` busca
 *  aquí la versión en inglés cuando el idioma activo es «en» y si no existe devuelve el
 *  texto original, de modo que migrar es seguro: nada se rompe, solo se traduce lo que
 *  ya tiene entrada.
 *
 *  Las cadenas con datos usan `{clave}` y se interpolan desde `t(texto, { clave })`.
 */

import { EN_ALUMNA } from "./traducciones-alumna";
import { EN_COACH } from "./traducciones-coach";
import { EN_COACH_B } from "./traducciones-coach-b";
import { EN_PLATAFORMA } from "./traducciones-plataforma";
import { EN_RAIZ } from "./traducciones-raiz";

export const EN: Record<string, string> = {
  /* Navegación y menús */
  "Panel": "Dashboard",
  "Pacientes": "Clients",
  "Alumnas": "Clients",
  "Agenda": "Schedule",
  "Finanzas": "Finances",
  "Ajustes": "Settings",
  "Ajustes y seguridad": "Settings & security",
  "Inicio": "Home",
  "Mi plan": "My plan",
  "Evolución": "Progress",
  "Mensajes": "Messages",
  "Avisos": "Notices",
  "Mi cuenta": "My account",
  "Privacidad": "Privacy",
  "Coaches": "Coaches",
  "Facturación": "Billing",
  "Salud": "Health",
  "Ir a": "Go to",
  "Secciones": "Sections",
  "Más opciones": "More options",
  "Tu cuenta": "Your account",
  "plataforma": "platform",
  "Este panel administra cuentas. No tiene acceso a fotografías, historiales, pesos ni nombres de alumnas: solo a cuántas hay.":
    "This panel manages accounts. It has no access to photos, histories, weights or client names: only to how many there are.",

  /* Menú hamburguesa e idioma */
  "Cerrar menú": "Close menu",
  "Abrir menú": "Open menu",
  "Abrir menú de opciones": "Open options menu",
  "Traducir al inglés": "Switch to English",
  "Volver al español": "Switch back to Spanish",
  "{nombre} · tu cuenta": "{nombre} · your account",
  "{nombre}. Tu cuenta": "{nombre}. Your account",
  "{nombre}. Abrir menú de opciones": "{nombre}. Open options menu",
  "{nombre} · opciones": "{nombre} · options",

  /* Menú del avatar (coach) */
  "Mándale una frase a tus alumnas": "Send a message to your clients",
  "Zona horaria, avisos y contraseña": "Time zone, notices and password",
  "Planes y precios": "Plans & pricing",
  "Lo que vendes y lo que cobras suelto": "What you sell and one-off charges",
  "Horario de consultas": "Consultation hours",
  "Cuándo pueden reservarte tus alumnas": "When your clients can book you",
  "Presentación": "Presentation",
  "Lo primero que ve una alumna nueva": "The first thing a new client sees",
  "Cuestionario": "Questionnaire",
  "Las preguntas que contesta al entrar": "The questions they answer on sign-up",
  "Apariencia": "Appearance",
  "Tu marca, tu color y el tema": "Your brand, your color and the theme",

  /* Buscador global (coach) */
  "Buscador": "Search",
  "Buscar alumna o sección…": "Search client or section…",
  "Busca una alumna, un chequeo o una sección…": "Search a client, a check-in or a section…",
  "Nada con ese nombre.": "Nothing matches that.",
  "ciclo {n}": "cycle {n}",
  "Ciclo {n} · {plan}": "Cycle {n} · {plan}",
  "sin plan": "no plan",
  "chequeo {d}": "check-in {d}",

  /* Estados de chequeo (rótulos compartidos) */
  "Borrador": "Draft",
  "En revisión": "Under review",
  "Validado": "Validated",
  "Rechazado": "Rejected",
  "Descartado": "Discarded",

  /* Seguridad (contraseña y sesión) */
  "Seguridad": "Security",
  "Cambiar mi contraseña": "Change my password",
  "Contraseña actual": "Current password",
  "Nueva contraseña": "New password",
  "Al menos {n} caracteres, debe incluir números y 1 caracter especial.":
    "At least {n} characters, including numbers and 1 special character.",
  "Repítela": "Repeat it",
  "Escribe tu contraseña actual.": "Enter your current password.",
  "La nueva necesita al menos {n} caracteres.": "The new one needs at least {n} characters.",
  "Necesita al menos un número.": "It needs at least one number.",
  "Necesita al menos un carácter especial, por ejemplo ! ? # o $.":
    "It needs at least one special character, e.g. ! ? # or $.",
  "Las dos nuevas no coinciden.": "The two new passwords don't match.",
  "La nueva tiene que ser distinta de la actual.": "The new password must be different from the current one.",
  "No se pudo cambiar.": "It couldn't be changed.",
  "Se cerrarán todas tus sesiones": "All your sessions will be closed",
  "También la de este dispositivo. Es a propósito: si alguien más había entrado, cambiar la contraseña sin cerrar su sesión no lo sacaría. Tendrás que volver a entrar.":
    "Including the one on this device. It's intentional: if someone else had logged in, changing the password without closing their session wouldn't kick them out. You'll have to sign in again.",
  "Cambiando…": "Changing…",
  "Cambiar contraseña": "Change password",
  "Te llegará un correo avisando del cambio, por si no fuiste tú.":
    "You'll receive an email about the change, in case it wasn't you.",
  "Cerrar sesión": "Sign out",

  /* Tema */
  "Tema de la interfaz": "Interface theme",
  "Claro": "Light",
  "Oscuro": "Dark",
  "Como el sistema": "Follow system",

  /* Diálogos */
  "Cerrar": "Close",

  /* Estados, conexión e idioma compartidos */
  "Sin conexión con el servidor": "No connection to the server",
  "No se pudo contactar la API.": "Couldn't reach the API.",
  "Estás viendo datos de ejemplo.": "You're seeing sample data.",
  "Cargando {que}…": "Loading {que}…",
  "Cargando": "Loading",

  /* Notificaciones push */
  "No se pudieron activar las notificaciones.": "Couldn't enable notifications.",
  "Tu chequeo del mes, cuando tu coach revise, tus consultas y tus pagos.":
    "Your monthly check-in, when your coach reviews it, your consults and your payments.",
  "Chequeos por validar, consultas del día y comprobantes que llegan.":
    "Check-ins to review, today's consults and incoming receipts.",
  "Notificaciones": "Notifications",
  "Activas": "On",
  "Bloqueadas": "Blocked",
  "Apagadas": "Off",
  "Llegan al teléfono aunque la app esté cerrada.": "They reach your phone even when the app is closed.",
  "Este navegador no las admite": "This browser doesn't support them",
  "En iPhone hay que agregar la app a la pantalla de inicio para que funcionen. Mientras tanto los avisos importantes siguen llegando por correo.":
    "On iPhone you need to add the app to the home screen for them to work. Meanwhile important notices still arrive by email.",
  "Las bloqueaste en este navegador": "You blocked them in this browser",
  "Desde aquí ya no se pueden volver a pedir. Hay que permitirlas en los ajustes del navegador para este sitio y recargar.":
    "From here they can't be requested again. You need to allow them in this browser's settings for this site and reload.",
  "Desactivar": "Turn off",
  "Activar notificaciones": "Turn on notifications",

  /* Hilo de mensajes */
  "No se pudo abrir la conversación.": "Couldn't open the conversation.",
  "No se pudo enviar tu mensaje.": "Couldn't send your message.",
  "la conversación": "the conversation",
  "Todavía no hay mensajes con {contraparte}. Escribe el primero.":
    "No messages with {contraparte} yet. Write the first one.",
  " · leído": " · read",
  "Escribe tu mensaje": "Write your message",
  "Escribe aquí…": "Write here…",
  "Para dudas del plan. Si es una urgencia médica, acude a un servicio de salud.":
    "For plan questions. If it's a medical emergency, go to a health service.",
  "Lo que escribas aquí lo lee tu alumna tal cual.": "Your client reads whatever you write here, verbatim.",
  "Enviar": "Send",

  /* Límite de error */
  "Esta pantalla no se pudo mostrar": "This screen couldn't be displayed",
  "Algo falló al pintarla. El resto de la aplicación sigue funcionando: usa el menú para ir a otro lado.":
    "Something failed while drawing it. The rest of the app keeps working: use the menu to go somewhere else.",
  "Volver a intentar": "Try again",
  "Ir al inicio": "Go home",

  /* Cobertura por dominio: la fusión hace que ganen las cadenas de las pantallas. */
  ...EN_RAIZ,
  ...EN_COACH,
  ...EN_COACH_B,
  ...EN_ALUMNA,
  ...EN_PLATAFORMA,
};