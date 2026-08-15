/** Planes y precios: lo que la coach vende y lo que cobra suelto.
 *
 *  Los dos juntos porque la pregunta que responden es la misma —cuánto cuesta— aunque sean
 *  cosas distintas: el plan es una suscripción con duración, el servicio es un cargo puntual.
 */

import { Planes } from "@/coach/Planes";
import { Servicios } from "@/coach/Servicios";
import { Etiqueta, Portada, Regla } from "@/componentes/primitivas";

export function Precios() {
  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta>Tu negocio</Etiqueta>
        <Portada>Planes y precios</Portada>
      </header>

      <Planes />

      <Regla />

      <Servicios />
    </div>
  );
}
