/** Marco de la app de alumna.
 *
 *  Tres pestañas, no cinco: cada pestaña extra es una decisión más que tomar. Cuenta,
 *  mensajes y avisos viven dentro de Inicio, que es donde ella llega siempre.
 *
 *  En teléfono la barra va abajo, al alcance del pulgar; en escritorio se convierte en
 *  barra superior, porque una barra flotante al pie de una pantalla grande no tiene sentido.
 */

import { LineChart, ListChecks, Sun } from "lucide-react";
import type { ComponentType } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { actorGuardado } from "@/lib/sesion";
import { cn } from "@/lib/utils";

interface Pestana {
  a: string;
  rotulo: string;
  Icono: ComponentType<{ className?: string; strokeWidth?: number }>;
}

const PESTANAS: Pestana[] = [
  { a: "/inicio", rotulo: "Inicio", Icono: Sun },
  { a: "/plan", rotulo: "Mi plan", Icono: ListChecks },
  { a: "/evolucion", rotulo: "Evolución", Icono: LineChart },
];

export function MarcoAlumna() {
  // La alumna ve la marca de su coach, no la de la plataforma: la relación es con ella.
  const marca = actorGuardado()?.marca ?? "MyProgressPlan";

  return (
    <div className="flex min-h-full flex-col">
      {/* Escritorio: la navegación sube y se vuelve discreta. */}
      <header className="sticky top-0 z-20 hidden border-b border-linea bg-fondo/85 backdrop-blur sm:block">
        <nav
          aria-label="Secciones"
          className="mx-auto flex h-16 w-full max-w-5xl items-center gap-8 px-6"
        >
          <span className="text-menor font-semibold tracking-[-0.01em]">{marca}</span>
          <div className="flex items-center gap-6">
            {PESTANAS.map(({ a, rotulo }) => (
              <NavLink
                key={a}
                to={a}
                className={({ isActive }) =>
                  cn(
                    "border-b-2 py-5 text-menor font-medium transition-colors",
                    isActive
                      ? "border-acento text-tinta"
                      : "border-transparent text-tinta-suave hover:text-tinta",
                  )
                }
              >
                {rotulo}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-5 pt-8 pb-28 sm:px-6 sm:pb-16">
        <Outlet />
      </main>

      {/* Teléfono: barra inferior fija, con área segura para el notch inferior. */}
      <nav
        aria-label="Secciones"
        className="fixed inset-x-0 bottom-0 z-20 border-t border-linea bg-fondo/95 backdrop-blur sm:hidden"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        <ul className="grid grid-cols-3">
          {PESTANAS.map(({ a, rotulo, Icono }) => (
            <li key={a}>
              <NavLink
                to={a}
                className={({ isActive }) =>
                  cn(
                    "flex h-16 flex-col items-center justify-center gap-1 text-micro font-medium",
                    isActive ? "text-tinta" : "text-tinta-suave",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <Icono className="size-5" strokeWidth={isActive ? 2.2 : 1.6} />
                    <span>{rotulo}</span>
                    {/* El dorado marca dónde estás; no lleva texto encima. */}
                    <span
                      className={cn(
                        "h-0.5 w-6 rounded-full transition-colors",
                        isActive ? "bg-acento" : "bg-transparent",
                      )}
                    />
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
