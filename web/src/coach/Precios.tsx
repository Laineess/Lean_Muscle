/** Planes y precios: lo que la coach vende y lo que cobra suelto.
 *
 *  Los dos juntos porque la pregunta que responden es la misma —cuánto cuesta— aunque sean
 *  cosas distintas: el plan es una suscripción con duración, el servicio es un cargo puntual.
 */

import { Tag } from "lucide-react";
import { Planes } from "@/coach/Planes";
import { Servicios } from "@/coach/Servicios";
import { Etiqueta, Portada, Regla } from "@/componentes/primitivas";
import { useIdioma } from "@/lib/idioma";

export function Precios() {
  const { t } = useIdioma();
  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta icono={Tag}>{t("Tu negocio")}</Etiqueta>
        <Portada>{t("Planes y precios")}</Portada>
      </header>

      <Planes />

      <Regla />

      <Servicios />
    </div>
  );
}
