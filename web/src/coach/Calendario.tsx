/** La rejilla del calendario: horas a la izquierda, días arriba, citas encima.
 *
 *  No sabe nada de la API. Las citas que se solapan se reparten el ancho en columnas;
 *  apilarlas escondería justo lo que hay que ver.
 */

import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

export interface CitaEnRejilla {
  id: string;
  titulo: string;
  subtitulo?: string | null;
  /** ISO local `YYYY-MM-DDTHH:mm`. */
  iniciaEn: string;
  terminaEn: string;
  tono: "consulta" | "bloqueo" | "cancelada";
}

interface Props {
  /** Días que se pintan, en `YYYY-MM-DD`. Uno para la vista de día, siete para la semana. */
  dias: string[];
  citas: CitaEnRejilla[];
  /** Primera y última hora visibles. Fuera de ahí la coach no agenda. */
  desdeHora?: number;
  hastaHora?: number;
  onTocarHueco: (iso: string) => void;
  onTocarCita: (id: string) => void;
}

/** Alto de una hora. 56 px deja legible una cita de 30 minutos sin que la semana no quepa. */
const ALTO_HORA = 56;

/** A cuánto se redondea al tocar un hueco. Nadie agenda a las 9:07. */
const PASO_MIN = 15;

const DIAS_CORTOS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];

function minutosDe(iso: string): number {
  const [h, m] = iso.slice(11, 16).split(":").map(Number);
  return (h ?? 0) * 60 + (m ?? 0);
}

/** Reparte en columnas las citas que se tocan. El solape es transitivo: A con B y B con C
 *  mete a las tres en el mismo grupo, o C se pintaría encima de A.
 */
function repartir(citas: CitaEnRejilla[]): Map<string, { columna: number; de: number }> {
  const orden = [...citas].sort(
    (a, b) => minutosDe(a.iniciaEn) - minutosDe(b.iniciaEn) || minutosDe(b.terminaEn) - minutosDe(a.terminaEn),
  );

  const reparto = new Map<string, { columna: number; de: number }>();
  let grupo: CitaEnRejilla[] = [];
  let finDelGrupo = -1;

  const cerrar = () => {
    if (!grupo.length) return;
    const columnas: CitaEnRejilla[][] = [];
    for (const cita of grupo) {
      // Primera columna donde quepa sin tocar a la última que hay en ella.
      let destino = columnas.findIndex(
        (col) => minutosDe(col[col.length - 1]!.terminaEn) <= minutosDe(cita.iniciaEn),
      );
      if (destino === -1) {
        columnas.push([cita]);
        destino = columnas.length - 1;
      } else {
        columnas[destino]!.push(cita);
      }
      reparto.set(cita.id, { columna: destino, de: 0 });
    }
    for (const cita of grupo) {
      const actual = reparto.get(cita.id)!;
      reparto.set(cita.id, { columna: actual.columna, de: columnas.length });
    }
    grupo = [];
    finDelGrupo = -1;
  };

  for (const cita of orden) {
    if (grupo.length && minutosDe(cita.iniciaEn) >= finDelGrupo) cerrar();
    grupo.push(cita);
    finDelGrupo = Math.max(finDelGrupo, minutosDe(cita.terminaEn));
  }
  cerrar();

  return reparto;
}

