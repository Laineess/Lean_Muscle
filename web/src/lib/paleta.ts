/** Los colores de la Coach, puestos en la interfaz.
 *
 *  Ella guarda dos hex y aquí salen seis variables CSS, recalculadas cada vez que cambia el
 *  tema. Ese recálculo no es un lujo: el mismo verde da 12.5:1 sobre blanco y 1.56:1 sobre
 *  negro, así que un solo valor para los dos temas deja la mitad de la interfaz sin ver.
 *
 *  Se escucha el tema por dos vías porque hay dos formas de cambiarlo: la clase que pone el
 *  selector y el ajuste del sistema operativo cuando nadie eligió nada.
 */

import { useEffect } from "react";

import { paletaDe } from "@/lib/color";

/** Los fondos de `index.css`. Si allá cambian, aquí también: son el suelo contra el que se
 *  mide el contraste, y medir contra el que no es da un color que no se ve. */
const FONDO_CLARO = "#ffffff";
const FONDO_OSCURO = "#0c0c0c";

/** Qué tema está pintando ahora mismo, con la misma regla que el CSS. */
export function esOscuro(): boolean {
  const raiz = document.documentElement;
  if (raiz.classList.contains("claro")) return false;
  if (raiz.classList.contains("dark") || raiz.classList.contains("oscuro")) return true;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

const TOKENS_DE_ACENTO = ["--acento", "--acento-texto", "--acento-sutil"] as const;
const TOKENS_SECUNDARIOS = ["--secundario", "--secundario-texto", "--secundario-sutil"] as const;

/** Devuelve la interfaz a los colores de fábrica.
 *
 *  Se llama al salir y en cualquier pantalla sin sesión. Sin esto, los colores de una coach
 *  se quedaban puestos en el acceso y en el primer pintado de quien entrara después: en un
 *  teléfono compartido, la alumna de otra coach veía la marca ajena.
 */
export function limpiarPaleta(): void {
  const raiz = document.documentElement;
  for (const token of [...TOKENS_DE_ACENTO, ...TOKENS_SECUNDARIOS]) {
    raiz.style.removeProperty(token);
  }
}

/** Escribe los seis tokens. Sin color los quita, en vez de dejar los de la sesión anterior. */
export function aplicarPaleta(acento?: string | null, secundario?: string | null): void {
  if (!acento && !secundario) {
    limpiarPaleta();
    return;
  }
  const fondo = esOscuro() ? FONDO_OSCURO : FONDO_CLARO;
  const raiz = document.documentElement;

  if (acento) {
    const p = paletaDe(acento, fondo);
    raiz.style.setProperty("--acento", p.base);
    raiz.style.setProperty("--acento-texto", p.texto);
    raiz.style.setProperty("--acento-sutil", p.sutil);
  } else {
    for (const token of TOKENS_DE_ACENTO) raiz.style.removeProperty(token);
  }

  if (secundario) {
    const p = paletaDe(secundario, fondo);
    raiz.style.setProperty("--secundario", p.base);
    raiz.style.setProperty("--secundario-texto", p.texto);
    raiz.style.setProperty("--secundario-sutil", p.sutil);
  } else {
    for (const token of TOKENS_SECUNDARIOS) raiz.style.removeProperty(token);
  }
}

/** Mantiene los tokens al día mientras la pantalla viva.
 *
 *  Vuelve a calcular al cambiar el tema por cualquiera de las dos vías. Sin esto, quien
 *  pasa de claro a oscuro con el selector se queda con el color calculado para el otro
 *  fondo, que es justo el caso que hay que evitar.
 */
export function usarPaleta(acento?: string | null, secundario?: string | null): void {
  useEffect(() => {
    aplicarPaleta(acento, secundario);

    const medio = window.matchMedia("(prefers-color-scheme: dark)");
    const alCambiar = () => aplicarPaleta(acento, secundario);
    medio.addEventListener("change", alCambiar);

    // El selector de tema cambia la clase de `<html>`, y eso no dispara ningún evento.
    const observador = new MutationObserver(alCambiar);
    observador.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    return () => {
      medio.removeEventListener("change", alCambiar);
      observador.disconnect();
    };
  }, [acento, secundario]);
}
