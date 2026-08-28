/** Las preguntas que contesta cada alumna nueva, después de leer la presentación. */

import { UserPlus } from "lucide-react";
import { Preguntas } from "@/coach/Presentacion";
import { Etiqueta, Portada } from "@/componentes/primitivas";
import { useIdioma } from "@/lib/idioma";

export function CuestionarioInicial() {
  const { t } = useIdioma();
  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta icono={UserPlus}>{t("Alta de alumnas")}</Etiqueta>
        <Portada>{t("Cuestionario inicial")}</Portada>
      </header>

      <Preguntas />
    </div>
  );
}