export function Calendario({
  dias,
  citas,
  desdeHora = 6,
  hastaHora = 22,
  onTocarHueco,
  onTocarCita,
}: Props) {
  const horas = Array.from({ length: hastaHora - desdeHora }, (_, i) => desdeHora + i);
  const cuerpo = useRef<HTMLDivElement>(null);
  const hoy = new Date().toISOString().slice(0, 10);

  const primerDia = dias[0];
  const primeraCita = citas.reduce<number | null>(
    (min, c) => (min === null ? minutosDe(c.iniciaEn) : Math.min(min, minutosDe(c.iniciaEn))),
    null,
  );

  // Abre a la altura de la primera cita del rango, o a las 8 si no hay ninguna. Empezar
  // siempre a las 6 de la mañana obliga a bajar cada vez que se entra.
  useEffect(() => {
    const objetivo = ((primeraCita ?? 8 * 60) / 60 - desdeHora - 0.5) * ALTO_HORA;
    if (cuerpo.current) cuerpo.current.scrollTop = Math.max(0, objetivo);
  }, [primerDia, primeraCita, desdeHora]);

  const ahora = new Date();
  const minutoActual = ahora.getHours() * 60 + ahora.getMinutes();
  const hayHoy = dias.includes(hoy);
  const dentroDelRango = minutoActual >= desdeHora * 60 && minutoActual <= hastaHora * 60;

  return (
    <div className="overflow-hidden rounded-marco border border-linea">
      {/* En teléfono la semana no cabe: se desplaza en horizontal, como cualquier calendario.
          El encabezado va dentro del mismo contenedor para que se mueva con la rejilla. */}
      <div className="overflow-x-auto">
        <div className={cn("flex flex-col", dias.length > 1 && "min-w-[44rem]")}>
      {/* ---- Encabezado de días. Queda fijo al desplazar la rejilla. ---- */}
      <div
        className="grid border-b border-linea bg-fondo"
        style={{ gridTemplateColumns: `3.5rem repeat(${dias.length}, minmax(0, 1fr))` }}
      >
        <div />
        {dias.map((dia) => {
          const d = new Date(`${dia}T12:00:00`);
          const esHoy = dia === hoy;
          return (
            <div
              key={dia}
              className={cn(
                "flex flex-col items-center gap-0.5 border-l border-linea py-2",
                esHoy && "bg-acento-sutil",
              )}
            >
              <span className="text-micro font-medium tracking-[0.06em] text-tinta-suave uppercase">
                {DIAS_CORTOS[d.getDay()]}
              </span>
              <span
                className={cn(
                  "cifra grid size-7 place-items-center rounded-full text-menor font-semibold",
                  esHoy && "bg-tinta text-fondo",
                )}
              >
                {d.getDate()}
              </span>
            </div>
          );
        })}
      </div>

      {/* ---- Rejilla ---- */}
      <div ref={cuerpo} className="relative max-h-[62vh] overflow-y-auto">
        <div
          className="relative grid"
          style={{ gridTemplateColumns: `3.5rem repeat(${dias.length}, minmax(0, 1fr))` }}
        >
          {/* Columna de horas */}
          <div>
            {horas.map((h) => (
              <div
                key={h}
                className="relative border-b border-linea/60"
                style={{ height: ALTO_HORA }}
              >
                <span className="cifra absolute -top-2 right-2 bg-fondo px-1 text-micro text-tinta-suave">
                  {String(h).padStart(2, "0")}:00
                </span>
              </div>
            ))}
          </div>

          {/* Una columna por día */}
          {dias.map((dia) => {
            const delDia = citas.filter((c) => c.iniciaEn.slice(0, 10) === dia);
            const reparto = repartir(delDia);

            return (
              <div key={dia} className="relative border-l border-linea">
                {horas.map((h) => (
                  <button
                    key={h}
                    type="button"
                    aria-label={`Agendar el ${dia} a las ${h}:00`}
                    onClick={(e) => {
                      // Dónde se tocó dentro de la hora, redondeado al cuarto más cercano.
                      const caja = e.currentTarget.getBoundingClientRect();
                      const dentro = (e.clientY - caja.top) / caja.height;
                      const minuto = Math.round((dentro * 60) / PASO_MIN) * PASO_MIN;
                      const total = h * 60 + Math.min(minuto, 60 - PASO_MIN);
                      const hh = String(Math.floor(total / 60)).padStart(2, "0");
                      const mm = String(total % 60).padStart(2, "0");
                      onTocarHueco(`${dia}T${hh}:${mm}`);
                    }}
                    className="block w-full border-b border-linea/60 transition-colors hover:bg-fondo-sutil"
                    style={{ height: ALTO_HORA }}
                  />
                ))}

                {delDia.map((c) => {
                  const inicio = minutosDe(c.iniciaEn);
                  const fin = minutosDe(c.terminaEn);
                  const { columna, de } = reparto.get(c.id) ?? { columna: 0, de: 1 };
                  const ancho = 100 / Math.max(de, 1);

                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => onTocarCita(c.id)}
                      className={cn(
                        "absolute overflow-hidden rounded-[6px] border-l-2 px-1.5 py-1 text-left transition-shadow hover:shadow-md",
                        c.tono === "cancelada"
                          ? "border-l-linea-fuerte bg-fondo-sutil text-tinta-suave line-through"
                          : c.tono === "consulta"
                            ? "border-l-acento bg-acento-sutil text-tinta"
                            : "border-l-tinta-suave bg-fondo-sutil text-tinta",
                      )}
                      style={{
                        top: ((inicio - desdeHora * 60) / 60) * ALTO_HORA,
                        // Mínimo de 22 px: una cita de 15 minutos tiene que poder tocarse.
                        height: Math.max(((fin - inicio) / 60) * ALTO_HORA - 2, 22),
                        left: `calc(${columna * ancho}% + 2px)`,
                        width: `calc(${ancho}% - 4px)`,
                      }}
                    >
                      <span className="cifra block text-micro leading-tight font-semibold">
                        {c.iniciaEn.slice(11, 16)}
                      </span>
                      <span className="block truncate text-micro leading-tight font-medium">
                        {c.titulo}
                      </span>
                      {c.subtitulo && fin - inicio >= 45 ? (
                        <span className="block truncate text-micro leading-tight opacity-70">
                          {c.subtitulo}
                        </span>
                      ) : null}
                    </button>
                  );
                })}
              </div>
            );
          })}

          {/* Línea de la hora actual. Solo si hoy está a la vista. */}
          {hayHoy && dentroDelRango ? (
            <div
              className="pointer-events-none absolute right-0 left-14 z-10 flex items-center"
              style={{ top: ((minutoActual - desdeHora * 60) / 60) * ALTO_HORA }}
            >
              <span className="size-2 shrink-0 -translate-x-1 rounded-full bg-peligro" />
              <span className="h-px flex-1 bg-peligro" />
            </div>
          ) : null}
        </div>
      </div>
        </div>
      </div>
    </div>
  );
}

