/** La conversación entre alumna y coach.
 *
 *  El mismo componente sirve a los dos frentes: cambia quién es «yo» y de dónde salen los
 *  mensajes, no cómo se leen. Duplicarlo habría garantizado que uno de los dos se quedara
 *  atrás en la siguiente corrección.
 *
 *  **No hay tiempo real.** El hilo se recarga al abrirlo y al enviar. Un websocket para un
 *  puñado de mensajes al día costaría una conexión abierta por alumna, un proceso más en el
 *  VPS y un modo de fallo nuevo, a cambio de nada que se note.
 */

import { Loader2, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Apoyo, Aviso, Boton, Vacio } from "@/componentes/primitivas";
import { Cargando } from "@/componentes/Estado";
import { ErrorApi, type MensajeApi } from "@/lib/api";
import { cn } from "@/lib/utils";

interface HiloProps {
  /** Quién escribe desde esta pantalla. Determina de qué lado se pinta cada burbuja. */
  yo: "alumna" | "coach";
  cargar: (senal: AbortSignal) => Promise<MensajeApi[]>;
  enviar: (cuerpo: string) => Promise<MensajeApi>;
  /** Cómo llamar a la otra persona cuando el hilo está vacío. */
  contraparte: string;
}

const LARGO_MAXIMO = 4000;

export function Hilo({ yo, cargar, enviar, contraparte }: HiloProps) {
  const [mensajes, setMensajes] = useState<MensajeApi[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const fondo = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const control = new AbortController();
    cargar(control.signal)
      .then((filas) => {
        if (!control.signal.aborted) setMensajes(filas);
      })
      .catch((causa: unknown) => {
        if (control.signal.aborted) return;
        setError(causa instanceof ErrorApi ? causa.message : "No se pudo abrir la conversación.");
        setMensajes([]);
      });
    return () => control.abort();
    // `cargar` se recrea en cada render de quien llama; la dependencia real la declara él.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Al último mensaje, que es el que importa al abrir.
  useEffect(() => {
    fondo.current?.scrollIntoView({ block: "end" });
  }, [mensajes?.length]);

  async function mandar() {
    const limpio = texto.trim();
    if (!limpio) return;

    setError(null);
    setEnviando(true);
    try {
      const nuevo = await enviar(limpio);
      setMensajes((previos) => [...(previos ?? []), nuevo]);
      setTexto("");
    } catch (causa: unknown) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo enviar tu mensaje.");
    } finally {
      setEnviando(false);
    }
  }

  if (mensajes === null) return <Cargando que="la conversación" />;

  return (
    <div className="flex flex-col gap-5">
      {error ? <Aviso tono="error">{error}</Aviso> : null}

      {mensajes.length === 0 ? (
        <Vacio>Todavía no hay mensajes con {contraparte}. Escribe el primero.</Vacio>
      ) : (
        <ol className="flex flex-col gap-3">
          {mensajes.map((m) => {
            const mio = m.autor === yo;
            return (
              <li key={m.ulid} className={cn("flex", mio ? "justify-end" : "justify-start")}>
                <div
                  className={cn(
                    "flex max-w-[80%] flex-col gap-1 rounded-marco px-4 py-3 text-menor leading-relaxed",
                    mio ? "bg-tinta text-fondo" : "border border-linea bg-fondo-sutil",
                  )}
                >
                  <p className="whitespace-pre-wrap">{m.cuerpo}</p>
                  <span
                    className={cn(
                      "text-micro tabular-nums",
                      mio ? "text-fondo/70" : "text-tinta-suave",
                    )}
                  >
                    {momento(m.enviadoEn)}
                    {mio && m.leidoEn ? " · leído" : ""}
                  </span>
                </div>
              </li>
            );
          })}
        </ol>
      )}
      <div ref={fondo} />

      <form
        className="flex flex-col gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void mandar();
        }}
      >
        <label htmlFor="mensaje" className="sr-only">
          Escribe tu mensaje
        </label>
        <textarea
          id="mensaje"
          rows={3}
          maxLength={LARGO_MAXIMO}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Escribe aquí…"
          className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
        />
        <div className="flex items-center justify-between gap-3">
          <Apoyo>
            {yo === "alumna"
              ? "Para dudas del plan. Si es una urgencia médica, acude a un servicio de salud."
              : "Lo que escribas aquí lo lee tu alumna tal cual."}
          </Apoyo>
          <Boton type="submit" disabled={enviando || !texto.trim()}>
            {enviando ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
            Enviar
          </Boton>
        </div>
      </form>
    </div>
  );
}

/** Fecha corta y hora. Un hilo de meses necesita el día; uno de hoy, la hora. */
function momento(iso: string): string {
  const cuando = new Date(iso);
  const hoy = new Date();
  const mismoDia = cuando.toDateString() === hoy.toDateString();
  return mismoDia
    ? cuando.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" })
    : cuando.toLocaleString("es-MX", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
}
