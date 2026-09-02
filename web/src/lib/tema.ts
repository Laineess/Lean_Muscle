/** Modo claro y oscuro.
 *
 *  Tres estados, no dos: «sistema» es el de fábrica y respeta lo que la persona ya eligió en
 *  su teléfono. La clase va en `<html>`, y la primera aplicación ocurre en `index.html` antes
 *  de pintar para que no haya un parpadeo blanco al abrir en oscuro.
 */

import { createContext, useContext } from "react";

export type Tema = "sistema" | "claro" | "oscuro";

export const LLAVE_TEMA = "mfp:tema";

export function temaGuardado(): Tema {
  const v = localStorage.getItem(LLAVE_TEMA);
  return v === "claro" || v === "oscuro" ? v : "sistema";
}

/** Guarda el tema como caché del dispositivo. Sin sesión es el punto de partida; con
 *  sesión manda la cuenta, pero esta copia evita un parpadeo al abrir en oscuro. */
export function guardarTema(tema: Tema): void {
  try {
    if (tema === "sistema") localStorage.removeItem(LLAVE_TEMA);
    else localStorage.setItem(LLAVE_TEMA, tema);
  } catch {
    // navegación privada o almacenamiento bloqueado: se sigue en memoria
  }
}

/** El tema de una cuenta, si el servidor se lo dio (cuentas previas al cambio no lo tienen).
 *  Devuelve `null` cuando no hay sesión o el valor no es uno de los conocidos. */
export function temaDe(actor: { tema?: string } | null): Tema | null {
  if (actor?.tema === "claro" || actor?.tema === "oscuro" || actor?.tema === "sistema") {
    return actor.tema;
  }
  return null;
}

export function aplicarTema(tema: Tema): void {
  const raiz = document.documentElement;
  raiz.classList.toggle("claro", tema === "claro");
  raiz.classList.toggle("dark", tema === "oscuro");
}

export interface ValorDeTema {
  tema: Tema;
  fijar: (tema: Tema) => void;
}

export const contextoDeTema = createContext<ValorDeTema | null>(null);

export function useTema(): ValorDeTema {
  const valor = useContext(contextoDeTema);
  if (!valor) throw new Error("useTema debe usarse dentro de <TemaProvider>");
  return valor;
}