/** Vista de mes, sin horas: lo que se quiere del mes es «qué días tengo cargados». */
/** Un cobro programado en la rejilla. No es una cita: no tiene hora ni ocupa hueco. */
export interface CobroEnRejilla {
  ulid: string;
  fecha: string;
  alumna: string;
  monto: number;
  vencido: boolean;
}

export function CalendarioMes({
  ancla,
  citas,
  cobros = [],
  onTocarDia,
  onTocarCita,
  onTocarCobro,
}: {
  /** Cualquier día del mes que se pinta. */
  ancla: Date;
  citas: CitaEnRejilla[];
  cobros?: CobroEnRejilla[];
  onTocarDia: (dia: string) => void;
  onTocarCita: (id: string) => void;
  onTocarCobro?: (ulid: string) => void;
}) {
  const hoy = new Date().toISOString().slice(0, 10);
  const primero = new Date(ancla.getFullYear(), ancla.getMonth(), 1);
  const desplazamiento = (primero.getDay() + 6) % 7; // la semana empieza en lunes

  const celdas = Array.from({ length: 42 }, (_, i) => {
    const d = new Date(primero);
    d.setDate(1 - desplazamiento + i);
    const p = (n: number) => String(n).padStart(2, "0");
    return {
      clave: `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`,
      numero: d.getDate(),
      delMes: d.getMonth() === ancla.getMonth(),
    };
  });

  return (
    <div className="overflow-hidden rounded-marco border border-linea">
      <div className="grid grid-cols-7 border-b border-linea">
        {["lun", "mar", "mié", "jue", "vie", "sáb", "dom"].map((d) => (
          <div
            key={d}
            className="py-2 text-center text-micro font-medium tracking-[0.06em] text-tinta-suave uppercase"
          >
            {d}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7">
        {celdas.map((celda) => {
          const delDia = citas
            .filter((c) => c.iniciaEn.slice(0, 10) === celda.clave)
            .sort((a, b) => minutosDe(a.iniciaEn) - minutosDe(b.iniciaEn));
          const cobrosDelDia = cobros.filter((c) => c.fecha === celda.clave);

          return (
            <div
              key={celda.clave}
              className={cn(
                "flex min-h-24 flex-col gap-0.5 border-t border-l border-linea p-1",
                !celda.delMes && "bg-fondo-sutil/50",
              )}
            >
              <button
                type="button"
                onClick={() => onTocarDia(celda.clave)}
                className="flex justify-end"
              >
                <span
                  className={cn(
                    "cifra grid size-6 place-items-center rounded-full text-micro font-semibold transition-colors hover:bg-fondo-sutil",
                    celda.clave === hoy && "bg-tinta text-fondo",
                    !celda.delMes && "text-tinta-suave",
                  )}
                >
                  {celda.numero}
                </span>
              </button>

              {/* El dinero primero y sin hora: no compite con las consultas por el hueco. */}
              {cobrosDelDia.map((c) => (
                <button
                  key={c.ulid}
                  type="button"
                  onClick={() => onTocarCobro?.(c.ulid)}
                  className={cn(
                    "truncate rounded-[4px] border border-dashed px-1 py-0.5 text-left text-micro leading-tight",
                    c.vencido
                      ? "border-peligro text-peligro"
                      : "border-linea-fuerte text-tinta-media",
                  )}
                >
                  <span className="cifra font-semibold">${c.monto}</span> {c.alumna}
                </button>
              ))}

              {delDia.slice(0, 3).map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => onTocarCita(c.id)}
                  className={cn(
                    "truncate rounded-[4px] border-l-2 px-1 py-0.5 text-left text-micro leading-tight",
                    c.tono === "cancelada"
                      ? "border-l-linea-fuerte text-tinta-suave line-through"
                      : c.tono === "consulta"
                        ? "border-l-acento bg-acento-sutil"
                        : "border-l-tinta-suave bg-fondo-sutil",
                  )}
                >
                  <span className="cifra font-semibold">{c.iniciaEn.slice(11, 16)}</span>{" "}
                  {c.titulo}
                </button>
              ))}

              {delDia.length > 3 ? (
                <button
                  type="button"
                  onClick={() => onTocarDia(celda.clave)}
                  className="px-1 text-left text-micro text-tinta-suave hover:text-tinta"
                >
                  +{delDia.length - 3} más
                </button>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
