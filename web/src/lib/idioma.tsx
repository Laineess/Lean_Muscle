import { useEffect, useState, type ReactNode } from "react";

import { api } from "@/lib/api";
import { actorGuardado, guardarActor, suscribirACambiosDeActor } from "@/lib/sesion";
import { CLAVE_IDIOMA, contextoDeIdioma, idiomaGuardado, type Idioma } from "./idioma";
import { EN } from "./traducciones";

function guardarEnLocalStorage(i: Idioma): void {
  try {
    localStorage.setItem(CLAVE_IDIOMA, i);
  } catch {
    // navegación privada o almacenamiento bloqueado: se sigue en memoria
  }
}

export function IdiomaProvider({ children }: { children: ReactNode }) {
  // El idioma de la cuenta manda: si hay sesión se usa el de esa cuenta, no el del
  // dispositivo. Sin sesión queda el que se guardó como caché (o el primero, español).
  const [idioma, setIdioma] = useState<Idioma>(
    () => idiomaDe(actorGuardado()) ?? idiomaGuardado(),
  );

  // Login, refresco del actor (`/auth/yo`) y cierre de sesión cambian el idioma del que se
  // parte: aquí se sigue a la cuenta de turno.
  useEffect(() => {
    return suscribirACambiosDeActor(() => {
      setIdioma(idiomaDe(actorGuardado()) ?? idiomaGuardado());
    });
  }, []);

  useEffect(() => {
    document.documentElement.lang = idioma;
  }, [idioma]);

  // Copia en localStorage: `formato.ts` lo lee fuera de React de forma síncrona, y es el
  // punto de partida de la pantalla sin sesión.
  useEffect(() => {
    guardarEnLocalStorage(idioma);
  }, [idioma]);

  const fijar = (i: Idioma) => {
    setIdioma(i);
    // Síncrona para `formato.ts`, que la lee fuera de React; también es el punto de
    // partida de la pantalla sin sesión.
    guardarEnLocalStorage(i);
    const actor = actorGuardado();
    if (actor) {
      // El idioma vive en la cuenta, no en el navegador: se persiste en el servidor para
      // que se lo lleve a cualquier dispositivo. Asi otra cuenta en esta maquina no lo ve.
      guardarActor({ ...actor, idioma: i });
      void api.acceso.idioma(i).catch(() => {
        /* si falla la red aquí, el idioma sigue en memoria y se retoma en el /auth/yo siguiente */
      });
    }
  };

  const alternar = () => fijar(idioma === "es" ? "en" : "es");

  const t = (texto: string, reemplazos?: Record<string, string | number>): string => {
    let salida = idioma === "en" ? (EN[texto] ?? texto) : texto;
    if (reemplazos) {
      for (const [clave, valor] of Object.entries(reemplazos)) {
        salida = salida.split(`{${clave}}`).join(String(valor));
      }
    }
    return salida;
  };

  return (
    <contextoDeIdioma.Provider value={{ idioma, fijar, alternar, t }}>
      {children}
    </contextoDeIdioma.Provider>
  );
}

/** El idioma de una cuenta, si el servidor se lo dio (cuentas previas al cambio no lo tienen).
 *  Devuelve `null` cuando no hay sesión o el valor no es uno de los conocidos. */
function idiomaDe(actor: { idioma?: string } | null): Idioma | null {
  if (actor?.idioma === "es" || actor?.idioma === "en") return actor.idioma;
  return null;
}