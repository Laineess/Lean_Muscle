/** Buscador global de la coach: cualquier alumna o sección en dos teclas, con ⌘K o Ctrl+K.
 *
 *  Es lo que permite mantener el panel espacioso en vez de apretarlo hasta volverlo una
 *  hoja de cálculo.
 */

import { Command } from "cmdk";
import { Search } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { cartera } from "@/lib/datos";
import { fecha } from "@/lib/formato";
import { ROTULO_ESTADO } from "@/lib/tipos";

const SECCIONES = [
  { rotulo: "Panel", a: "/coach" },
  { rotulo: "Alumnas", a: "/coach/alumnas" },
  { rotulo: "Agenda", a: "/coach/agenda" },
  { rotulo: "Finanzas", a: "/coach/finanzas" },
  { rotulo: "Ajustes y seguridad", a: "/coach/ajustes" },
];

export function DisparadorBuscador({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex h-9 w-full max-w-xs items-center gap-2 rounded-marco border border-linea px-3 text-menor text-tinta-suave transition-colors hover:border-tinta hover:text-tinta"
    >
      <Search className="size-4 shrink-0" strokeWidth={1.6} />
      <span className="truncate">Buscar alumna o sección…</span>
      <kbd className="ml-auto hidden shrink-0 rounded border border-linea px-1.5 py-0.5 text-micro font-medium lg:inline">
        ⌘K
      </kbd>
    </button>
  );
}

export function Buscador({ abierto, onCerrar }: { abierto: boolean; onCerrar: () => void }) {
  const navegar = useNavigate();

  const ir = (a: string) => {
    void navegar(a);
    onCerrar();
  };

  return (
    <Command.Dialog
      open={abierto}
      onOpenChange={(v) => !v && onCerrar()}
      label="Buscador"
      className="fixed inset-0 z-50 grid place-items-start justify-items-center bg-tinta/40 pt-[12vh] backdrop-blur-sm"
    >
      <div className="w-[min(92vw,36rem)] overflow-hidden rounded-marco border border-linea bg-fondo-elevado">
        <div className="flex items-center gap-3 border-b border-linea px-4">
          <Search className="size-4 shrink-0 text-tinta-suave" strokeWidth={1.6} />
          <Command.Input
            autoFocus
            placeholder="Busca una alumna, un chequeo o una sección…"
            className="h-12 w-full bg-transparent text-cuerpo outline-none placeholder:text-tinta-suave"
          />
        </div>

        <Command.List className="max-h-[min(60vh,24rem)] overflow-y-auto p-2">
          <Command.Empty className="px-3 py-8 text-center text-menor text-tinta-suave">
            Nada con ese nombre.
          </Command.Empty>

          <Command.Group
            heading="Alumnas"
            className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-2 [&_[cmdk-group-heading]]:text-micro [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.1em] [&_[cmdk-group-heading]]:text-tinta-suave"
          >
            {cartera.map((a) => (
              <Command.Item
                key={a.ulid}
                value={`${a.nombre} ${(a.plan ?? "sin plan")} ciclo ${a.ciclo}`}
                onSelect={() => ir(`/coach/alumnas?a=${a.ulid}`)}
                className="flex cursor-pointer items-center justify-between gap-3 rounded-marco px-3 py-2.5 text-menor data-[selected=true]:bg-fondo-sutil"
              >
                <span className="flex flex-col">
                  <span className="font-medium">{a.nombre}</span>
                  <span className="text-micro text-tinta-suave">
                    Ciclo {a.ciclo} · {(a.plan ?? "sin plan")}
                    {a.chequeoFecha ? ` · chequeo ${fecha(a.chequeoFecha)}` : ""}
                  </span>
                </span>
                {a.chequeoEstado ? (
                  <span className="shrink-0 text-micro text-tinta-suave">
                    {ROTULO_ESTADO[a.chequeoEstado]}
                  </span>
                ) : null}
              </Command.Item>
            ))}
          </Command.Group>

          <Command.Group
            heading="Ir a"
            className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-2 [&_[cmdk-group-heading]]:text-micro [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.1em] [&_[cmdk-group-heading]]:text-tinta-suave"
          >
            {SECCIONES.map((s) => (
              <Command.Item
                key={s.a}
                value={s.rotulo}
                onSelect={() => ir(s.a)}
                className="cursor-pointer rounded-marco px-3 py-2.5 text-menor data-[selected=true]:bg-fondo-sutil"
              >
                {s.rotulo}
              </Command.Item>
            ))}
          </Command.Group>
        </Command.List>
      </div>
    </Command.Dialog>
  );
}
