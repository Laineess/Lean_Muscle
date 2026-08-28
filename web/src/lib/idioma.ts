import { createContext, useContext } from "react";

export type Idioma = "es" | "en";

export const CLAVE_IDIOMA = "myfittplan.idioma";

/** El idioma vigente para el formateo de fechas y números fuera de React. */
export function idiomaGuardado(): Idioma {
  try {
    return localStorage.getItem(CLAVE_IDIOMA) === "en" ? "en" : "es";
  } catch {
    return "es";
  }
}

export interface ValorDeIdioma {
  idioma: Idioma;
  fijar: (idioma: Idioma) => void;
  alternar: () => void;
  /** Traduce la cadena al idioma activo. `texto` es la versión en español (clave del
   *  diccionario); si no existe traducción se muestra tal cual, de modo que las cadenas
   *  sin migrar siguen funcionando y la cobertura crece de a poco. */
  t: (texto: string, reemplazos?: Record<string, string | number>) => string;
}

export const contextoDeIdioma = createContext<ValorDeIdioma | null>(null);

export function useIdioma(): ValorDeIdioma {
  const valor = useContext(contextoDeIdioma);
  if (!valor) throw new Error("useIdioma debe usarse dentro de <IdiomaProvider>");
  return valor;
}