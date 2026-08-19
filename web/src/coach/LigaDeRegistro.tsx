/** La liga por la que una alumna se registra sola, y su interruptor.
 *
 *  Vive en la cartera porque es la otra forma de sumar alumnas: o las da de alta ella, o
 *  llegan por aquí. Apagada, la liga responde que no está disponible; encendida, cualquiera
 *  que tenga la dirección puede empezar su solicitud.
 */

import { Check, Copy, Link2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Apoyo, Aviso, Boton, Chip, Titulo } from "@/componentes/primitivas";
import { ErrorApi, api, type RegistroDeCoachApi } from "@/lib/api";
import { num } from "@/lib/formato";
import { usarApi } from "@/lib/usarApi";

export function LigaDeRegistro() {
  const carga = usarApi<RegistroDeCoachApi>((s) => api.coach.registro(s));
  const [ocupado, setOcupado] = useState(false);
  const [copiada, setCopiada] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);

  const r = carga.datos;
  if (carga.cargando || !r) return null;

  const direccion = `${window.location.origin}${r.liga}`;

  async function cambiar(abierto: boolean) {
    setFallo(null);
    setOcupado(true);
    try {
      await api.coach.abrirRegistro(abierto);
      carga.recargar();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo cambiar.");
    } finally {
      setOcupado(false);
    }
  }

  async function copiar() {
    try {
      await navigator.clipboard.writeText(direccion);
      setCopiada(true);
      window.setTimeout(() => setCopiada(false), 2000);
    } catch {
      // Sin permiso de portapapeles la dirección sigue a la vista para copiarla a mano.
      setFallo("Copia la dirección a mano: el navegador no dio permiso.");
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <Titulo>Tu liga de registro</Titulo>
            {r.abierto ? <Chip tono="exito">Abierta</Chip> : <Chip>Apagada</Chip>}
            {r.solicitudesPendientes > 0 ? (
              <Link to="/coach/solicitudes" className="no-underline">
                <Chip tono="espera">
                  {r.solicitudesPendientes === 1
                    ? "1 solicitud esperando"
                    : `${r.solicitudesPendientes} solicitudes esperando`}
                </Chip>
              </Link>
            ) : null}
          </div>
          <Apoyo>
            Compártela y quien la abra empieza su registro sola. Queda como solicitud hasta
            que tú la aceptes, y no cuenta contra tu límite.
          </Apoyo>
        </div>

        <div className="flex items-center gap-2">
          <Boton asChild tono="discreto" medida="chica">
            <Link to="/coach/solicitudes">Ver solicitudes</Link>
          </Boton>
          <Boton
            tono={r.abierto ? "contorno" : "solido"}
            medida="chica"
            disabled={ocupado || (!r.abierto && !r.puedeEncenderse)}
            onClick={() => void cambiar(!r.abierto)}
          >
            {r.abierto ? "Apagar" : "Encender"}
          </Boton>
        </div>
      </div>

      {r.puedeEncenderse ? null : (
        <Aviso tono="atencion" titulo="Todavía no se puede encender">
          {r.motivo}
        </Aviso>
      )}

      {fallo ? <Aviso tono="error">{fallo}</Aviso> : null}

      <div className="flex flex-wrap items-center gap-3 rounded-marco border border-linea px-4 py-3">
        <Link2 className="size-4 shrink-0 text-tinta-suave" />
        <span className="min-w-0 flex-1 truncate text-menor">{direccion}</span>
        {r.precioInscripcion !== null ? (
          <span className="text-micro text-tinta-suave">
            inscripción ${num(r.precioInscripcion)}
          </span>
        ) : null}
        <Boton tono="contorno" medida="chica" onClick={() => void copiar()}>
          {copiada ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
          {copiada ? "Copiada" : "Copiar"}
        </Boton>
      </div>
    </section>
  );
}
