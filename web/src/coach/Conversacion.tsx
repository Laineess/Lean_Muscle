/** El hilo de una alumna, desde el panel de la coach. Abrirlo marca como leídos sus
 *  mensajes.
 */

import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { Hilo } from "@/componentes/Hilo";
import { Apoyo, Boton, Etiqueta, Portada } from "@/componentes/primitivas";
import { api } from "@/lib/api";
import { usarApi } from "@/lib/usarApi";
import type { FilaCarteraApi } from "@/lib/api";

export function Conversacion() {
  const { alumnaUlid = "" } = useParams();

  // La cartera ya está en caché del navegador la mayoría de las veces; se pide para tener el
  // nombre sin inventarlo a partir del ULID.
  const { datos: cartera } = usarApi<FilaCarteraApi[]>((senal) => api.coach.alumnas(senal), []);
  const alumna = cartera?.find((a) => a.ulid === alumnaUlid);

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <Boton asChild tono="discreto" medida="icono" aria-label="Regresar">
            <Link to="/coach/alumnas">
              <ArrowLeft className="size-4" />
            </Link>
          </Boton>
          <Etiqueta>Conversación</Etiqueta>
        </div>
        <Portada>{alumna?.nombre ?? "Mensajes"}</Portada>
        <Apoyo className="medida">
          Todo lo que se han dicho, en orden. Lo que escribas aquí lo lee ella tal cual.
        </Apoyo>
      </header>

      <Hilo
        yo="coach"
        contraparte={alumna?.nombre.split(" ")[0] ?? "tu alumna"}
        cargar={(senal) => api.coach.mensajes(alumnaUlid, senal)}
        enviar={(cuerpo) => api.coach.responder(alumnaUlid, cuerpo)}
      />
    </div>
  );
}
