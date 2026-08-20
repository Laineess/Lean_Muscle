/** Derechos ARCO que ejercen sus alumnas.
 *
 *  La coach es la Responsable frente a la LFPDPPP: el plazo le corre a ella, 20 días
 *  hábiles para contestar y 15 más para ejecutar. Por eso lo primero es lo que vence antes.
 */

import { Scale } from "lucide-react";
import { useState } from "react";

import { Apoyo, Aviso, Boton, Campo, Chip, Titulo, Vacio } from "@/componentes/primitivas";
import { ErrorApi, api, type SolicitudArcoApi } from "@/lib/api";
import { fecha } from "@/lib/formato";
import { usarApi } from "@/lib/usarApi";

const ESTADO: Record<SolicitudArcoApi["estado"], string> = {
  recibida: "Sin contestar",
  respondida: "Contestada, falta ejecutarla",
  resuelta: "Resuelta",
};

export function Arco() {
  const carga = usarApi<SolicitudArcoApi[]>((s) => api.coach.arco(s), []);
  const [abierta, setAbierta] = useState<string | null>(null);
  const [respuesta, setRespuesta] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);

  const filas = carga.datos ?? [];

  async function correr(accion: () => Promise<unknown>) {
    setFallo(null);
    setOcupado(true);
    try {
      await accion();
      setAbierta(null);
      setRespuesta("");
      carga.recargar();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo guardar.");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <Titulo icono={Scale}>Derechos de tus alumnas</Titulo>
        <Apoyo>
          Acceso, rectificación, cancelación y oposición. Tienes 20 días hábiles para
          contestar y 15 más para ejecutar lo que prometas.
        </Apoyo>
      </div>

      {fallo ? <Aviso tono="error">{fallo}</Aviso> : null}

      {carga.cargando ? null : filas.length === 0 ? (
        <Vacio>Ninguna alumna ha ejercido sus derechos.</Vacio>
      ) : (
        <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
          {filas.map((s) => (
            <li key={s.ulid} className="flex flex-col gap-2 py-4">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="text-menor font-medium">
                    {s.rotulo} · {s.alumna ?? "una alumna"}
                  </span>
                  <span className="text-micro text-tinta-suave">
                    {ESTADO[s.estado]} · recibida el {fecha(s.recibidaEn)}
                    {s.venceEl ? ` · vence el ${fecha(s.venceEl)}` : ""}
                  </span>
                </span>
                {s.estado === "resuelta" ? (
                  <Chip tono="exito">Resuelta</Chip>
                ) : (s.diasRestantes ?? 0) < 0 ? (
                  <Chip tono="error">Fuera de plazo</Chip>
                ) : (
                  <Chip tono={(s.diasRestantes ?? 99) <= 5 ? "espera" : "neutro"}>
                    {s.diasRestantes} días
                  </Chip>
                )}
              </div>

              {s.detalle ? <p className="medida text-menor text-tinta-media">{s.detalle}</p> : null}
              {s.respuesta ? (
                <p className="medida border-l-2 border-l-acento pl-3 text-menor text-tinta-media">
                  {s.respuesta}
                </p>
              ) : null}

              {abierta === s.ulid ? (
                <div className="flex flex-col gap-2">
                  <Campo id={`ar-${s.ulid}`} etiqueta="Tu respuesta">
                    <textarea
                      id={`ar-${s.ulid}`}
                      rows={3}
                      value={respuesta}
                      onChange={(e) => setRespuesta(e.target.value)}
                      placeholder="Qué le contestas y qué vas a hacer."
                      className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
                    />
                  </Campo>
                  <div className="flex flex-wrap gap-2">
                    <Boton
                      medida="chica"
                      disabled={ocupado || !respuesta.trim()}
                      onClick={() => void correr(() => api.coach.responderArco(s.ulid, respuesta))}
                    >
                      Guardar respuesta
                    </Boton>
                    <Boton tono="contorno" medida="chica" onClick={() => setAbierta(null)}>
                      Cancelar
                    </Boton>
                  </div>
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {s.estado === "recibida" ? (
                    <Boton
                      tono="contorno"
                      medida="chica"
                      onClick={() => {
                        setAbierta(s.ulid);
                        setRespuesta("");
                      }}
                    >
                      Contestar
                    </Boton>
                  ) : null}
                  {s.estado === "respondida" ? (
                    <Boton
                      tono="contorno"
                      medida="chica"
                      disabled={ocupado}
                      onClick={() => void correr(() => api.coach.resolverArco(s.ulid))}
                    >
                      Marcar como resuelta
                    </Boton>
                  ) : null}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
