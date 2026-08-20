/** El chequeo mensual: cinco pasos, a pantalla completa.
 *
 *  El borrador vive en el servidor y se guarda al cambiar de paso. Lo que se valida aquí es
 *  cortesía; las reglas que mandan están en `app/dominio/chequeo.py`.
 */

import { ArrowLeft, Camera, Check, RotateCcw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Dialogo } from "@/componentes/Dialogo";
import { CargandoPantalla } from "@/componentes/Estado";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Casilla,
  Chip,
  Entrada,
  Etiqueta,
  Portada,
  Regla,
  Titulo,
} from "@/componentes/primitivas";
import { ErrorApi, api, urlDeFoto, type Angulo, type BorradorApi } from "@/lib/api";
import { delta, fecha, num } from "@/lib/formato";
import { ANGULOS, MEDIDAS, type TipoMedida } from "@/lib/tipos";
import { cn } from "@/lib/utils";

const PASOS = ["Estado", "Peso", "Medidas", "Fotos", "Envío"] as const;
type Paso = 0 | 1 | 2 | 3 | 4;

/** En qué paso retomar, deducido de lo que ya está guardado.
 *
 *  No se guarda el número de paso en ningún lado: se deduce del expediente, que es la única
 *  fuente que sobrevive a cerrar sesión, refrescar o cambiar de teléfono. Guardar el paso
 *  aparte abriría la puerta a que dijera «vas por las fotos» sobre un chequeo sin peso.
 *
 *  Se para en el primero que falte, no en el último que esté: así vuelve justo a lo que
 *  dejó a medias.
 */
/** Las condiciones a medio marcar, en este navegador.
 *
 *  El expediente guarda si están **todas** confirmadas, no cuáles: es un solo booleano, y
 *  cambiarlo por una lista pediría una migración para cuatro casillas que se vuelven a
 *  marcar en tres segundos. Quien cierra a medio paso las recupera aquí; quien vuelve desde
 *  otro teléfono las marca otra vez, y no pierde ningún dato por ello.
 */
const LLAVE_CONDICIONES = "mfp:chequeo:condiciones";

function condicionesGuardadas(ulid: string): Set<string> {
  try {
    const crudo = localStorage.getItem(`${LLAVE_CONDICIONES}:${ulid}`);
    const ids: unknown = crudo ? JSON.parse(crudo) : [];
    return new Set(Array.isArray(ids) ? ids.filter((x): x is string => typeof x === "string") : []);
  } catch {
    // Un almacenamiento lleno o bloqueado no puede impedir hacer el chequeo.
    return new Set();
  }
}

function guardarCondiciones(ulid: string, ids: Set<string>): void {
  try {
    localStorage.setItem(`${LLAVE_CONDICIONES}:${ulid}`, JSON.stringify([...ids]));
  } catch {
    /* vacío a propósito: es una comodidad, no un dato */
  }
}

/** Qué le pasa a una medida, dicho en el propio campo.
 *
 *  El resumen de abajo se queda: enumera todo lo que falta antes de avanzar. Pero con ocho
 *  campos en dos columnas, «revisa Pantorrilla» obliga a buscar cuál es. El aviso tiene que
 *  estar donde está el número que hay que corregir.
 */
function problemaDeMedida(
  m: { rotulo: string; min: number; max: number },
  crudo: string | undefined,
): string | null {
  const texto = (crudo ?? "").trim();
  if (!texto) return null;
  const v = Number.parseFloat(texto);
  if (Number.isNaN(v)) return "Escribe solo el número.";
  if (v < m.min) return `Muy poco. ${m.rotulo} va de ${m.min} a ${m.max} cm.`;
  if (v > m.max) return `Muy alto. ${m.rotulo} va de ${m.min} a ${m.max} cm.`;
  return null;
}

function pasoDondeSeQuedo(b: BorradorApi): Paso {
  if (!b.ayunoConfirmado) return 0;
  if (b.pesoKg === null) return 1;
  if (Object.keys(b.medidas).length < MEDIDAS.length) return 2;
  if (b.fotos.length < ANGULOS.length) return 3;
  return 4;
}

