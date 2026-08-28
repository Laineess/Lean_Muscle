/** Marco del panel de coach: barra superior en escritorio, hamburguesa en teléfono.
 *
 *  Mismo sistema visual que la app de la alumna. El buscador global resuelve la densidad:
 *  con 60 alumnas no se recorre una lista, se busca.
 */

import { CalendarDays, LayoutDashboard, Menu, Settings, Users, Wallet, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { Limite } from "@/componentes/Limite";
import { Buscador, DisparadorBuscador } from "@/coach/Buscador";
import { BotonDeIdioma } from "@/componentes/Idioma";
import { useBuscador } from "@/lib/usarBuscador";
import { MenuDeCuenta } from "@/coach/MenuDeCuenta";
import { urlDeFotoDeCoach, urlDeLogo } from "@/lib/api";
import { useIdioma } from "@/lib/idioma";
import { usarVersionDeMarca } from "@/lib/marca";
import { coach } from "@/lib/datos";
import { actorGuardado } from "@/lib/sesion";
import { iniciales } from "@/lib/formato";
import { cn } from "@/lib/utils";

interface Seccion {
  a: string;
  rotulo: string;
  exacto: boolean;
  Icono: LucideIcon;
}

const SECCIONES: Seccion[] = [
  { a: "/coach", rotulo: "Panel", exacto: true, Icono: LayoutDashboard },
  { a: "/coach/alumnas", rotulo: "Pacientes", exacto: false, Icono: Users },
  { a: "/coach/agenda", rotulo: "Agenda", exacto: false, Icono: CalendarDays },
  { a: "/coach/finanzas", rotulo: "Finanzas", exacto: false, Icono: Wallet },
];

/** En escritorio Ajustes vive en el menú del avatar; en teléfono no hay avatar desplegable,
 *  así que se cuela al final de la hamburguesa. */
const AJUSTES: Seccion = {
  a: "/coach/ajustes",
  rotulo: "Ajustes",
  exacto: false,
  Icono: Settings,
};

export function MarcoCoach() {
  const { abierto, setAbierto } = useBuscador();
  const { t } = useIdioma();
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
                    "flex items-center gap-2 border-b-2 py-5 text-menor font-medium",
                    "rounded-marco px-2 transition-[background-color,box-shadow,color] duration-[var(--mov-rapido)] ease-suave",
                    isActive
                      ? "border-acento bg-fondo-sutil text-tinta shadow-[0_0_14px_2px_rgba(12,12,12,0.08)] dark:shadow-[0_0_14px_2px_rgba(255,255,255,0.18)]"
                      : "border-transparent text-tinta-suave hover:bg-fondo-sutil hover:text-tinta hover:shadow-[0_0_12px_1px_rgba(12,12,12,0.06)] dark:hover:shadow-[0_0_12px_1px_rgba(255,255,255,0.12)]",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {/* El trazo engorda en la sección activa: el dorado del filete ya marca
                        dónde estás, y el icono lo acompaña sin meter otro color. */}
                    <s.Icono
                      aria-hidden
                      className="size-4 shrink-0"
                      strokeWidth={isActive ? 2.2 : 1.6}
                    />
                    {t(s.rotulo)}
                  </>
                )}
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
              title={t("{nombre} · tu cuenta", { nombre })}
              aria-label={t("{nombre}. Tu cuenta", { nombre })}
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
            aria-label={menu ? t("Cerrar menú") : t("Abrir menú")}
            className="hunde grid size-9 place-items-center rounded-marco border border-linea transition-colors duration-[var(--mov-rapido)] ease-suave hover:border-tinta lg:hidden"
          >
            {/* Las dos aspas viven encima una de otra y se cruzan girando: así el botón
                acusa el toque aunque el panel tarde en pintarse. */}
            <span aria-hidden className="relative grid size-4 place-items-center">
              <Menu
                className={cn(
                  "absolute size-4 transition-all duration-[var(--mov-normal)] ease-salida",
                  menu ? "rotate-90 scale-75 opacity-0" : "rotate-0 scale-100 opacity-100",
                )}
              />
              <X
                className={cn(
                  "absolute size-4 transition-all duration-[var(--mov-normal)] ease-salida",
                  menu ? "rotate-0 scale-100 opacity-100" : "-rotate-90 scale-75 opacity-0",
                )}
              />
            </span>
          </button>
        </div>

        {menu ? (
          <div className="despliega border-t border-linea lg:hidden">
            <div>
              <div className="px-5 pb-4">
                <div className="py-3">
                  <DisparadorBuscador
                    onClick={() => {
                      setMenu(false);
                      setAbierto(true);
                    }}
                  />
                </div>
                <nav aria-label="Secciones" className="escalona flex flex-col">
                  {[...SECCIONES, AJUSTES].map((s) => (
                    <NavLink
                      key={s.a}
                      to={s.a}
                      end={s.exacto}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-3 border-l-2 py-3 pl-3 text-cuerpo font-medium",
                          "rounded-marco transition-[background-color,box-shadow,color] duration-[var(--mov-rapido)] ease-suave",
                          isActive
                            ? "border-acento bg-fondo-sutil text-tinta shadow-[0_0_14px_2px_rgba(12,12,12,0.08)] dark:shadow-[0_0_14px_2px_rgba(255,255,255,0.18)]"
                            : "border-transparent text-tinta-media hover:bg-fondo-sutil hover:text-tinta hover:shadow-[0_0_12px_1px_rgba(12,12,12,0.06)] dark:hover:shadow-[0_0_12px_1px_rgba(255,255,255,0.12)]",
                        )
                      }
                    >
                      {({ isActive }) => (
                        <>
                          <s.Icono
                            aria-hidden
                            className="size-4 shrink-0"
                            strokeWidth={isActive ? 2.2 : 1.6}
                          />
                          {t(s.rotulo)}
                        </>
                      )}
                    </NavLink>
                  ))}
                </nav>
                <div className="mt-3 border-t border-linea pt-3">
                  <BotonDeIdioma />
                </div>
              </div>
            </div>
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
