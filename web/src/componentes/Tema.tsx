/** Selector de tema. La lógica vive en `lib/tema.tsx`; esto solo la enseña. */

import { Monitor, Moon, Sun } from "lucide-react";

import { useIdioma } from "@/lib/idioma";
import type { Tema } from "@/lib/tema";
import { useTema } from "@/lib/tema";
import { cn } from "@/lib/utils";

const OPCIONES: { id: Tema; rotulo: string; Icono: typeof Sun }[] = [
  { id: "claro", rotulo: "Claro", Icono: Sun },
  { id: "oscuro", rotulo: "Oscuro", Icono: Moon },
  { id: "sistema", rotulo: "Como el sistema", Icono: Monitor },
];

export function InterruptorDeTema({ className }: { className?: string }) {
  const { t } = useIdioma();
  const { tema, fijar } = useTema();

  return (
    <div
      role="radiogroup"
      aria-label={t("Tema de la interfaz")}
      className={cn("flex items-center gap-0.5 rounded-marco border border-linea p-0.5", className)}
    >
      {OPCIONES.map(({ id, rotulo, Icono }) => (
        <button
          key={id}
          role="radio"
          aria-checked={tema === id}
          title={t(rotulo)}
          aria-label={t(rotulo)}
          onClick={() => fijar(id)}
          className={cn(
            "grid size-7 place-items-center rounded-[calc(var(--radio)-1px)] transition-colors",
            tema === id ? "bg-fondo-sutil text-tinta" : "text-tinta-suave hover:text-tinta",
          )}
        >
          <Icono className="size-3.5" strokeWidth={1.8} />
        </button>
      ))}
    </div>
  );
}
