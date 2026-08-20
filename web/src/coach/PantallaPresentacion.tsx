/** La presentación de la coach, en su propia pantalla. */

import { Eye } from "lucide-react";
import { Presentacion } from "@/coach/Presentacion";
import { Etiqueta, Portada } from "@/componentes/primitivas";

export function PantallaPresentacion() {
  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta icono={Eye}>Lo primero que ve una alumna nueva</Etiqueta>
        <Portada>Tu presentación</Portada>
      </header>

      <Presentacion />
    </div>
  );
}
