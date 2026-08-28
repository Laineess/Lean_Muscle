/** Botón de idioma para los menús: alterna entre español e inglés.
 *
 *  El rótulo muestra siempre el idioma al que cambia (no el actual): «English» cuando se
 *  habla español, «Español» cuando se habla inglés.
 */

import { Languages } from "lucide-react";

import { useIdioma } from "@/lib/idioma";
import { cn } from "@/lib/utils";

export function BotonDeIdioma({ className }: { className?: string }) {
  const { idioma, alternar, t } = useIdioma();
  const esEspanol = idioma === "es";

  return (
    <button
      type="button"
      onClick={alternar}
      title={esEspanol ? t("Traducir al inglés") : t("Volver al español")}
      aria-label={esEspanol ? t("Traducir al inglés") : t("Volver al español")}
      className={cn(
        "hunde flex items-center gap-3 rounded-marco px-3 py-2.5 text-menor transition-colors hover:bg-fondo-sutil",
        className,
      )}
    >
      <Languages aria-hidden className="size-4 shrink-0 text-tinta-suave" />
      {esEspanol ? "English" : "Español"}
    </button>
  );
}