/** Tema (claro/oscuro/sistema) de la interfaz, por cuenta. */

import { useEffect, useState, type ReactNode } from "react";

import { api } from "@/lib/api";
import { actorGuardado, guardarActor, suscribirACambiosDeActor } from "@/lib/sesion";
import { aplicarTema, contextoDeTema, guardarTema, temaDe, temaGuardado, type Tema } from "./tema";

export function TemaProvider({ children }: { children: ReactNode }) {
  // El tema de la cuenta manda: si hay sesión se usa el de esa cuenta, no el del
  // dispositivo. Sin sesión queda el que se guardó como caché (o el sistema).
  const [tema, setTema] = useState(() => temaDe(actorGuardado()) ?? temaGuardado());

  // Login, refresco del actor (`/auth/yo`) y cierre de sesión cambian el tema del que se
  // parte: aquí se sigue a la cuenta de turno para que una cuenta no se herede en la otra.
  useEffect(() => {
    return suscribirACambiosDeActor(() => {
      setTema(temaDe(actorGuardado()) ?? temaGuardado());
    });
  }, []);

  useEffect(() => {
    aplicarTema(tema);
  }, [tema]);

  const fijar = (nuevo: Tema) => {
    setTema(nuevo);
    // Copia en localStorage: es la caché del dispositivo, el punto de partida de la
    // pantalla sin sesión y de la primera aplicación antes de pintar en `index.html`.
    guardarTema(nuevo);
    const actor = actorGuardado();
    if (actor) {
      // El tema vive en la cuenta, no en el navegador: se persiste en el servidor para que
      // se lo lleve a cualquier dispositivo. Así otra cuenta en esta máquina no lo ve.
      guardarActor({ ...actor, tema: nuevo });
      void api.acceso.tema(nuevo).catch(() => {
        /* si falla la red aquí, el tema sigue en memoria y se retoma en el /auth/yo siguiente */
      });
    }
  };

  return (
    <contextoDeTema.Provider value={{ tema, fijar }}>{children}</contextoDeTema.Provider>
  );
}