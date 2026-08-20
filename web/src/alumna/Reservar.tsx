/** La alumna reserva su consulta.
 *
 *  Solo se le enseñan huecos libres, agrupados por día en su propia hora. Elegir uno lo
 *  agenda en firme; si a su coach le estorba, ella lo reagenda desde su calendario.
 */

import { ArrowLeft, Check } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Dialogo } from "@/componentes/Dialogo";
import { CargandoPantalla } from "@/componentes/Estado";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Chip,
  Etiqueta,
  Portada,
  Selector,
  Titulo,
  Vacio,
} from "@/componentes/primitivas";
import { ErrorApi, api, type CitaDeAlumnaApi, type HuecoApi } from "@/lib/api";
import { diaSemana, horaLocal } from "@/lib/formato";
import { usarApi } from "@/lib/usarApi";

const MODALIDADES: [string, string][] = [
  ["video", "Por video"],
  ["telefono", "Por teléfono"],
  ["presencial", "En persona"],
];

const ROTULO = Object.fromEntries(MODALIDADES) as Record<string, string>;

/** Día calendario en la zona del navegador: agrupar por el ISO en UTC parte los días. */
function diaLocal(iso: string): string {
  return new Date(iso).toLocaleDateString("en-CA");
}

function porDia(huecos: HuecoApi[]): [string, HuecoApi[]][] {
  const dias = new Map<string, HuecoApi[]>();
  for (const h of huecos) {
    const clave = diaLocal(h.iniciaEn);
    dias.set(clave, [...(dias.get(clave) ?? []), h]);
  }
  return [...dias.entries()];
}

export function Reservar() {
  const carga = usarApi<HuecoApi[]>((s) => api.alumna.huecos(s));
  const [elegido, setElegido] = useState<HuecoApi | null>(null);
  const [modalidad, setModalidad] = useState("video");
  const [ocupado, setOcupado] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);
  const [reservada, setReservada] = useState<CitaDeAlumnaApi | null>(null);

  async function reservar() {
    if (!elegido) return;
    setFallo(null);
    setOcupado(true);
    try {
      setReservada(await api.alumna.reservar(elegido.iniciaEn, modalidad));
      setElegido(null);
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo reservar.");
      // Si alguien se le adelantó, la lista que está viendo ya no es la de verdad.
      setElegido(null);
      carga.recargar();
    } finally {
      setOcupado(false);
    }
  }

  if (reservada) return <Confirmada cita={reservada} />;
  if (carga.cargando) return <CargandoPantalla que="los horarios libres" filas={4} />;

  const dias = porDia(carga.datos ?? []);

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <Etiqueta>Con tu coach</Etiqueta>
        <Portada>Reserva tu consulta</Portada>
        <Apoyo>Elige la hora que te acomode. Queda agendada al momento.</Apoyo>
      </header>

      {fallo ? <Aviso tono="error">{fallo}</Aviso> : null}

      {carga.error ? (
        <Vacio>{carga.error.message}</Vacio>
      ) : dias.length === 0 ? (
        <Vacio>
          Ahora mismo no hay horarios libres. Tu coach abre más conforme se acerquen las
          fechas.
        </Vacio>
      ) : (
        <div className="flex flex-col gap-8">
          {dias.map(([clave, huecos]) => (
            <section key={clave} className="flex flex-col gap-3">
              <Titulo className="capitalize">{diaSemana(huecos[0]!.iniciaEn)}</Titulo>
              <ul className="flex flex-wrap gap-2">
                {huecos.map((h) => (
                  <li key={h.iniciaEn}>
                    <Boton
                      tono="contorno"
                      onClick={() => {
                        setFallo(null);
                        setElegido(h);
                      }}
                    >
                      <span className="cifra">{horaLocal(h.iniciaEn)}</span>
                    </Boton>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}

      <div>
        <Boton asChild tono="discreto">
          <Link to="/inicio">
            <ArrowLeft className="size-4" /> Volver a inicio
          </Link>
        </Boton>
      </div>

      {elegido ? (
        <Dialogo
          abierto
          onCambio={(v) => !v && setElegido(null)}
          etiqueta="Confirma tu consulta"
          titulo={`${diaSemana(elegido.iniciaEn)}, ${horaLocal(elegido.iniciaEn)}`}
          pie={
            <>
              <Boton tono="contorno" medida="chica" onClick={() => setElegido(null)}>
                Cancelar
              </Boton>
              <Boton medida="chica" disabled={ocupado} onClick={() => void reservar()}>
                Reservar
              </Boton>
            </>
          }
        >
          <Apoyo>
            Termina a las {horaLocal(elegido.terminaEn)}. Las horas están en tu zona horaria.
          </Apoyo>

          <Campo id="rs-modalidad" etiqueta="Cómo prefieres la consulta">
            <Selector
              id="rs-modalidad"
              value={modalidad}
              onChange={(e) => setModalidad(e.target.value)}
            >
              {MODALIDADES.map(([valor, rotulo]) => (
                <option key={valor} value={valor}>
                  {rotulo}
                </option>
              ))}
            </Selector>
          </Campo>

          <Etiqueta>Si te surge algo, escríbele a tu coach para moverla.</Etiqueta>
        </Dialogo>
      ) : null}
    </div>
  );
}

function Confirmada({ cita }: { cita: CitaDeAlumnaApi }) {
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-3">
        <Etiqueta>Listo</Etiqueta>
        <Portada>Tu consulta quedó agendada</Portada>
      </header>

      <Aviso tono="exito" titulo={`${diaSemana(cita.iniciaEn)}, ${horaLocal(cita.iniciaEn)}`}>
        <span className="flex items-center gap-2">
          <Check className="size-4" /> {ROTULO[cita.modalidad] ?? cita.modalidad} · termina a las{" "}
          {horaLocal(cita.terminaEn)}
        </span>
      </Aviso>

      <div className="flex flex-wrap items-center gap-3">
        <Boton asChild>
          <Link to="/inicio">Ir a mi inicio</Link>
        </Boton>
        <Chip>Te llega el recordatorio un día antes</Chip>
      </div>
    </div>
  );
}
