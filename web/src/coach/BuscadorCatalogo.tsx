/** Buscadores de alimentos y ejercicios sobre el catálogo.
 *
 *  La coach elige «Pechuga de pollo», escribe 180 g y salen kcal y macros escalados. La
 *  búsqueda va con retardo corto: buscar en cada tecla dispararía una petición por letra.
 */

import { Plus, Search } from "lucide-react";
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
  Selector,
  Vacio,
} from "@/componentes/primitivas";
import {
  baseDeCatalogo,
  escalar,
  type AlimentoEnPlan,
  type EjercicioEnPlan,
} from "@/lib/alimentos";
import { api, ErrorApi, type AlimentoCatalogoApi, type EjercicioCatalogoApi } from "@/lib/api";
import { num } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
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
  const { t } = useIdioma();
  const [q, setQ] = useState("");
  const [elegido, setElegido] = useState<AlimentoCatalogoApi | null>(null);
  const [cantidad, setCantidad] = useState("");

  // Alimento nuevo del banco propio: los valores van por 100 g (o 100 ml).
  const [creando, setCreando] = useState(false);
  const [formNuevo, setFormNuevo] = useState({
    nombre: "",
    unidad: "g",
    kcal: "",
    proteina: "",
    carbo: "",
    grasa: "",
  });
  const [guardandoNuevo, setGuardandoNuevo] = useState(false);
  const [errorNuevo, setErrorNuevo] = useState<string | null>(null);

  const { resultados, buscando } = usarBusqueda<AlimentoCatalogoApi>(
    (texto, senal) => api.coach.alimentos(texto, senal),
    q,
  );

  const cantidadNum = Number.parseFloat(cantidad);

  const calculado = useMemo(() => {
    if (!elegido || !cantidadNum || cantidadNum <= 0) return null;
    return escalar(elegido.nombre, baseDeCatalogo(elegido), cantidadNum, elegido.unidad);
  }, [elegido, cantidadNum]);

  const listoNuevo = formNuevo.nombre.trim().length > 0;

  async function guardarNuevo() {
    setGuardandoNuevo(true);
    setErrorNuevo(null);
    try {
      const creado = await api.coach.crearAlimento({
        nombre: formNuevo.nombre.trim(),
        porcion: 100,
        unidad: formNuevo.unidad,
        kcal: Number.parseFloat(formNuevo.kcal) || 0,
        proteina: Number.parseFloat(formNuevo.proteina) || 0,
        carbo: Number.parseFloat(formNuevo.carbo) || 0,
        grasa: Number.parseFloat(formNuevo.grasa) || 0,
      });
      // Queda elegido con su porción de referencia: solo falta la cantidad.
      setElegido(creado);
      setCantidad("100");
      setCreando(false);
      setFormNuevo({ nombre: "", unidad: "g", kcal: "", proteina: "", carbo: "", grasa: "" });
    } catch (causa) {
      setErrorNuevo(causa instanceof ErrorApi ? causa.message : t("No se pudo guardar el alimento."));
    } finally {
      setGuardandoNuevo(false);
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={t("Agregar alimento")}
      titulo={creando ? t("Nuevo alimento") : elegido ? elegido.nombre : t("Busca en el catálogo")}
      pie={
        creando ? (
          <>
            <Boton
              tono="discreto"
              medida="chica"
              disabled={guardandoNuevo}
              onClick={() => {
                setCreando(false);
                setErrorNuevo(null);
              }}
            >
              {t("Volver")}
            </Boton>
            <Boton
              medida="chica"
              disabled={!listoNuevo || guardandoNuevo}
              cargando={guardandoNuevo}
              onClick={() => void guardarNuevo()}
            >
              {t("Guardar alimento")}
            </Boton>
          </>
        ) : (
          <>
            <Boton tono="contorno" medida="chica" onClick={onCerrar}>
              {t("Cancelar")}
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
              {t("Agregar")}
            </Boton>
          </>
        )
      }
    >
      {creando ? (
        <>
          <Campo id="na-nombre" etiqueta={t("Nombre")}>
            <Entrada
              id="na-nombre"
              autoFocus
              value={formNuevo.nombre}
              onChange={(e) => setFormNuevo((f) => ({ ...f, nombre: e.target.value }))}
              placeholder={t("Pechuga, garbanzos, requesón…")}
            />
          </Campo>

          <Campo id="na-unidad" etiqueta={t("Unidad")}>
            <Selector
              id="na-unidad"
              value={formNuevo.unidad}
              onChange={(e) => setFormNuevo((f) => ({ ...f, unidad: e.target.value }))}
              className="max-w-40"
            >
              <option value="g">{t("Gramos")}</option>
              <option value="ml">{t("Mililitros")}</option>
            </Selector>
          </Campo>

          <Apoyo>
            {t("Los valores van por 100 {unidad}.", {
              unidad: formNuevo.unidad === "g" ? t("gramos") : t("mililitros"),
            })}
          </Apoyo>

          <div className="grid gap-4 sm:grid-cols-2">
            <Campo id="na-kcal" etiqueta={t("Calorías")} sufijo="kcal">
              <Entrada
                id="na-kcal"
                type="number"
                min={0}
                step="any"
                inputMode="decimal"
                value={formNuevo.kcal}
                onChange={(e) => setFormNuevo((f) => ({ ...f, kcal: e.target.value }))}
                className="rounded-r-none"
              />
            </Campo>
            <Campo id="na-proteina" etiqueta={t("Proteína")} sufijo="g">
              <Entrada
                id="na-proteina"
                type="number"
                min={0}
                step="any"
                inputMode="decimal"
                value={formNuevo.proteina}
                onChange={(e) => setFormNuevo((f) => ({ ...f, proteina: e.target.value }))}
                className="rounded-r-none"
              />
            </Campo>
            <Campo id="na-carbo" etiqueta={t("Carbohidratos")} sufijo="g">
              <Entrada
                id="na-carbo"
                type="number"
                min={0}
                step="any"
                inputMode="decimal"
                value={formNuevo.carbo}
                onChange={(e) => setFormNuevo((f) => ({ ...f, carbo: e.target.value }))}
                className="rounded-r-none"
              />
            </Campo>
            <Campo id="na-grasa" etiqueta={t("Grasa")} sufijo="g">
              <Entrada
                id="na-grasa"
                type="number"
                min={0}
                step="any"
                inputMode="decimal"
                value={formNuevo.grasa}
                onChange={(e) => setFormNuevo((f) => ({ ...f, grasa: e.target.value }))}
                className="rounded-r-none"
              />
            </Campo>
          </div>

          {errorNuevo ? <Aviso tono="error">{errorNuevo}</Aviso> : null}

          <Apoyo>
            {t("Se guarda en tu banco con el sello «Tuyo» y queda para esta alumna y las que siguen.")}
          </Apoyo>
        </>
      ) : elegido === null ? (
        <>
          <Campo id="ba-q" etiqueta={t("Buscar")}>
            <div className="flex w-full items-center gap-2 rounded-marco border border-linea px-3 focus-within:border-tinta">
              <Search className="size-4 shrink-0 text-tinta-suave" strokeWidth={1.6} />
              <input
                id="ba-q"
                autoFocus
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={t("Pollo, avena, tortilla…")}
                className="h-11 w-full bg-transparent text-cuerpo outline-none placeholder:text-tinta-suave"
              />
            </div>
          </Campo>

          {resultados.length === 0 ? (
            <Vacio>{buscando ? t("Buscando…") : t("Nada con ese nombre.")}</Vacio>
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
                        {a.propio ? <Chip>{t("Tuyo")}</Chip> : null}
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

          <div className="flex flex-col gap-2">
            <Boton
              tono="contorno"
              medida="chica"
              onClick={() => {
                setCreando(true);
                setErrorNuevo(null);
              }}
            >
              <Plus className="size-3.5" /> {t("Nuevo alimento")}
            </Boton>
            <Apoyo>{t("El catálogo trae la base pública más tus alimentos propios. Si falta alguno, créalo aquí.")}</Apoyo>
          </div>
        </>
      ) : (
        <>
          <Campo
            id="ba-cantidad"
            etiqueta={t("Cantidad")}
            sufijo={elegido.unidad}
            ayuda={t("Referencia del catálogo: {porcion} {unidad} = {kcal} kcal.", {
              porcion: num(elegido.porcion, 0),
              unidad: elegido.unidad,
              kcal: num(elegido.kcal, 0),
            })}
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
                  <dt className="text-micro uppercase tracking-[0.08em] text-tinta-suave">{t(k)}</dt>
                  <dd className="cifra text-guia font-semibold">{v}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <Aviso tono="atencion">{t("Escribe una cantidad mayor que cero.")}</Aviso>
          )}

          <Boton tono="discreto" medida="chica" onClick={() => setElegido(null)}>
            {t("Elegir otro alimento")}
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
  const { t } = useIdioma();
  const [q, setQ] = useState("");
  const [elegido, setElegido] = useState<EjercicioCatalogoApi | null>(null);
  const [series, setSeries] = useState("3");
  const [reps, setReps] = useState("8-10");
  const [carga, setCarga] = useState("");
  const [nota, setNota] = useState("");

  // Ejercicio nuevo del banco propio.
  const [creando, setCreando] = useState(false);
  const [formNuevo, setFormNuevo] = useState({ nombre: "", grupo: "", equipo: "", patron: "" });
  const [guardandoNuevo, setGuardandoNuevo] = useState(false);
  const [errorNuevo, setErrorNuevo] = useState<string | null>(null);

  const { resultados, buscando } = usarBusqueda<EjercicioCatalogoApi>(
    (texto, senal) => api.coach.ejercicios(texto, senal),
    q,
  );

  const seriesNum = Number.parseInt(series, 10);
  const listo = elegido !== null && seriesNum > 0 && reps.trim().length > 0;

  const listoNuevo = formNuevo.nombre.trim().length > 0;

  async function guardarNuevo() {
    setGuardandoNuevo(true);
    setErrorNuevo(null);
    try {
      const creado = await api.coach.crearEjercicio({
        nombre: formNuevo.nombre.trim(),
        grupo: formNuevo.grupo.trim() || null,
        equipo: formNuevo.equipo.trim() || null,
        patron: formNuevo.patron.trim() || null,
      });
      // Queda elegido: solo falta la prescripción de series, reps y carga.
      setElegido(creado);
      setCreando(false);
      setFormNuevo({ nombre: "", grupo: "", equipo: "", patron: "" });
    } catch (causa) {
      setErrorNuevo(causa instanceof ErrorApi ? causa.message : t("No se pudo guardar el ejercicio."));
    } finally {
      setGuardandoNuevo(false);
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={t("Agregar ejercicio")}
      titulo={creando ? t("Nuevo ejercicio") : elegido ? elegido.nombre : t("Busca en el catálogo")}
      pie={
        creando ? (
          <>
            <Boton
              tono="discreto"
              medida="chica"
              disabled={guardandoNuevo}
              onClick={() => {
                setCreando(false);
                setErrorNuevo(null);
              }}
            >
              {t("Volver")}
            </Boton>
            <Boton
              medida="chica"
              disabled={!listoNuevo || guardandoNuevo}
              cargando={guardandoNuevo}
              onClick={() => void guardarNuevo()}
            >
              {t("Guardar ejercicio")}
            </Boton>
          </>
        ) : (
          <>
            <Boton tono="contorno" medida="chica" onClick={onCerrar}>
              {t("Cancelar")}
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
              {t("Agregar")}
            </Boton>
          </>
        )
      }
    >
      {creando ? (
        <>
          <Campo id="ne-nombre" etiqueta={t("Nombre")}>
            <Entrada
              id="ne-nombre"
              autoFocus
              value={formNuevo.nombre}
              onChange={(e) => setFormNuevo((f) => ({ ...f, nombre: e.target.value }))}
              placeholder={t("Press banca, remo, zancada…")}
            />
          </Campo>

          <Campo id="ne-grupo" etiqueta={t("Músculo que trabaja")}>
            <Entrada
              id="ne-grupo"
              value={formNuevo.grupo}
              onChange={(e) => setFormNuevo((f) => ({ ...f, grupo: e.target.value }))}
              placeholder={t("Pecho, espalda, pierna…")}
            />
          </Campo>

          <Campo id="ne-equipo" etiqueta={t("Equipo")}>
            <Entrada
              id="ne-equipo"
              value={formNuevo.equipo}
              onChange={(e) => setFormNuevo((f) => ({ ...f, equipo: e.target.value }))}
              placeholder={t("Barra, mancuernas, máquina, peso corporal…")}
            />
          </Campo>

          <Campo id="ne-patron" etiqueta={t("Tipo de movimiento")}>
            <Entrada
              id="ne-patron"
              value={formNuevo.patron}
              onChange={(e) => setFormNuevo((f) => ({ ...f, patron: e.target.value }))}
              placeholder={t("Empuje, jalón, sentadilla, bisagra…")}
            />
          </Campo>

          {errorNuevo ? <Aviso tono="error">{errorNuevo}</Aviso> : null}

          <Apoyo>
            {t("Se guarda en tu banco con el sello «Tuyo» y queda para esta alumna y las que siguen.")}
          </Apoyo>
        </>
      ) : elegido === null ? (
        <>
          <Campo id="be-q" etiqueta={t("Buscar")}>
            <div className="flex w-full items-center gap-2 rounded-marco border border-linea px-3 focus-within:border-tinta">
              <Search className="size-4 shrink-0 text-tinta-suave" strokeWidth={1.6} />
              <input
                id="be-q"
                autoFocus
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={t("Sentadilla, remo, hip thrust…")}
                className="h-11 w-full bg-transparent text-cuerpo outline-none placeholder:text-tinta-suave"
              />
            </div>
          </Campo>

          {resultados.length === 0 ? (
            <Vacio>{buscando ? t("Buscando…") : t("Nada con ese nombre.")}</Vacio>
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
                      {e.propio ? <Chip>{t("Tuyo")}</Chip> : null}
                      {e.tieneVideo ? <Chip tono="exito">{t("Con video")}</Chip> : null}
                    </span>
                    <span className="text-micro text-tinta-suave">
                      {[e.grupo, e.equipo, e.patron].filter(Boolean).join(" · ")}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="flex flex-col gap-2">
            <Boton
              tono="contorno"
              medida="chica"
              onClick={() => {
                setCreando(true);
                setErrorNuevo(null);
              }}
            >
              <Plus className="size-3.5" /> {t("Nuevo ejercicio")}
            </Boton>
            <Apoyo>{t("El banco trae la base pública más tus ejercicios propios. Si falta alguno, créalo aquí.")}</Apoyo>
          </div>
        </>
      ) : (
        <>
          {/* El aviso no bloquea: quien decide si el ejercicio le sirve es la coach. */}
          {lesiones ? (
            <Aviso tono="atencion" titulo={t("Recuerda su historial")}>
              {lesiones}
            </Aviso>
          ) : null}
          {elegido.contraindicaciones ? (
            <Aviso tono="error" titulo={t("Contraindicaciones de este ejercicio")}>
              {elegido.contraindicaciones}
            </Aviso>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-3">
            <Campo id="be-series" etiqueta={t("Series")}>
              <Entrada
                id="be-series"
                type="number"
                min={1}
                max={12}
                value={series}
                onChange={(ev) => setSeries(ev.target.value)}
              />
            </Campo>
            <Campo id="be-reps" etiqueta={t("Repeticiones")}>
              <Entrada id="be-reps" value={reps} onChange={(ev) => setReps(ev.target.value)} />
            </Campo>
            <Campo id="be-carga" etiqueta={t("Carga")}>
              <Entrada
                id="be-carga"
                value={carga}
                onChange={(ev) => setCarga(ev.target.value)}
                placeholder={t("45 kg")}
              />
            </Campo>
          </div>

          <Campo
            id="be-nota"
            etiqueta={t("Nota de ejecución (opcional)")}
            ayuda={t("La alumna la ve debajo del ejercicio, en su plan y en el PDF.")}
          >
            <Entrada
              id="be-nota"
              value={nota}
              onChange={(ev) => setNota(ev.target.value)}
              placeholder={t("Profundidad hasta paralelo. Nada de valgo.")}
            />
          </Campo>

          <Boton tono="discreto" medida="chica" onClick={() => setElegido(null)}>
            {t("Elegir otro ejercicio")}
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
  const { t } = useIdioma();
  return (
    <li className={cn("flex items-baseline justify-between gap-3 py-2.5", className)}>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">{children}</div>
      <Boton tono="discreto" medida="chica" onClick={onQuitar} aria-label={t("Quitar")}>
        {t("Quitar")}
      </Boton>
    </li>
  );
}

export { Etiqueta };
