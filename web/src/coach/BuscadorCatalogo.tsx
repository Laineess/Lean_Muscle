/** Buscadores de alimentos y ejercicios sobre el catálogo.
 *
 *  La coach elige «Pechuga de pollo», escribe 180 g y salen kcal y macros escalados. La
 *  búsqueda va con retardo corto: buscar en cada tecla dispararía una petición por letra.
 */

import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Dialogo } from "@/componentes/Dialogo";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Chip,
  Entrada,
  Etiqueta,
  Vacio,
} from "@/componentes/primitivas";
import {
  baseDeCatalogo,
  escalar,
  type AlimentoEnPlan,
  type EjercicioEnPlan,
} from "@/lib/alimentos";
import { api, type AlimentoCatalogoApi, type EjercicioCatalogoApi } from "@/lib/api";
import { num } from "@/lib/formato";
import { cn } from "@/lib/utils";

const RETARDO_MS = 250;

/** Búsqueda con retardo. Sin esto, «pechuga» dispara siete peticiones. */
function usarBusqueda<T>(
  pedir: (q: string, senal: AbortSignal) => Promise<T[]>,
  q: string,
): { resultados: T[]; buscando: boolean } {
  const [resultados, setResultados] = useState<T[]>([]);
  const [buscando, setBuscando] = useState(false);

  useEffect(() => {
    const control = new AbortController();
    const temporizador = setTimeout(() => {
      setBuscando(true);
      pedir(q, control.signal)
        .then((r) => {
          if (!control.signal.aborted) setResultados(r);
        })
        .catch(() => {
          // Sin servidor el buscador se queda vacío; la pantalla ya avisa arriba.
          if (!control.signal.aborted) setResultados([]);
        })
        .finally(() => {
          if (!control.signal.aborted) setBuscando(false);
        });
    }, RETARDO_MS);

    return () => {
      clearTimeout(temporizador);
      control.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  return { resultados, buscando };
}

/* ---------------------------------------------------------------- Alimentos --- */

export function BuscadorAlimento({
  onElegir,
  onCerrar,
}: {
  onElegir: (a: AlimentoEnPlan) => void;
  onCerrar: () => void;
}) {
  const [q, setQ] = useState("");
  const [elegido, setElegido] = useState<AlimentoCatalogoApi | null>(null);
  const [cantidad, setCantidad] = useState("");

  const { resultados, buscando } = usarBusqueda<AlimentoCatalogoApi>(
    (texto, senal) => api.coach.alimentos(texto, senal),
    q,
  );

  const cantidadNum = Number.parseFloat(cantidad);

  const calculado = useMemo(() => {
    if (!elegido || !cantidadNum || cantidadNum <= 0) return null;
    return escalar(elegido.nombre, baseDeCatalogo(elegido), cantidadNum, elegido.unidad);
  }, [elegido, cantidadNum]);

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta="Agregar alimento"
      titulo={elegido ? elegido.nombre : "Busca en el catálogo"}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton
            medida="chica"
            disabled={!calculado}
            onClick={() => {
              if (calculado) {
                onElegir(calculado);
                onCerrar();
              }
            }}
          >
            Agregar
          </Boton>
        </>
      }
    >
      {elegido === null ? (
        <>
          <Campo id="ba-q" etiqueta="Buscar">
            <div className="flex w-full items-center gap-2 rounded-marco border border-linea px-3 focus-within:border-tinta">
              <Search className="size-4 shrink-0 text-tinta-suave" strokeWidth={1.6} />
              <input
                id="ba-q"
                autoFocus
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Pollo, avena, tortilla…"
                className="h-11 w-full bg-transparent text-cuerpo outline-none placeholder:text-tinta-suave"
              />
            </div>
          </Campo>

          {resultados.length === 0 ? (
            <Vacio>{buscando ? "Buscando…" : "Nada con ese nombre."}</Vacio>
          ) : (
            <ul className="flex flex-col divide-y divide-linea border-y border-linea">
              {resultados.map((a) => (
                <li key={a.ulid}>
                  <button
                    onClick={() => {
                      setElegido(a);
                      setCantidad(String(a.porcion));
                    }}
                    className="flex w-full items-center justify-between gap-3 py-2.5 text-left transition-colors hover:bg-fondo-sutil"
                  >
                    <span className="flex min-w-0 flex-col">
                      <span className="flex items-center gap-2 text-menor font-medium">
                        {a.nombre}
                        {a.propio ? <Chip>Tuyo</Chip> : null}
                      </span>
                      <span className="cifra text-micro text-tinta-suave">
                        {num(a.porcion, 0)} {a.unidad} · {num(a.kcal, 0)} kcal · P {num(a.proteina)}{" "}
                        C {num(a.carbo)} G {num(a.grasa)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          <Apoyo>
            El catálogo trae la base pública más tus alimentos propios. Si falta alguno, créalo
            desde la biblioteca.
          </Apoyo>
        </>
      ) : (
        <>
          <Campo
            id="ba-cantidad"
            etiqueta="Cantidad"
            sufijo={elegido.unidad}
            ayuda={`Referencia del catálogo: ${num(elegido.porcion, 0)} ${elegido.unidad} = ${num(elegido.kcal, 0)} kcal.`}
          >
            <Entrada
              id="ba-cantidad"
              type="number"
              min={1}
              step="1"
              autoFocus
              value={cantidad}
              onChange={(e) => setCantidad(e.target.value)}
              className="rounded-r-none"
            />
          </Campo>

          {calculado ? (
            <dl className="grid grid-cols-4 gap-3">
              {(
                [
                  ["Calorías", `${calculado.kcal}`],
                  ["Proteína", `${calculado.p} g`],
                  ["Carbos", `${calculado.c} g`],
                  ["Grasa", `${calculado.g} g`],
                ] as const
              ).map(([k, v]) => (
                <div key={k} className="flex flex-col gap-0.5">
                  <dt className="text-micro uppercase tracking-[0.08em] text-tinta-suave">{k}</dt>
                  <dd className="cifra text-guia font-semibold">{v}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <Aviso tono="atencion">Escribe una cantidad mayor que cero.</Aviso>
          )}

          <Boton tono="discreto" medida="chica" onClick={() => setElegido(null)}>
            Elegir otro alimento
          </Boton>
        </>
      )}
    </Dialogo>
  );
}

/* --------------------------------------------------------------- Ejercicios --- */

export function BuscadorEjercicio({
  lesiones,
  onElegir,
  onCerrar,
}: {
  /** Para avisar si el ejercicio choca con algo del historial de la alumna. */
  lesiones: string | null;
  onElegir: (e: EjercicioEnPlan) => void;
  onCerrar: () => void;
}) {
  const [q, setQ] = useState("");
  const [elegido, setElegido] = useState<EjercicioCatalogoApi | null>(null);
  const [series, setSeries] = useState("3");
  const [reps, setReps] = useState("8-10");
  const [carga, setCarga] = useState("");
  const [nota, setNota] = useState("");

  const { resultados, buscando } = usarBusqueda<EjercicioCatalogoApi>(
    (texto, senal) => api.coach.ejercicios(texto, senal),
    q,
  );

  const seriesNum = Number.parseInt(series, 10);
  const listo = elegido !== null && seriesNum > 0 && reps.trim().length > 0;

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta="Agregar ejercicio"
      titulo={elegido ? elegido.nombre : "Busca en el catálogo"}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton
            medida="chica"
            disabled={!listo}
            onClick={() => {
              if (elegido) {
                onElegir({
                  nombre: elegido.nombre,
                  series: seriesNum,
                  reps: reps.trim(),
                  carga: carga.trim(),
                  nota: nota.trim(),
                });
                onCerrar();
              }
            }}
          >
            Agregar
          </Boton>
        </>
      }
    >
      {elegido === null ? (
        <>
          <Campo id="be-q" etiqueta="Buscar">
            <div className="flex w-full items-center gap-2 rounded-marco border border-linea px-3 focus-within:border-tinta">
              <Search className="size-4 shrink-0 text-tinta-suave" strokeWidth={1.6} />
              <input
                id="be-q"
                autoFocus
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Sentadilla, remo, hip thrust…"
                className="h-11 w-full bg-transparent text-cuerpo outline-none placeholder:text-tinta-suave"
              />
            </div>
          </Campo>

          {resultados.length === 0 ? (
            <Vacio>{buscando ? "Buscando…" : "Nada con ese nombre."}</Vacio>
          ) : (
            <ul className="flex flex-col divide-y divide-linea border-y border-linea">
              {resultados.map((e) => (
                <li key={e.ulid}>
                  <button
                    onClick={() => setElegido(e)}
                    className="flex w-full flex-col gap-0.5 py-2.5 text-left transition-colors hover:bg-fondo-sutil"
                  >
                    <span className="flex flex-wrap items-center gap-2 text-menor font-medium">
                      {e.nombre}
                      {e.propio ? <Chip>Tuyo</Chip> : null}
                      {e.tieneVideo ? <Chip tono="exito">Con video</Chip> : null}
                    </span>
                    <span className="text-micro text-tinta-suave">
                      {[e.grupo, e.equipo, e.patron].filter(Boolean).join(" · ")}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <>
          {/* El aviso no bloquea: quien decide si el ejercicio le sirve es la coach. */}
          {lesiones ? (
            <Aviso tono="atencion" titulo="Recuerda su historial">
              {lesiones}
            </Aviso>
          ) : null}
          {elegido.contraindicaciones ? (
            <Aviso tono="error" titulo="Contraindicaciones de este ejercicio">
              {elegido.contraindicaciones}
            </Aviso>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-3">
            <Campo id="be-series" etiqueta="Series">
              <Entrada
                id="be-series"
                type="number"
                min={1}
                max={12}
                value={series}
                onChange={(ev) => setSeries(ev.target.value)}
              />
            </Campo>
            <Campo id="be-reps" etiqueta="Repeticiones">
              <Entrada id="be-reps" value={reps} onChange={(ev) => setReps(ev.target.value)} />
            </Campo>
            <Campo id="be-carga" etiqueta="Carga">
              <Entrada
                id="be-carga"
                value={carga}
                onChange={(ev) => setCarga(ev.target.value)}
                placeholder="45 kg"
              />
            </Campo>
          </div>

          <Campo
            id="be-nota"
            etiqueta="Nota de ejecución (opcional)"
            ayuda="La alumna la ve debajo del ejercicio, en su plan y en el PDF."
          >
            <Entrada
              id="be-nota"
              value={nota}
              onChange={(ev) => setNota(ev.target.value)}
              placeholder="Profundidad hasta paralelo. Nada de valgo."
            />
          </Campo>

          <Boton tono="discreto" medida="chica" onClick={() => setElegido(null)}>
            Elegir otro ejercicio
          </Boton>
        </>
      )}
    </Dialogo>
  );
}

/** Fila con acción de borrado, compartida por los dos editores. */
export function FilaEditable({
  children,
  onQuitar,
  className,
}: {
  children: React.ReactNode;
  onQuitar: () => void;
  className?: string;
}) {
  return (
    <li className={cn("flex items-baseline justify-between gap-3 py-2.5", className)}>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">{children}</div>
      <Boton tono="discreto" medida="chica" onClick={onQuitar} aria-label="Quitar">
        Quitar
      </Boton>
    </li>
  );
}

export { Etiqueta };
