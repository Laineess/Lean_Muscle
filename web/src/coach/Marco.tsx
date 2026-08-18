/** Marco del panel de coach.
 *
 *  Barra superior en escritorio; menú de hamburguesa en teléfono. Mismo sistema visual que
 *  la app de la alumna —los dos frentes se sienten del mismo producto— y el buscador global
 *  resuelve la densidad: con 60 alumnas no se recorre una lista, se busca.
 */

import { Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { Limite } from "@/componentes/Limite";
import { Buscador, DisparadorBuscador, useBuscador } from "@/coach/Buscador";
import { MenuDeCuenta } from "@/coach/MenuDeCuenta";
import { urlDeFotoDeCoach, urlDeLogo } from "@/lib/api";
import { usarVersionDeMarca } from "@/lib/marca";
import { coach } from "@/lib/datos";
import { actorGuardado } from "@/lib/sesion";
import { iniciales } from "@/lib/formato";
import { cn } from "@/lib/utils";

const SECCIONES = [
  { a: "/coach", rotulo: "Panel", exacto: true },
  { a: "/coach/alumnas", rotulo: "Alumnas", exacto: false },
  { a: "/coach/agenda", rotulo: "Agenda", exacto: false },
  { a: "/coach/finanzas", rotulo: "Finanzas", exacto: false },
];

export function MarcoCoach() {
  const { abierto, setAbierto } = useBuscador();
  const [menu, setMenu] = useState(false);
  const [cuenta, setCuenta] = useState(false);
  const [logoRoto, setLogoRoto] = useState(false);
  const [retratoRoto, setRetratoRoto] = useState(false);
  const version = usarVersionDeMarca();
  const actor = actorGuardado();
  const nombre = actor?.nombre ?? coach.nombre;

  // Al subir una imagen se vuelve a intentar: si antes falló por no existir, ahora existe.
  useEffect(() => {
    setLogoRoto(false);
    setRetratoRoto(false);
  }, [version]);
  const marca = actor?.marca ?? coach.marca;
  const { pathname } = useLocation();
  // El menú de teléfono se cierra al navegar; si no, queda tapando la pantalla nueva.
  useEffect(() => setMenu(false), [pathname]);

  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-30 border-b border-linea bg-fondo/90 backdrop-blur">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center gap-4 px-5 sm:px-6">
          <div className="flex items-center gap-2">
            {/* El logo se pide siempre; si no hay, `onError` deja las iniciales. La clave
                lleva la versión: al subir uno nuevo el elemento se remonta y se vuelve a
                intentar, en vez de quedarse con las iniciales para siempre. */}
            {logoRoto ? (
              <span className="grid size-6 place-items-center rounded-marco border border-linea-fuerte text-[10px] font-bold">
                {iniciales(marca)}
              </span>
            ) : (
              <img
                key={version}
                src={urlDeLogo(version)}
                alt=""
                onError={() => setLogoRoto(true)}
                className="size-6 rounded-marco border border-linea object-cover"
              />
            )}
            <span className="text-menor font-semibold tracking-[-0.01em]">{marca}</span>
          </div>

          {/* Escritorio: secciones en la barra */}
          <nav aria-label="Secciones" className="ml-4 hidden items-center gap-6 lg:flex">
            {SECCIONES.map((s) => (
              <NavLink
                key={s.a}
                to={s.a}
                end={s.exacto}
                className={({ isActive }) =>
                  cn(
                    "border-b-2 py-5 text-menor font-medium transition-colors",
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

          <div className="ml-auto hidden flex-1 justify-end lg:flex">
            <DisparadorBuscador onClick={() => setAbierto(true)} />
          </div>

          {/* Su retrato, el de la presentación. Si todavía no sube ninguno, sus iniciales
              —las suyas de verdad, no las de los datos de ejemplo—. */}
          <MenuDeCuenta abierto={cuenta} onCerrar={() => setCuenta(false)}>
            <button
              type="button"
              onClick={() => setCuenta((v) => !v)}
              aria-expanded={cuenta}
              aria-haspopup="menu"
              title={`${nombre} · tu cuenta`}
              aria-label={`${nombre}. Tu cuenta`}
              className="grid size-8 shrink-0 place-items-center overflow-hidden rounded-full border border-linea-fuerte text-micro font-semibold transition-colors hover:bg-fondo-sutil"
            >
              {retratoRoto ? (
                iniciales(nombre)
              ) : (
                <img
                  key={version}
                  src={urlDeFotoDeCoach(version)}
                  alt=""
                  onError={() => setRetratoRoto(true)}
                  className="size-full object-cover"
                />
              )}
            </button>
          </MenuDeCuenta>

          {/* Teléfono: hamburguesa */}
          <button
            onClick={() => setMenu((v) => !v)}
            aria-expanded={menu}
            aria-label={menu ? "Cerrar menú" : "Abrir menú"}
            className="grid size-9 place-items-center rounded-marco border border-linea lg:hidden"
          >
            {menu ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
        </div>

        {menu ? (
          <div className="border-t border-linea px-5 pb-4 lg:hidden">
            <div className="py-3">
              <DisparadorBuscador
                onClick={() => {
                  setMenu(false);
                  setAbierto(true);
                }}
              />
            </div>
            <nav aria-label="Secciones" className="flex flex-col">
              {[...SECCIONES, { a: "/coach/ajustes", rotulo: "Ajustes", exacto: false }].map((s) => (
                <NavLink
                  key={s.a}
                  to={s.a}
                  end={s.exacto}
                  className={({ isActive }) =>
                    cn(
                      "border-l-2 py-3 pl-3 text-cuerpo font-medium transition-colors",
                      isActive ? "border-acento text-tinta" : "border-transparent text-tinta-media",
                    )
                  }
                >
                  {s.rotulo}
                </NavLink>
              ))}
            </nav>
          </div>
        ) : null}
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-5 pt-8 pb-16 sm:px-6">
        <Limite clave={pathname}>
          <Outlet />
        </Limite>
      </main>

      <Buscador abierto={abierto} onCerrar={() => setAbierto(false)} />
    </div>
  );
}
