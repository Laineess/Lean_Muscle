import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/* tailwind-merge resuelve conflictos entre clases, pero solo conoce las escalas de Tailwind
 * por defecto. Las nuestras hay que declararlas o las confunde: `text-fondo` (color) y
 * `text-cuerpo` (tamaño) caen en el mismo grupo `text-*`, y descarta una.
 *
 * Eso fue exactamente el bug de los botones invisibles: el color de texto se perdía contra
 * el tamaño, el botón heredaba --tinta y quedaba blanco sobre blanco en modo oscuro.
 *
 * Al agregar un token nuevo en index.css hay que agregarlo también aquí. */

const COLORES = [
  "fondo",
  "fondo-sutil",
  "fondo-elevado",
  "tinta",
  "tinta-media",
  "tinta-suave",
  "linea",
  "linea-fuerte",
  "acento",
  "acento-texto",
  "acento-sutil",
  "peligro",
  "peligro-sutil",
  "exito",
  "exito-sutil",
] as const;

const TAMANOS = ["micro", "menor", "cuerpo", "guia", "titulo", "portada", "cifra"] as const;

const fusionar = extendTailwindMerge({
  // `theme` va dentro de `extend`: en la raíz se ignora en silencio, que es como se coló
  // el bug de los botones invisibles.
  extend: {
    theme: {
      color: [...COLORES],
      text: [...TAMANOS],
      radius: ["marco"],
    },
  },
});

/** Combina clases resolviendo conflictos de Tailwind (la última gana). */
export function cn(...entradas: ClassValue[]) {
  return fusionar(clsx(entradas));
}
