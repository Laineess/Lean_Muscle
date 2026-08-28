/** Marco de la app de alumna: tres pestañas, no cinco.
 *
 *  Cuenta, mensajes y avisos viven dentro de Inicio. En teléfono la barra va abajo, al
 *  alcance del pulgar; en escritorio sube.
 */

import { Bell, Dumbbell, House, LineChart, Menu, MessageSquare, ShieldCheck, Sun, User, X } from "lucide-react";
import { useEffect, useRef, useState, type ComponentType } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { Limite } from "@/componentes/Limite";
import { BotonDeIdioma } from "@/componentes/Idioma";
import { BotonSalir } from "@/componentes/Seguridad";
import { urlDeLogo } from "@/lib/api";
import { iniciales } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
import { actorGuardado } from "@/lib/sesion";
import { cn } from "@/lib/utils";

interface Pestana {
  a: string;
  rotulo: string;
  Icono: ComponentType<{ className?: string; strokeWidth?: number }>;
}

const PESTANAS: Pestana[] = [
  { a: "/inicio", rotulo: "Inicio", Icono: Sun },
  // Pesa y no lista de tareas: su plan es entrenamiento y comida, no pendientes que se tachan.
  { a: "/plan", rotulo: "Mi plan", Icono: Dumbbell },
  { a: "/evolucion", rotulo: "Evolución", Icono: LineChart },
];

