/** Las preguntas que contesta cada alumna nueva, después de leer la presentación. */

import { Preguntas } from "@/coach/Presentacion";
import { Etiqueta, Portada } from "@/componentes/primitivas";

export function CuestionarioInicial() {
  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta>Alta de alumnas</Etiqueta>
        <Portada>Cuestionario inicial</Portada>
      </header>

      <Preguntas />
    </div>
  );
}