const CONDICIONES = [
  { id: "ayunas", titulo: "Estoy en ayunas", detalle: "Nada de comida ni bebida desde anoche, tampoco agua." },
  { id: "despierta", titulo: "Acabo de despertar", detalle: "Es lo primero que hago hoy." },
  { id: "bano", titulo: "Ya fui al baño", detalle: "Evacué antes de pesarme." },
  { id: "sin_entrenar", titulo: "No he entrenado", detalle: "Ni entrenamiento ni cardio hoy." },
] as const;

/** Una causa de rechazo tal y como la manda el servidor. */
interface CausaDeRechazo {
  codigo: string;
  mensaje: string;
}

export function Chequeo() {
  const navegar = useNavigate();

  const [borrador, setBorrador] = useState<BorradorApi | null>(null);
  const [errorDeCarga, setErrorDeCarga] = useState<string | null>(null);

  const [paso, setPaso] = useState<Paso>(0);
  const [condiciones, setCondiciones] = useState<Set<string>>(new Set());
  const [peso, setPeso] = useState("");
  const [varianzaConfirmada, setVarianzaConfirmada] = useState(false);
  const [entorno, setEntorno] = useState({ bascula: true, lugar: true, hora: true });
  // Se guarda lo que teclea, no el número: descartar el valor mientras está fuera de rango
  // hace imposible escribir «75», porque el «7» de en medio cae bajo el mínimo y se borra.
  const [textoMedidas, setTextoMedidas] = useState<Partial<Record<TipoMedida, string>>>({});
  const [nota, setNota] = useState("");

  const [guardando, setGuardando] = useState(false);
  const [errorAlGuardar, setErrorAlGuardar] = useState<string | null>(null);
  const [causas, setCausas] = useState<CausaDeRechazo[]>([]);
  const [ayudaDe, setAyudaDe] = useState<TipoMedida | null>(null);
  const [enviado, setEnviado] = useState(false);

  /* ---- Abrir el chequeo del ciclo (o recuperar el que ya estaba abierto) ---- */
  useEffect(() => {
    let vivo = true;
    api.alumna
      .abrirChequeo()
      .then((b) => {
        if (!vivo) return;
        setBorrador(b);
        setPeso(b.pesoKg !== null ? String(b.pesoKg) : "");
        setTextoMedidas(
          Object.fromEntries(Object.entries(b.medidas).map(([k, v]) => [k, String(v)])),
        );
        setNota(b.notaAlumna ?? "");
        setVarianzaConfirmada(b.varianzaConfirmada);
        // Confirmadas las cuatro, se marcan las cuatro. A medias solo lo sabe este
        // navegador: el expediente guarda si están todas, no cuáles.
        setCondiciones(
          b.ayunoConfirmado ? new Set(CONDICIONES.map((c) => c.id)) : condicionesGuardadas(b.ulid),
        );
        setPaso(pasoDondeSeQuedo(b));
      })
      .catch((causa: unknown) => {
        if (!vivo) return;
        setErrorDeCarga(
          causa instanceof ErrorApi ? causa.message : "No se pudo abrir tu chequeo.",
        );
      });
    return () => {
      vivo = false;
    };
  }, []);

  const previoPeso = borrador?.pesoAnteriorKg ?? null;
  const previoMedidas = borrador?.medidasAnteriores ?? {};

  const pesoNum = Number.parseFloat(peso);
  const varianza = pesoNum && previoPeso ? (pesoNum - previoPeso) / previoPeso : 0;
  const magnitud = Math.abs(varianza);

  // Solo las que ya son un número dentro de rango. Es lo que se guarda y lo que se cuenta.
  const medidas: Partial<Record<TipoMedida, number>> = {};
  const fueraDeRango: string[] = [];
  for (const m of MEDIDAS) {
    const crudo = (textoMedidas[m.tipo] ?? "").trim();
    if (!crudo) continue;
    const v = Number.parseFloat(crudo);
    if (Number.isNaN(v)) continue;
    if (v < m.min || v > m.max) fueraDeRango.push(m.rotulo);
    else medidas[m.tipo] = v;
  }

  const medidasListas = Object.keys(medidas).length;
  const fotos = borrador?.fotos ?? [];
  const fotosListas = fotos.length;

  const pesajes = borrador?.pesajes ?? [];
  // Son tres tomas como mucho: memorizar el promedio costaba más que calcularlo.
  const promedio = pesajes.length
    ? Math.round((pesajes.reduce((s, p) => s + p.pesoKg, 0) / pesajes.length) * 10) / 10
    : null;

  /* ---- Guardas por paso, las mismas que aplica el servidor ---- */
  const puedeAvanzar: Record<Paso, boolean> = {
    0: condiciones.size === CONDICIONES.length,
    1: Boolean(pesoNum) && pesoNum >= 30 && pesoNum <= 250 && (magnitud <= 0.03 || varianzaConfirmada),
    2: medidasListas === MEDIDAS.length,
    3: fotosListas === ANGULOS.length,
    4: true,
  };

  /** Manda al servidor lo que se capturó en este paso. */
  async function guardarPaso(): Promise<boolean> {
    if (!borrador) return false;
    setErrorAlGuardar(null);
    setGuardando(true);
    try {
      const cambios: Parameters<typeof api.alumna.guardarChequeo>[1] = {};
      if (paso === 0) cambios.ayunoConfirmado = condiciones.size === CONDICIONES.length;
      if (paso === 1) {
        cambios.pesoKg = pesoNum;
        cambios.varianzaConfirmada = varianzaConfirmada;
        // El entorno no bloquea: se anota para que la coach sepa con qué comparar.
        cambios.basculaUsada = entorno.bascula ? (borrador.basculaRef ?? "") : "";
        cambios.lugarUsado = entorno.lugar ? (borrador.lugarRef ?? "") : "";
        cambios.horaUsada = entorno.hora ? (borrador.horaRef ?? "") : "";
      }
      if (paso === 2) cambios.medidas = medidas;
      if (paso === 4) cambios.notaAlumna = nota;

      setBorrador(await api.alumna.guardarChequeo(borrador.ulid, cambios));
      return true;
    } catch (causa: unknown) {
      setErrorAlGuardar(
        causa instanceof ErrorApi ? causa.message : "No se pudo guardar. Inténtalo otra vez.",
      );
      return false;
    } finally {
      setGuardando(false);
    }
  }

  async function avanzar() {
    if (!(await guardarPaso())) return;
    setPaso((p) => Math.min(p + 1, 4) as Paso);
  }

  function retroceder() {
    if (paso === 0) void navegar("/inicio");
    else setPaso((p) => (p - 1) as Paso);
  }

  async function enviar() {
    if (!borrador) return;
    if (!(await guardarPaso())) return;

    setCausas([]);
    setGuardando(true);
    try {
      await api.alumna.enviarChequeo(borrador.ulid);
      setEnviado(true);
    } catch (causa: unknown) {
      if (causa instanceof ErrorApi) {
        // El servidor manda **todas** las causas juntas: se muestran todas para que se
        // arreglen de una pasada en vez de descubrir una nueva en cada intento.
        const detalle = causa.detalle as { errores?: CausaDeRechazo[] } | undefined;
        setCausas(detalle?.errores ?? [{ codigo: causa.codigo ?? "", mensaje: causa.message }]);
      } else {
        setErrorAlGuardar("No se pudo enviar. Inténtalo otra vez.");
      }
    } finally {
      setGuardando(false);
    }
  }

  if (errorDeCarga !== null) {
    return (
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-5 pt-10 sm:px-6">
        <Aviso tono="error" titulo="No se pudo abrir tu chequeo">
          {errorDeCarga}
        </Aviso>
        <Boton tono="contorno" onClick={() => navegar("/inicio")}>
          Volver al inicio
        </Boton>
      </div>
    );
  }

  if (borrador === null) {
    return (
      <div className="mx-auto w-full max-w-2xl px-5 pt-10 sm:px-6">
        <CargandoPantalla que="tu chequeo" texto={2} filas={4} />
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-full w-full max-w-2xl flex-col gap-8 px-5 pt-6 pb-32 sm:px-6">
      {/* ---- Progreso ---- */}
      <header className="flex flex-col gap-5">
        <div className="flex items-center gap-3">
          <Boton tono="discreto" medida="icono" onClick={retroceder} aria-label="Regresar">
            <ArrowLeft className="size-4" />
          </Boton>
          <Etiqueta>
            Chequeo #{borrador.numero} · {fecha(borrador.fecha)}
          </Etiqueta>
        </div>

        {borrador.estado === "rechazado_calidad" ? (
          <Aviso tono="atencion" titulo="Tu coach pidió repetir una toma">
            Este es el mismo chequeo, no uno nuevo. Corrige lo que te señaló y vuelve a enviarlo.
          </Aviso>
        ) : null}

        <ol className="flex gap-1.5" aria-label="Progreso del chequeo">
          {PASOS.map((rotulo, i) => (
            <li key={rotulo} className="flex flex-1 flex-col gap-1.5">
              <span
                className={cn(
                  "h-0.5 rounded-full transition-colors",
                  i < paso ? "bg-acento" : i === paso ? "bg-tinta" : "bg-linea",
                )}
              />
              <span
                className={cn(
                  "text-micro font-medium",
                  i === paso ? "text-tinta" : "text-tinta-suave",
                )}
              >
                {rotulo}
              </span>
            </li>
          ))}
        </ol>
      </header>

      {/* ---- Paso 0: estado fisiológico ---- */}
      {paso === 0 ? (
        <section className="flex flex-col gap-6">
          <div className="flex flex-col gap-3">
            <Portada>Antes de empezar, confirma cómo estás</Portada>
            <Apoyo className="medida">
              Estas condiciones no son burocracia: son lo que hace que tu peso de este mes sea
              comparable con el del mes pasado.
            </Apoyo>
          </div>

          <div className="flex flex-col gap-2">
            {CONDICIONES.map((c) => (
              <Casilla
                key={c.id}
                id={`cond-${c.id}`}
                titulo={c.titulo}
                checked={condiciones.has(c.id)}
                onChange={(e) =>
                  setCondiciones((s) => {
                    const n = new Set(s);
                    if (e.target.checked) n.add(c.id);
                    else n.delete(c.id);
                    // Se anota al marcar, no al avanzar: quien cierra a media casilla las
                    // encuentra igual al volver.
                    guardarCondiciones(borrador.ulid, n);
                    return n;
                  })
                }
              >
                {c.detalle}
              </Casilla>
            ))}
          </div>

          <Aviso tono={puedeAvanzar[0] ? "exito" : "info"}>
            {puedeAvanzar[0]
              ? "Estás en condiciones de chequeo. Vamos por el peso."
              : "Si algo de esto no se cumple, mejor mañana. Un chequeo hecho después de desayunar mide otra cosa; no pasa nada por posponerlo un día."}
          </Aviso>
        </section>
      ) : null}

      {/* ---- Paso 1: peso ---- */}
      {paso === 1 ? (
        <section className="flex flex-col gap-8">
          <div className="flex flex-col gap-3">
            <Portada>Tu peso de hoy</Portada>
            <Apoyo>Sin ropa o con ropa ligera, con la misma báscula de siempre.</Apoyo>
          </div>

          <Campo
            id="peso"
            etiqueta="Peso en ayunas"
            sufijo="kg"
            ayuda={
              previoPeso !== null
                ? `Tu peso del mes pasado fue ${num(previoPeso)} kg.`
                : "Es tu primer pesaje: no hay con qué compararlo todavía."
            }
          >
            <Entrada
              id="peso"
              type="number"
              step="0.1"
              min={30}
              max={250}
              inputMode="decimal"
              placeholder="0.0"
              value={peso}
              onChange={(e) => {
                setPeso(e.target.value);
                setVarianzaConfirmada(false);
              }}
              className="rounded-r-none text-titulo"
            />
          </Campo>

          {pesoNum && (pesoNum < 30 || pesoNum > 250) ? (
            <Aviso tono="error" titulo="Ese peso está fuera de rango">
              Aceptamos entre 30.0 y 250.0 kg. Revisa que no se te haya ido un dígito.
            </Aviso>
          ) : magnitud > 0.03 ? (
            <Aviso
              tono={magnitud > 0.1 ? "error" : "atencion"}
              titulo={`Cambio de ${num(magnitud * 100)} %`}
            >
              {magnitud > 0.1
                ? "Es un salto grande para un mes. Tu coach verá una alerta y te va a preguntar."
                : "Es más de lo habitual en un mes. Confirma el dato o vuelve a pesarte."}
              <div className="mt-3">
                <Casilla
                  id="confirmar-varianza"
                  titulo="Confirmo que el dato es correcto"
                  checked={varianzaConfirmada}
                  onChange={(e) => setVarianzaConfirmada(e.target.checked)}
                />
              </div>
            </Aviso>
          ) : pesoNum ? (
            <Aviso tono="exito" titulo="Anotado">
              Cambio de {num(magnitud * 100)} % respecto al mes pasado. Dentro de lo esperado.
            </Aviso>
          ) : null}

          <Regla />

          {/* Hasta 3 pesajes por ciclo: el promedio quita el ruido de un día de retención. */}
          <div className="flex flex-col gap-3">
            <div className="flex items-baseline justify-between gap-3">
              <Titulo>Tus pesajes de este ciclo</Titulo>
              <Chip>
                {pesajes.length} de {borrador.maxPesajes}
              </Chip>
            </div>
            <Apoyo>
              Puedes pesarte hasta en {borrador.maxPesajes} días distintos. Se promedian para
              quitar el ruido de un día raro.
            </Apoyo>

            {pesajes.length ? (
              <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
                {pesajes.map((p) => (
                  <li key={p.fecha} className="flex items-baseline justify-between gap-3 py-2.5">
                    <span className="text-menor">{fecha(p.fecha)}</span>
                    <span className="cifra font-semibold">{num(p.pesoKg)} kg</span>
                  </li>
                ))}
              </ul>
            ) : null}

            {promedio !== null && pesajes.length > 1 ? (
              <Aviso tono="exito" titulo={`Promedio: ${num(promedio)} kg`}>
                Sale de tus {pesajes.length} pesajes. Es el número que tu coach usará para
                ajustar tu plan.
              </Aviso>
            ) : (
              <Apoyo>Con un solo pesaje usamos ese. Si te pesas otro día del ciclo, promediamos.</Apoyo>
            )}
          </div>

          <Regla />

          <div className="flex flex-col gap-3">
            <Titulo>¿Todo igual que el mes pasado?</Titulo>
            <Apoyo>Si cambia el lugar o la hora el dato sigue sirviendo; solo se lo anotamos a tu coach.</Apoyo>
            <div className="flex flex-col gap-2">
              <Casilla
                id="e-bascula"
                titulo="Misma báscula"
                checked={entorno.bascula}
                onChange={(e) => setEntorno((v) => ({ ...v, bascula: e.target.checked }))}
              >
                {borrador.basculaRef ?? "La que usaste la vez pasada"}
              </Casilla>
              <Casilla
                id="e-lugar"
                titulo="Mismo lugar"
                checked={entorno.lugar}
                onChange={(e) => setEntorno((v) => ({ ...v, lugar: e.target.checked }))}
              >
                {borrador.lugarRef ?? "Donde te pesaste la vez pasada"}
              </Casilla>
              <Casilla
                id="e-hora"
                titulo="Misma hora"
                checked={entorno.hora}
                onChange={(e) => setEntorno((v) => ({ ...v, hora: e.target.checked }))}
              >
                {borrador.horaRef ? `Alrededor de las ${borrador.horaRef}` : "A la hora de siempre"}
              </Casilla>
            </div>
            {!entorno.bascula || !entorno.lugar || !entorno.hora ? (
              <Aviso tono="atencion" titulo="Cambió algo del entorno">
                No bloquea tu chequeo. Se lo anotamos a tu coach para que lo tome en cuenta al
                comparar.
              </Aviso>
            ) : null}
          </div>
        </section>
      ) : null}

      {/* ---- Paso 2: las ocho medidas ---- */}
      {paso === 2 ? (
        <section className="flex flex-col gap-6">
          <div className="flex flex-col gap-3">
            <Portada>Las ocho medidas</Portada>
            <Apoyo className="medida">
              Cinta paralela al piso, apretada sin marcar la piel. Toca «¿dónde?» si dudas.
            </Apoyo>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            {MEDIDAS.map((m) => {
              const valor = medidas[m.tipo];
              const anterior = previoMedidas[m.tipo];
              const d = valor && anterior ? delta(valor, anterior, "cm") : null;
              const problema = problemaDeMedida(m, textoMedidas[m.tipo]);
              return (
                <Campo
                  key={m.tipo}
                  id={`m-${m.tipo}`}
                  etiqueta={m.rotulo}
                  sufijo="cm"
                  {...(problema ? { error: problema } : {})}
                  ayuda={
                    <span className="flex items-center gap-2">
                      <span>{anterior ? `Mes pasado: ${num(anterior)} cm` : "Sin referencia previa"}</span>
                      {d ? <strong className="font-semibold">{d.texto}</strong> : null}
                      <button
                        type="button"
                        onClick={() => setAyudaDe(m.tipo)}
                        className="ml-auto underline underline-offset-2"
                      >
                        ¿Dónde?
                      </button>
                    </span>
                  }
                >
                  <Entrada
                    id={`m-${m.tipo}`}
                    type="number"
                    step="0.1"
                    min={m.min}
                    max={m.max}
                    inputMode="decimal"
                    placeholder="0.0"
                    value={textoMedidas[m.tipo] ?? ""}
                    onChange={(e) =>
                      setTextoMedidas((prev) => ({ ...prev, [m.tipo]: e.target.value }))
                    }
                    aria-invalid={problema ? true : undefined}
                    className={cn(
                      "rounded-r-none",
                      problema && "border-peligro focus:border-peligro",
                    )}
                  />
                </Campo>
              );
            })}
          </div>

          {fueraDeRango.length > 0 ? (
            <Aviso tono="error" titulo="Revisa estas medidas">
              {fueraDeRango.join(", ")}: el valor está fuera de lo que aceptamos. Casi
              siempre es un dígito de más o de menos.
            </Aviso>
          ) : null}

          <Apoyo>
            <strong className="cifra font-semibold text-tinta">{medidasListas}</strong> de{" "}
            {MEDIDAS.length} capturadas
          </Apoyo>
        </section>
      ) : null}

      {/* ---- Paso 3: las tres fotos ---- */}
      {paso === 3 ? (
        <section className="flex flex-col gap-6">
          <div className="flex flex-col gap-3">
            <Portada>Tus tres fotos</Portada>
            <Apoyo className="medida">
              Del cuello para abajo. El servidor recorta la cabeza antes de guardar nada: esa
              parte de la imagen no llega a existir en el disco.
            </Apoyo>
          </div>

          <Aviso tono="info" titulo="Cómo salen bien a la primera">
            Luz natural de frente, nunca a tus espaldas. Pared clara y lisa. Brazos colgando,
            abdomen relajado — sin meterlo. Short y top de color liso.
          </Aviso>

          <div className="grid gap-4 sm:grid-cols-3">
            {ANGULOS.map((a) => (
              <CapturaDeFoto
                key={a.id}
                angulo={a.id}
                rotulo={a.rotulo}
                guia={a.guia}
                chequeoUlid={borrador.ulid}
                estado={fotos.find((f) => f.angulo === a.id) ?? null}
                onCambio={setBorrador}
              />
            ))}
          </div>

          <Apoyo>
            <strong className="cifra font-semibold text-tinta">{fotosListas}</strong> de{" "}
            {ANGULOS.length} capturadas
          </Apoyo>
        </section>
      ) : null}

      {/* ---- Paso 4: revisión y envío ---- */}
      {paso === 4 ? (
        <section className="flex flex-col gap-8">
          <div className="flex flex-col gap-3">
            <Portada>Revisa antes de enviar</Portada>
            <Apoyo>Después de enviarlo ya no se puede editar: tu coach lo revisa tal cual.</Apoyo>
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <Etiqueta>Peso</Etiqueta>
              <p className="cifra text-portada font-semibold tracking-[-0.03em]">
                {num(pesoNum)} <span className="text-guia font-medium text-tinta-suave">kg</span>
              </p>
              {previoPeso !== null ? (
                <p className="text-menor text-tinta-media">{delta(pesoNum, previoPeso, "kg")?.texto}</p>
              ) : null}
            </div>
            <div className="flex flex-col gap-1">
              <Etiqueta>Fotos</Etiqueta>
              <p className="cifra text-portada font-semibold tracking-[-0.03em]">
                {fotosListas} <span className="text-guia font-medium text-tinta-suave">de 3</span>
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-3">
            <Titulo>Las ocho medidas</Titulo>
            <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
              {MEDIDAS.map((m) => {
                const valor = medidas[m.tipo];
                const anterior = previoMedidas[m.tipo];
                const d = valor && anterior ? delta(valor, anterior, "cm") : null;
                return (
                  <li key={m.tipo} className="flex items-baseline justify-between gap-3 py-2.5">
                    <span className="text-menor">{m.rotulo}</span>
                    <span className="flex items-baseline gap-3">
                      <span className="cifra text-menor text-tinta-suave">
                        {anterior ? num(anterior) : "—"}
                      </span>
                      <span className="cifra font-semibold">{valor ? num(valor) : "—"} cm</span>
                      {d ? (
                        <span className="cifra w-16 text-right text-menor text-tinta-media">
                          {d.texto}
                        </span>
                      ) : null}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>

          <Campo id="nota" etiqueta="¿Algo que tu coach deba saber? (opcional)">
            <textarea
              id="nota"
              value={nota}
              onChange={(e) => setNota(e.target.value)}
              rows={3}
              className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
              placeholder="Por ejemplo: dormí mal toda la semana, o me lastimé la rodilla el martes."
            />
          </Campo>

          {causas.length ? (
            <Aviso tono="error" titulo="Falta algo para poder enviarlo">
              <ul className="flex list-disc flex-col gap-1 pl-4">
                {causas.map((c) => (
                  <li key={c.codigo}>{c.mensaje}</li>
                ))}
              </ul>
            </Aviso>
          ) : null}
        </section>
      ) : null}

      {errorAlGuardar ? (
        <Aviso tono="error" titulo="No se pudo guardar">
          {errorAlGuardar}
        </Aviso>
      ) : null}

      {/* ---- Acción fija al pie: el botón nunca queda fuera de vista ---- */}
      <div
        className="fixed inset-x-0 bottom-0 border-t border-linea bg-fondo/95 px-5 py-3 backdrop-blur sm:px-6"
        style={{ paddingBottom: "calc(0.75rem + env(safe-area-inset-bottom))" }}
      >
        <div className="mx-auto flex max-w-2xl gap-3">
          <Boton tono="contorno" onClick={retroceder} disabled={guardando}>
            {paso === 0 ? "Lo hago mañana" : "Atrás"}
          </Boton>
          <Boton
            className="flex-1"
            medida="grande"
            cargando={guardando}
            disabled={!puedeAvanzar[paso] || guardando}
            onClick={paso === 4 ? enviar : avanzar}
          >
            {paso === 4 ? "Enviar a mi coach" : "Continuar"}
          </Boton>
        </div>
      </div>

      {/* ---- Ayuda de medida ---- */}
      <Dialogo
        abierto={ayudaDe !== null}
        onCambio={(v) => !v && setAyudaDe(null)}
        etiqueta="Dónde medir"
        titulo={MEDIDAS.find((m) => m.tipo === ayudaDe)?.rotulo ?? ""}
        pie={
          <Boton medida="chica" onClick={() => setAyudaDe(null)}>
            Entendido
          </Boton>
        }
      >
        <p className="text-cuerpo leading-relaxed">{MEDIDAS.find((m) => m.tipo === ayudaDe)?.ayuda}</p>
        <Aviso tono="info">
          Rango aceptado: {MEDIDAS.find((m) => m.tipo === ayudaDe)?.min} a{" "}
          {MEDIDAS.find((m) => m.tipo === ayudaDe)?.max} cm. Si tu medida cae fuera, casi siempre
          es la cinta mal puesta.
        </Aviso>
      </Dialogo>

      {/* ---- Enviado ---- */}
      <Dialogo
        abierto={enviado}
        onCambio={(v) => !v && navegar("/inicio")}
        etiqueta="Enviado"
        titulo="Tu chequeo ya está con tu coach"
        pie={
          <Boton medida="chica" onClick={() => navegar("/inicio")}>
            Volver al inicio
          </Boton>
        }
      >
        <p className="flex items-center gap-3 text-cuerpo">
          <Check className="size-5 shrink-0 text-exito" />
          Te avisamos en cuanto lo revise. Suele tardar menos de 48 horas.
        </p>
      </Dialogo>
    </div>
  );
}

/* ------------------------------------------------------------- Una toma --- */

interface CapturaProps {
  angulo: Angulo;
  rotulo: string;
  guia: string;
  chequeoUlid: string;
  estado: { estadoAuto: string; nitidez: number | null; luminancia: number | null } | null;
  onCambio: (b: BorradorApi) => void;
}

/** Una de las tres tomas. La miniatura que se enseña es la del servidor, ya recortada: con
 *  la del archivo local la alumna vería su cara y creería que eso se guardó.
 */
function CapturaDeFoto({ angulo, rotulo, guia, chequeoUlid, estado, onCambio }: CapturaProps) {
  const entrada = useRef<HTMLInputElement>(null);
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [motivo, setMotivo] = useState<string | null>(null);
  // Cambia en cada subida para que el navegador no sirva la miniatura anterior desde su caché.
  const [version, setVersion] = useState(0);

  const lista = estado !== null;
  const rechazada = estado?.estadoAuto === "rechazada";

  async function subir(archivo: File) {
    setError(null);
    setSubiendo(true);
    try {
      const resultado = await api.alumna.subirFoto(chequeoUlid, angulo, archivo);
      setMotivo(resultado.motivoRechazo);
      setVersion((v) => v + 1);
      onCambio(await api.alumna.abrirChequeo());
    } catch (causa: unknown) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo subir la foto.");
    } finally {
      setSubiendo(false);
      if (entrada.current) entrada.current.value = "";
    }
  }

  async function repetir() {
    setSubiendo(true);
    try {
      await api.alumna.borrarFoto(chequeoUlid, angulo);
      setMotivo(null);
      onCambio(await api.alumna.abrirChequeo());
    } catch (causa: unknown) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo borrar la foto.");
    } finally {
      setSubiendo(false);
    }
  }

  return (
    <article className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-menor font-semibold">{rotulo}</h3>
        {rechazada ? (
          <Chip tono="espera">Revisar</Chip>
        ) : lista ? (
          <Chip tono="exito">Lista</Chip>
        ) : (
          <Chip>Falta</Chip>
        )}
      </div>

      <div className="relative grid aspect-3/4 place-items-center overflow-hidden rounded-marco border border-linea-fuerte bg-fondo-sutil">
        {lista ? (
          <img
            src={`${urlDeFoto(chequeoUlid, angulo, true)}${version ? `&v=${version}` : ""}`}
            alt={`Tu toma ${rotulo.toLowerCase()}, ya recortada`}
            className="size-full object-cover"
          />
        ) : (
          <SiluetaGuia />
        )}
        <p className="absolute inset-x-2 bottom-2 rounded-marco bg-tinta px-2 py-1.5 text-center text-micro font-medium text-fondo">
          {subiendo ? "Procesando…" : lista ? "Recortada y guardada" : guia}
        </p>
      </div>

      {motivo ? (
        <Aviso tono="atencion" titulo="Se puede mejorar">
          {motivo}
        </Aviso>
      ) : null}
      {error ? <Aviso tono="error">{error}</Aviso> : null}

      <input
        ref={entrada}
        type="file"
        accept="image/*"
        // `capture` abre la cámara directamente en el teléfono; en escritorio se ignora y
        // sale el selector de archivos de siempre.
        capture="environment"
        className="hidden"
        onChange={(e) => {
          const archivo = e.target.files?.[0];
          if (archivo) void subir(archivo);
        }}
      />

      <Boton
        tono={lista ? "contorno" : "solido"}
        ancho="completo"
        medida="chica"
        cargando={subiendo}
        onClick={() => (lista ? void repetir() : entrada.current?.click())}
      >
        {subiendo ? null : lista ? (
          <>
            <RotateCcw className="size-3.5" /> Repetir
          </>
        ) : (
          <>
            <Camera className="size-3.5" /> Capturar
          </>
        )}
      </Boton>
    </article>
  );
}

/** Silueta esquemática sin rostro: el encuadre empieza en el cuello, por diseño. */
function SiluetaGuia() {
  return (
    <svg viewBox="0 0 120 160" className="absolute inset-0 size-full" aria-hidden="true">
      <line x1="8" y1="30" x2="112" y2="30" stroke="var(--tinta)" strokeWidth="0.8" strokeDasharray="3 3" />
      <text x="60" y="25" textAnchor="middle" fontSize="6" fontWeight="600" fill="var(--tinta-media)">
        línea del cuello
      </text>
      <g fill="none" stroke="var(--tinta-suave)" strokeWidth="1" strokeDasharray="3 3">
        <path d="M60 32 C48 32 44 38 42 46 L36 78 M60 32 C72 32 76 38 78 46 L84 78" />
        <path d="M42 46 L42 92 L78 92 L78 46" />
        <path d="M36 78 L33 108 M84 78 L87 108" />
        <path d="M46 92 L44 148 M74 92 L76 148" />
      </g>
    </svg>
  );
}
