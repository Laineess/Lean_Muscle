/** Sesión del navegador.
 *
 *  **La contraseña nunca se guarda.** «Recordar mis datos» hace dos cosas y ninguna es
 *  almacenar credenciales: recuerda el correo para no reescribirlo, y le pide al servidor
 *  una cookie de sesión de 30 días en lugar de una de 12 horas.
 *
 *  El token vive en una cookie `HttpOnly` que pone el servidor: JavaScript no lo lee ni lo
 *  escribe. Por eso aquí solo hay preferencias y una copia del actor para pintar la barra
 *  sin esperar a la red, nunca secretos.
 */

import { limpiarPaleta } from "@/lib/paleta";
import type { ActorPublico } from "@/lib/api";

export type Rol = "alumna" | "coach" | "admin_plataforma";

const LLAVE_CORREO = "mfp.correo_recordado";
const LLAVE_ACTOR = "mfp.actor";

function leer(almacen: Storage, llave: string): string | null {
  try {
    return almacen.getItem(llave);
  } catch {
    // Navegador en modo privado o con almacenamiento bloqueado: se sigue sin recordar.
    return null;
  }
}

function escribir(almacen: Storage, llave: string, valor: string | null): void {
  try {
    if (valor === null) almacen.removeItem(llave);
    else almacen.setItem(llave, valor);
  } catch {
    /* sin almacenamiento: no es un error que deba detener el acceso */
  }
}

export function correoRecordado(): string {
  return leer(localStorage, LLAVE_CORREO) ?? "";
}

export function recordarCorreo(correo: string, recordar: boolean): void {
  escribir(localStorage, LLAVE_CORREO, recordar ? correo : null);
}

/** Copia del actor para pintar la barra sin esperar a la red.
 *
 *  No es una fuente de verdad: la sesión real es la cookie, y el servidor decide. Si esto
 *  dice «coach» pero la cookie expiró, la primera petición devuelve 401 y se cierra sesión.
 */
export function actorGuardado(): ActorPublico | null {
  const bruto = leer(sessionStorage, LLAVE_ACTOR);
  if (!bruto) return null;
  try {
    return JSON.parse(bruto) as ActorPublico;
  } catch {
    return null;
  }
}

export function guardarActor(actor: ActorPublico): void {
  escribir(sessionStorage, LLAVE_ACTOR, JSON.stringify(actor));
  avisarDelCambioDeActor();
}

export function rolActual(): Rol | null {
  return actorGuardado()?.rol ?? null;
}

/** Quien quiera enterarse de los cambios de actor (login, refresco, cierre). Devuelve la
 *  función que cancela la suscripción. El idioma de la cuenta depende de estos cambios:
 *  al entrar otra cuenta hay que volver al idioma de la nueva, no quedarse con el anterior. */
export function suscribirACambiosDeActor(avisar: () => void): () => void {
  avisosDelCambioDeActor.add(avisar);
  return () => {
    avisosDelCambioDeActor.delete(avisar);
  };
}

const avisosDelCambioDeActor = new Set<() => void>();

function avisarDelCambioDeActor(): void {
  for (const avisar of avisosDelCambioDeActor) avisar();
}

export function cerrarSesion(): void {
  escribir(sessionStorage, LLAVE_ACTOR, null);
  avisarDelCambioDeActor();
  // Los colores viven en `<html>`, fuera de React: si no se quitan aquí, la marca de una
  // coach sigue puesta en el acceso y en el primer pintado de quien entre después.
  limpiarPaleta();
}
