/** Mensajes con la coach. Fuera de las tres pestañas: es un hilo que se abre dos veces al
 *  mes, y gastar una pestaña en eso carga la navegación de todos los días.
 */

import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

import { Hilo } from "@/componentes/Hilo";
import { Apoyo, Boton, Etiqueta, Portada } from "@/componentes/primitivas";
import { api } from "@/lib/api";
import { actorGuardado } from "@/lib/sesion";

export function Mensajes() {
  const actor = actorGuardado();

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <Boton asChild tono="discreto" medida="icono" aria-label="Regresar">
            <Link to="/inicio">
              <ArrowLeft className="size-4" />
            </Link>
          </Boton>
          <Etiqueta>Conversación</Etiqueta>
        </div>
        <Portada>Tus mensajes</Portada>
        <Apoyo className="medida">
          Aquí queda todo lo que se han dicho, en orden. Abrir el hilo marca como leídos los
          mensajes de tu coach.
        </Apoyo>
      </header>

      <Hilo
        yo="alumna"
        contraparte={actor?.marca ?? "tu coach"}
        cargar={(senal) => api.alumna.mensajes(senal)}
        enviar={(cuerpo) => api.alumna.escribir(cuerpo)}
      />
    </div>
  );
}
