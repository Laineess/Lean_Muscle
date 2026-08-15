/** Versión de las imágenes de la marca: el logo y el retrato de la coach.
 *
 *  Las dos se piden por una ruta fija —`/api/logo`, `/api/presentacion/foto`— así que al
 *  cambiarlas el navegador sigue sirviendo la anterior de su caché. Y la barra superior vive
 *  fuera de la pantalla de ajustes, de modo que subir un logo ahí no la hacía repintarse.
 *
 *  Esto resuelve las dos cosas con un número: subir una imagen lo incrementa, quien la pinta
 *  lo pone en la URL y vuelve a montarse. No guarda nada de la imagen, solo cuándo cambió.
 */

import { useSyncExternalStore } from "react";

let version = 0;
const suscriptores = new Set<() => void>();

/** Lo llama quien acaba de subir una imagen de marca. */
export function marcaCambiada(): void {
  version += 1;
  for (const avisar of suscriptores) avisar();
}

function suscribir(avisar: () => void): () => void {
  suscriptores.add(avisar);
  return () => suscriptores.delete(avisar);
}

/** La versión actual. Cambia sola cuando alguien sube un logo o un retrato. */
export function usarVersionDeMarca(): number {
  return useSyncExternalStore(
    suscribir,
    () => version,
    () => version,
  );
}
