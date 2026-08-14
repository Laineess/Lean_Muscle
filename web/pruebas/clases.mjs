/* Verifica que `cn` no descarte colores contra tamaños.
 *
 * Este archivo existe por un bug concreto: los botones salían invisibles porque
 * tailwind-merge trataba `text-fondo` (color) y `text-cuerpo` (tamaño) como el mismo
 * grupo y se quedaba solo con el último. En modo oscuro eso daba blanco sobre blanco.
 *
 *   node pruebas/clases.mjs
 */

import { clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

const COLORES = [
  "fondo", "fondo-sutil", "fondo-elevado", "tinta", "tinta-media", "tinta-suave",
  "linea", "linea-fuerte", "acento", "acento-texto", "acento-sutil",
  "peligro", "peligro-sutil", "exito", "exito-sutil",
];
const TAMANOS = ["micro", "menor", "cuerpo", "guia", "titulo", "portada", "cifra"];

const fusionar = extendTailwindMerge({
  extend: { theme: { color: COLORES, text: TAMANOS, radius: ["marco"] } },
});
const cn = (...e) => fusionar(clsx(e));

const casos = [
  {
    nombre: "botón sólido grande conserva color y tamaño",
    entrada: "bg-tinta text-fondo h-13 px-7 text-cuerpo",
    exige: ["text-fondo", "text-cuerpo", "bg-tinta"],
  },
  {
    nombre: "botón discreto chico conserva color y tamaño",
    entrada: "text-tinta-media hover:text-tinta h-8 px-3 text-micro",
    exige: ["text-tinta-media", "text-micro"],
  },
  {
    nombre: "botón peligro conserva color y tamaño",
    entrada: "border border-peligro text-peligro h-11 px-5 text-menor",
    exige: ["text-peligro", "text-menor"],
  },
  {
    nombre: "chip conserva tamaño base y color de variante",
    entrada: "text-micro font-semibold border-acento text-acento-texto bg-acento-sutil",
    exige: ["text-micro", "text-acento-texto", "bg-acento-sutil"],
  },
  {
    nombre: "dos tamaños sí colapsan al último",
    entrada: "text-menor text-cuerpo",
    exige: ["text-cuerpo"],
    prohibe: ["text-menor"],
  },
  {
    nombre: "dos colores sí colapsan al último",
    entrada: "text-tinta text-peligro",
    exige: ["text-peligro"],
    prohibe: ["text-tinta"],
  },
];

let fallos = 0;
for (const caso of casos) {
  const salida = cn(caso.entrada).split(" ");
  const faltan = (caso.exige ?? []).filter((c) => !salida.includes(c));
  const sobran = (caso.prohibe ?? []).filter((c) => salida.includes(c));

  if (faltan.length || sobran.length) {
    fallos++;
    console.log(`FALLA  ${caso.nombre}`);
    if (faltan.length) console.log(`       se perdió: ${faltan.join(", ")}`);
    if (sobran.length) console.log(`       sobrevivió de más: ${sobran.join(", ")}`);
    console.log(`       resultado: ${salida.join(" ")}`);
  } else {
    console.log(`OK     ${caso.nombre}`);
  }
}

console.log(fallos ? `\n${fallos} problema(s)` : "\nLas clases se combinan bien");
process.exit(fallos ? 1 : 0);
