/** Menú del avatar: a dónde va la coach cuando toca su foto.
 *
 *  Antes llevaba a una sola pantalla con todo dentro —marca, precios, presentación, tema,
 *  avisos, contraseña— y había que bajar buscando el bloque. Cada cosa vive ahora en su
 *  pantalla y esto es el índice.
 *
 *  Sin librería de menús: es una lista de enlaces. Lo que sí hace falta es que se cierre
 *  como se espera —fuera, Escape, al navegar— porque un menú que se queda abierto tapando
 *  la pantalla es peor que no tenerlo.
 */

import { useEffect, useRef } from "react";
import { Link, useLocation } from "react-router-dom";

import { BotonSalir } from "@/componentes/Seguridad";
import { Regla } from "@/componentes/primitivas";
import { cn } from "@/lib/utils";

const OPCIONES: [string, string, string][] = [
  ["/coach/avisos", "Avisos", "Mándale una frase a tus alumnas"],
  ["/coach/ajustes", "Ajustes", "Zona horaria, avisos y contraseña"],
  ["/coach/precios", "Planes y precios", "Lo que vendes y lo que cobras suelto"],
  ["/coach/presentacion", "Presentación", "Lo primero que ve una alumna nueva"],
  ["/coach/cuestionario", "Cuestionario", "Las preguntas que contesta al entrar"],
  ["/coach/apariencia", "Apariencia", "Tu marca, tu color y el tema"],
];

export function MenuDeCuenta({
  abierto,
  onCerrar,
  children,
}: {
  abierto: boolean;
  onCerrar: () => void;
  /** El disparador: el avatar. Va dentro para que el menú se ancle a él. */
  children: React.ReactNode;
}) {
  const caja = useRef<HTMLDivElement>(null);
  const { pathname } = useLocation();

  // Al navegar se cierra solo: si no, queda abierto encima de la pantalla nueva.
  useEffect(() => onCerrar(), [pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!abierto) return;

    const fuera = (e: MouseEvent) => {
      if (caja.current && !caja.current.contains(e.target as Node)) onCerrar();
    };
    const escape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCerrar();
    };

    document.addEventListener("mousedown", fuera);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", fuera);
      document.removeEventListener("keydown", escape);
    };
  }, [abierto, onCerrar]);

  return (
    <div ref={caja} className="relative ml-auto lg:ml-3">
      {children}

      {abierto ? (
        <div
          role="menu"
          aria-label="Tu cuenta"
          className="absolute right-0 top-full z-40 mt-2 w-72 overflow-hidden rounded-marco border border-linea bg-fondo-elevado shadow-lg"
        >
          <ul className="flex flex-col py-1">
            {OPCIONES.map(([ruta, rotulo, detalle]) => (
              <li key={ruta}>
                <Link
                  to={ruta}
                  role="menuitem"
                  className={cn(
                    "flex flex-col gap-0.5 px-4 py-2.5 transition-colors hover:bg-fondo-sutil",
                    pathname === ruta && "bg-fondo-sutil",
                  )}
                >
                  <span className="text-menor font-medium">{rotulo}</span>
                  <span className="text-micro text-tinta-suave">{detalle}</span>
                </Link>
              </li>
            ))}
          </ul>

          <Regla />

          <div className="px-4 py-3">
            <BotonSalir />
          </div>
        </div>
      ) : null}
    </div>
  );
}