export function MarcoAlumna() {
  // La alumna ve la marca de su coach, no la de la plataforma: la relación es con ella.
  const actor = actorGuardado();
  const { t } = useIdioma();
  const marca = actor?.marca ?? "MyFittPlan";
  const nombre = actor?.nombre ?? "Paciente";
  const [logoRoto, setLogoRoto] = useState(false);
  const [opciones, setOpciones] = useState(false);
  const { pathname } = useLocation();
  const cajaOpciones = useRef<HTMLDivElement>(null);

  useEffect(() => setOpciones(false), [pathname]);

  useEffect(() => {
    if (!opciones) return;

    const fuera = (e: MouseEvent) => {
      if (cajaOpciones.current && !cajaOpciones.current.contains(e.target as Node)) {
        setOpciones(false);
      }
    };
    const escape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpciones(false);
    };

    document.addEventListener("mousedown", fuera);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", fuera);
      document.removeEventListener("keydown", escape);
    };
  }, [opciones]);

  return (
    <div className="flex min-h-full flex-col">
      {/* Escritorio: la navegación sube y se vuelve discreta. */}
      <header className="sticky top-0 z-20 border-b border-linea bg-fondo/85 backdrop-blur">
        <nav
          aria-label="Secciones"
          className="mx-auto flex h-16 w-full max-w-5xl items-center gap-4 px-5 sm:gap-8 sm:px-6"
        >
          {/* El logo de su coach, si lo subió. La alumna ve su marca, no la nuestra. */}
          {logoRoto ? null : (
            <img
              src={urlDeLogo()}
              alt=""
              onError={() => setLogoRoto(true)}
              className="size-6 rounded-marco border border-linea object-cover"
            />
          )}
          <span className="text-menor font-semibold tracking-[-0.01em]">{marca}</span>
          <div className="hidden items-center gap-6 sm:flex">
            {PESTANAS.map(({ a, rotulo, Icono }) => (
              <NavLink
                key={a}
                to={a}
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
                    <Icono aria-hidden className="size-4 shrink-0" strokeWidth={isActive ? 2.2 : 1.6} />
                    {t(rotulo)}
                  </>
                )}
              </NavLink>
            ))}
          </div>

          <div ref={cajaOpciones} className="relative ml-auto flex items-center gap-2">
            <button
              type="button"
              onClick={() => setOpciones((v) => !v)}
              aria-expanded={opciones}
              aria-haspopup="menu"
              aria-label={t("Abrir menú de opciones")}
              className="grid size-9 place-items-center rounded-marco border border-linea transition-colors hover:border-tinta hover:bg-fondo-sutil sm:hidden"
            >
              {opciones ? <X aria-hidden className="size-4" /> : <Menu aria-hidden className="size-4" />}
            </button>
            <button
              type="button"
              onClick={() => setOpciones((v) => !v)}
              aria-expanded={opciones}
              aria-haspopup="menu"
              aria-label={t("{nombre}. Abrir menú de opciones", { nombre })}
              title={t("{nombre} · opciones", { nombre })}
              className="grid size-9 shrink-0 place-items-center rounded-full border border-linea-fuerte text-micro font-semibold transition-colors hover:bg-fondo-sutil"
            >
              {iniciales(nombre)}
            </button>

            {opciones ? (
              <MenuDeOpcionesPaciente />
            ) : null}
          </div>
        </nav>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-5 pt-8 pb-28 sm:px-6 sm:pb-16">
        <Limite clave={pathname}>
          <Outlet />
        </Limite>
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
                    "mx-1 flex h-16 flex-col items-center justify-center gap-1 rounded-marco text-micro font-medium transition-[background-color,box-shadow,color] duration-[var(--mov-rapido)] ease-suave",
                    isActive
                      ? "bg-fondo-sutil text-tinta shadow-[0_0_14px_2px_rgba(12,12,12,0.08)] dark:shadow-[0_0_14px_2px_rgba(255,255,255,0.18)]"
                      : "text-tinta-suave hover:bg-fondo-sutil hover:text-tinta hover:shadow-[0_0_12px_1px_rgba(12,12,12,0.06)] dark:hover:shadow-[0_0_12px_1px_rgba(255,255,255,0.12)]",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <Icono
                      aria-hidden
                      className={cn(
                        "size-5 transition-transform duration-[var(--mov-normal)] ease-salida",
                        isActive && "-translate-y-0.5",
                      )}
                      strokeWidth={isActive ? 2.2 : 1.6}
                    />
                    <span>{t(rotulo)}</span>
                    {/* El dorado marca dónde estás; no lleva texto encima. Crece desde el
                        centro al llegar, en vez de encenderse de golpe. */}
                    <span
                      className={cn(
                        "h-0.5 w-6 rounded-full bg-acento transition-transform",
                        "duration-[var(--mov-normal)] ease-salida",
                        isActive ? "scale-x-100" : "scale-x-0",
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

function MenuDeOpcionesPaciente() {
  const { t } = useIdioma();
  const opciones = [
    { ruta: "/inicio", rotulo: "Inicio", Icono: House },
    { ruta: "/mensajes", rotulo: "Mensajes", Icono: MessageSquare },
    { ruta: "/avisos", rotulo: "Avisos", Icono: Bell },
    { ruta: "/cuenta", rotulo: "Mi cuenta", Icono: User },
    { ruta: "/cuenta", rotulo: "Privacidad", Icono: ShieldCheck },
  ];

  return (
    <div
      role="menu"
      aria-label={t("Más opciones")}
      className="animate-emerge absolute right-0 top-full z-40 mt-2 w-[min(18rem,calc(100vw-2.5rem))] overflow-hidden rounded-marco border border-linea bg-fondo-elevado p-2 shadow-lg"
    >
      <nav className="flex flex-col" aria-label={t("Más opciones")}>
        {opciones.map(({ ruta, rotulo, Icono }) => (
          <Link
            key={rotulo}
            to={ruta}
            role="menuitem"
            className="flex items-center gap-3 rounded-marco px-3 py-2.5 text-menor transition-colors hover:bg-fondo-sutil"
          >
            <Icono aria-hidden className="size-4 text-tinta-suave" />
            {t(rotulo)}
          </Link>
        ))}
      </nav>
      <div className="mt-2 border-t border-linea pt-2">
        <BotonDeIdioma />
      </div>
      <div className="mt-2 border-t border-linea pt-2">
        <BotonSalir className="w-full justify-center" />
      </div>
    </div>
  );
}
