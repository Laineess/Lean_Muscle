/* Service worker de MyFittPlan.
 *
 * Hace una sola cosa: recibir notificaciones y abrir la pantalla correcta al tocarlas.
 *
 * **No cachea nada.** Un caché aquí guardaría respuestas con datos de salud en el
 * almacenamiento del navegador, fuera del control de la sesión: seguirían ahí después de
 * cerrar sesión y sobrevivirían a un préstamo del teléfono. La app es rápida sin eso.
 */

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (evento) => evento.waitUntil(self.clients.claim()));

self.addEventListener("push", (evento) => {
  let datos = {};
  try {
    datos = evento.data ? evento.data.json() : {};
  } catch {
    /* Un payload ilegible no debe dejar al teléfono sin avisar de nada. */
  }

  const titulo = datos.titulo || "MyFittPlan";
  const opciones = {
    body: datos.cuerpo || "",
    // Etiqueta igual reemplaza la anterior en la bandeja: evita cinco avisos apilados de lo
    // mismo cuando el teléfono estuvo sin señal un rato.
    tag: datos.etiqueta || "myfittplan",
    renotify: false,
    icon: "/icono-192.png",
    badge: "/icono-192.png",
    data: { ruta: datos.ruta || "/inicio" },
  };

  evento.waitUntil(self.registration.showNotification(titulo, opciones));
});

self.addEventListener("notificationclick", (evento) => {
  evento.notification.close();
  const ruta = (evento.notification.data && evento.notification.data.ruta) || "/inicio";

  evento.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((ventanas) => {
      // Si la app ya está abierta se reutiliza esa pestaña: abrir una segunda deja dos
      // sesiones de la misma persona compitiendo por la misma pantalla.
      for (const ventana of ventanas) {
        if (ventana.url.includes(self.location.origin) && "focus" in ventana) {
          ventana.navigate(ruta);
          return ventana.focus();
        }
      }
      return self.clients.openWindow(ruta);
    }),
  );
});
