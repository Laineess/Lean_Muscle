/** Marco del panel de plataforma.
 *
 *  Deliberadamente más sobrio que el de la coach: aquí no hay marca de nadie, no hay dorado
 *  de nadie y no hay nada que se parezca al producto que ve una alumna. Quien entra aquí
 *  administra cuentas, no acompaña a personas.
 *
 *  El aviso de la cabecera no es decorativo. Es el recordatorio de que este panel **no puede
 *  ver datos de alumnas**, que es la línea que sostiene que la plataforma sea Encargado y no
 *  Responsable frente a la LFPDPPP.
 */

import { ShieldAlert } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { BotonSalir } from "@/componentes/Seguridad";
import { cn } from "@/lib/utils";

const SECCIONES = [
  { a: "/plataforma", rotulo: "Coaches", exacto: true },
  { a: "/plataforma/facturacion", rotulo: "Facturación", exacto: false },
  { a: "/plataforma/salud", rotulo: "Salud", exacto: false },
];

export function MarcoPlataforma() {
  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-30 border-b border-linea bg-fondo/90 backdrop-blur">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center gap-6 px-5 sm:px-6">
          <span className="text-menor font-semibold tracking-[-0.01em]">
            MyProgressPlan <span className="text-tinta-suave">· plataforma</span>
          </span>

          <nav aria-label="Secciones" className="flex items-center gap-5 overflow-x-auto">
            {SECCIONES.map((s) => (
              <NavLink
                key={s.a}
                to={s.a}
                end={s.exacto}
                className={({ isActive }) =>
                  cn(
                    "border-b-2 py-5 text-menor font-medium whitespace-nowrap transition-colors",
                    isActive
                      ? "border-acento text-tinta"
                      : "border-transparent text-tinta-suave hover:text-tinta",
                  )
                }
              >
                {s.rotulo}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto">
            <BotonSalir />
          </div>
        </div>
      </header>

      <div className="border-b border-linea bg-fondo-sutil">
        <p className="mx-auto flex w-full max-w-6xl items-center gap-2 px-5 py-2 text-micro text-tinta-media sm:px-6">
          <ShieldAlert className="size-3.5 shrink-0" />
          Este panel administra cuentas. No tiene acceso a fotografías, historiales, pesos ni
          nombres de alumnas: solo a cuántas hay.
        </p>
      </div>

      <main className="mx-auto w-full max-w-6xl flex-1 px-5 py-8 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}
