/** Notificaciones push en el navegador.
 *
 *  Es el canal del día a día del método: no depende de que el correo llegue ni de la
 *  reputación de un dominio recién comprado.
 *
 *  **El permiso se pide cuando la usuaria toca el interruptor, nunca al cargar la app.** Un
 *  navegador que ve el diálogo de permisos sin contexto lo bloquea, y bloqueado no se puede
 *  volver a pedir: se acabó el canal para siempre en ese dispositivo.
 */

import { api } from "@/lib/api";

export type EstadoPush = "no-soportado" | "bloqueado" | "activo" | "inactivo";

/** Safari en iOS solo permite push si la app está instalada en la pantalla de inicio. */
export function soportado(): boolean {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

export async function estado(): Promise<EstadoPush> {
  if (!soportado()) return "no-soportado";
  if (Notification.permission === "denied") return "bloqueado";

  const registro = await navigator.serviceWorker.getRegistration();
  const suscripcion = await registro?.pushManager.getSubscription();
  return suscripcion ? "activo" : "inactivo";
}

/** La llave pública VAPID viaja en base64url y `subscribe()` la pide en bytes.
 *
 *  Se construye sobre un `ArrayBuffer` explícito: el tipo por defecto de `Uint8Array` admite
 *  también memoria compartida, que `applicationServerKey` no acepta.
 */
function aBytes(base64url: string): Uint8Array<ArrayBuffer> {
  const relleno = "=".repeat((4 - (base64url.length % 4)) % 4);
  const base64 = (base64url + relleno).replace(/-/g, "+").replace(/_/g, "/");
  const crudo = window.atob(base64);
  const bytes = new Uint8Array(new ArrayBuffer(crudo.length));
  for (let i = 0; i < crudo.length; i += 1) bytes[i] = crudo.charCodeAt(i);
  return bytes;
}

function llaveEnBase64(suscripcion: PushSubscription, nombre: "p256dh" | "auth"): string {
  const bruto = suscripcion.getKey(nombre);
  if (!bruto) throw new Error(`la suscripción no trae ${nombre}`);
  return window
    .btoa(String.fromCharCode(...new Uint8Array(bruto)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

/** Registra el service worker. Sin él no hay push ni notificaciones. */
export async function registrarTrabajador(): Promise<ServiceWorkerRegistration | null> {
  if (!soportado()) return null;
  try {
    return await navigator.serviceWorker.register("/sw.js", { scope: "/" });
  } catch {
    // Un service worker que no registra no debe tumbar la app: solo se queda sin push.
    return null;
  }
}

/** Pide permiso, se suscribe y le pasa la suscripción al servidor. */
export async function activar(): Promise<EstadoPush> {
  if (!soportado()) return "no-soportado";

  const permiso = await Notification.requestPermission();
  if (permiso !== "granted") return permiso === "denied" ? "bloqueado" : "inactivo";

  const registro = (await navigator.serviceWorker.getRegistration()) ?? (await registrarTrabajador());
  if (!registro) return "no-soportado";

  const { publica } = await api.push.llave();
  if (!publica) {
    // Sin llave configurada en el servidor no hay nada que suscribir. Se dice en claro en
    // lugar de dejar un interruptor que parece funcionar y no notifica nunca.
    throw new Error("El servidor todavía no tiene configuradas las notificaciones.");
  }

  const suscripcion =
    (await registro.pushManager.getSubscription()) ??
    (await registro.pushManager.subscribe({
      // Obligatorio en todos los navegadores actuales: no se permite push silencioso.
      userVisibleOnly: true,
      applicationServerKey: aBytes(publica),
    }));

  await api.push.suscribir({
    endpoint: suscripcion.endpoint,
    p256dh: llaveEnBase64(suscripcion, "p256dh"),
    auth: llaveEnBase64(suscripcion, "auth"),
  });

  return "activo";
}

/** Cancela en el navegador **y** en el servidor.
 *
 *  Las dos cosas: cancelar solo en el navegador dejaría al servidor mandando a un endpoint
 *  muerto hasta agotar reintentos.
 */
export async function desactivar(): Promise<EstadoPush> {
  const registro = await navigator.serviceWorker.getRegistration();
  const suscripcion = await registro?.pushManager.getSubscription();
  if (suscripcion) await suscripcion.unsubscribe();
  await api.push.desuscribir();
  return "inactivo";
}
