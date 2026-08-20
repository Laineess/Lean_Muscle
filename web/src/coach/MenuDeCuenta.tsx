/** Menú del avatar: el índice de sus pantallas de configuración.
 *
 *  Sin librería: es una lista de enlaces. Lo que sí hace falta es que se cierre como se
 *  espera —fuera, Escape, al navegar—, porque uno que se queda abierto tapa la pantalla.
 */

import {
  CalendarClock,
  ClipboardList,
  Eye,
  Megaphone,
  Palette,
  Settings,
  Tag,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useRef } from "react";
import { Link, useLocation } from "react-router-dom";

import { BotonSalir } from "@/componentes/Seguridad";
import { Regla } from "@/componentes/primitivas";
import { cn } from "@/lib/utils";

interface Opcion {
  ruta: string;
  rotulo: string;
  detalle: string;
  Icono: LucideIcon;
}

const OPCIONES: Opcion[] = [
  { ruta: "/coach/avisos", rotulo: "Avisos", detalle: "Mándale una frase a tus alumnas", Icono: Megaphone },
  { ruta: "/coach/ajustes", rotulo: "Ajustes", detalle: "Zona horaria, avisos y contraseña", Icono: Settings },
  { ruta: "/coach/precios", rotulo: "Planes y precios", detalle: "Lo que vendes y lo que cobras suelto", Icono: Tag },
  { ruta: "/coach/horario", rotulo: "Horario de consultas", detalle: "Cuándo pueden reservarte tus alumnas", Icono: CalendarClock },
  { ruta: "/coach/presentacion", rotulo: "Presentación", detalle: "Lo primero que ve una alumna nueva", Icono: Eye },
  { ruta: "/coach/cuestionario", rotulo: "Cuestionario", detalle: "Las preguntas que contesta al entrar", Icono: ClipboardList },
  { ruta: "/coach/apariencia", rotulo: "Apariencia", detalle: "Tu marca, tu color y el tema", Icono: Palette },
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
          // Crece desde la esquina de la que cuelga, que es de donde el ojo viene.
          className="animate-emerge absolute right-0 top-full z-40 mt-2 w-72 origin-top-right overflow-hidden rounded-marco border border-linea bg-fondo-elevado shadow-lg"
        >
          <ul className="escalona flex flex-col py-1">
            {OPCIONES.map(({ ruta, rotulo, detalle, Icono }) => (
              <li key={ruta}>
                <Link
                  to={ruta}
                  role="menuitem"
                  className={cn(
                    "group flex items-start gap-3 px-4 py-2.5",
                    "transition-colors duration-[var(--mov-rapido)] ease-suave hover:bg-fondo-sutil",
                    pathname === ruta && "bg-fondo-sutil",
                  )}
                >
                  <Icono
                    aria-hidden
                    className={cn(
                      "mt-0.5 size-4 shrink-0 transition-colors duration-[var(--mov-rapido)]",
                      pathname === ruta ? "text-acento" : "text-tinta-suave group-hover:text-tinta",
                    )}
                  />
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className="text-menor font-medium">{rotulo}</span>
                    <span className="text-micro text-tinta-suave">{detalle}</span>
                  </span>
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
