/** Modo claro y oscuro.
 *
 *  Tres estados, no dos: «sistema» es el de fábrica y respeta lo que la persona ya eligió en
 *  su teléfono. La clase va en `<html>`, y la primera aplicación ocurre en `index.html` antes
 *  de pintar para que no haya un parpadeo blanco al abrir en oscuro.
 */

export type Tema = "sistema" | "claro" | "oscuro";

export const LLAVE_TEMA = "mfp:tema";

export function temaGuardado(): Tema {
  const v = localStorage.getItem(LLAVE_TEMA);
  return v === "claro" || v === "oscuro" ? v : "sistema";
}

export function aplicarTema(tema: Tema): void {
  const raiz = document.documentElement;
  raiz.classList.toggle("claro", tema === "claro");
  raiz.classList.toggle("dark", tema === "oscuro");
}
