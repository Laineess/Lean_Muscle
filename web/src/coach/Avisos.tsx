/** Avisos de la coach: un título, una frase y a quién va.
 *
 *  No es el hilo de mensajes: aquello es una conversación de dos y esto va en una dirección.
 *
 *  Sale por push, no por correo: una frase de ánimo en la bandeja de entrada es correo
 *  basura, y entonces el que sí importa —acceso, dinero— también se aprende a ignorar.
 */

import { Send } from "lucide-react";
import { useState } from "react";

import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Chip,
  Entrada,
  Etiqueta,
  Portada,
  Regla,
  Titulo,
  Vacio,
} from "@/componentes/primitivas";
import { ErrorApi, api, type AnuncioApi, type FilaCarteraApi } from "@/lib/api";
import { fecha } from "@/lib/formato";
import { usarApi } from "@/lib/usarApi";
import { cn } from "@/lib/utils";

/** Lo que cabe en la notificación de un teléfono sin que se recorte. */
const LARGO_TITULO = 80;
const LARGO_CUERPO = 300;

export function Avisos() {
  const historial = usarApi<AnuncioApi[]>((s) => api.coach.anuncios(s), []);
  const cartera = usarApi<FilaCarteraApi[]>((s) => api.coach.alumnas(s), []);

  const [titulo, setTitulo] = useState("");
  const [cuerpo, setCuerpo] = useState("");
  const [elegidas, setElegidas] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);
  const [hecho, setHecho] = useState<string | null>(null);

  const activas = (cartera.datos ?? []).filter((a) => a.estado === "activa");
  const listo = titulo.trim().length > 0 && cuerpo.trim().length > 0 && activas.length > 0;

  function alternar(ulid: string) {
    setElegidas((antes) =>
      antes.includes(ulid) ? antes.filter((u) => u !== ulid) : [...antes, ulid],
    );
  }

  async function enviar() {
    setFallo(null);
    setHecho(null);
    setEnviando(true);
    try {
      const r = await api.coach.enviarAnuncio({
        titulo: titulo.trim(),
        cuerpo: cuerpo.trim(),
        alumnas: elegidas,
      });
      setTitulo("");
      setCuerpo("");
      setElegidas([]);
      setHecho(
        r.enviadas === 1 ? "Enviado a una alumna." : `Enviado a ${r.enviadas} alumnas.`,
      );
      historial.recargar();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo enviar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta>Avisos</Etiqueta>
        <Portada>Escríbele a tus alumnas</Portada>
        <Apoyo className="medida">
          Les llega como notificación al teléfono. Va en una sola dirección: si quieres
          conversar con una, usa su hilo de mensajes.
        </Apoyo>
      </header>

      <section className="flex max-w-xl flex-col gap-4">
        <Campo id="av-titulo" etiqueta="Título" ayuda={`${titulo.length} de ${LARGO_TITULO}`}>
          <Entrada
            id="av-titulo"
            value={titulo}
            maxLength={LARGO_TITULO}
            onChange={(e) => setTitulo(e.target.value)}
            placeholder="Lunes de arranque"
          />
        </Campo>

        <Campo id="av-cuerpo" etiqueta="Mensaje" ayuda={`${cuerpo.length} de ${LARGO_CUERPO}`}>
          <textarea
            id="av-cuerpo"
            value={cuerpo}
            maxLength={LARGO_CUERPO}
            rows={3}
            onChange={(e) => setCuerpo(e.target.value)}
            placeholder="No tiene que ser perfecto, tiene que ser hoy."
            className="w-full rounded-marco border border-linea bg-fondo px-3 py-2.5 text-cuerpo placeholder:text-tinta-suave focus:border-tinta focus:outline-none"
          />
        </Campo>

        <div className="flex flex-col gap-2">
          <Etiqueta>
            {elegidas.length === 0
              ? `A todas tus alumnas activas (${activas.length})`
              : `A ${elegidas.length} de ${activas.length}`}
          </Etiqueta>
          <Apoyo>Sin elegir a nadie va a todas. Toca un nombre para mandarlo solo a ella.</Apoyo>
          {activas.length === 0 ? (
            <Vacio>No tienes alumnas activas.</Vacio>
          ) : (
            <div className="flex flex-wrap gap-2">
              {activas.map((a) => (
                <button
                  key={a.ulid}
                  type="button"
                  aria-pressed={elegidas.includes(a.ulid)}
                  onClick={() => alternar(a.ulid)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-micro font-medium transition-colors",
                    elegidas.includes(a.ulid)
                      ? "border-acento bg-acento-sutil text-tinta"
                      : "border-linea text-tinta-suave hover:text-tinta",
                  )}
                >
                  {a.nombre.split(" ")[0]}
                </button>
              ))}
            </div>
          )}
        </div>

        {fallo ? <Aviso tono="error">{fallo}</Aviso> : null}
        {hecho ? <Aviso tono="exito">{hecho}</Aviso> : null}

        <div>
          <Boton disabled={!listo || enviando} onClick={() => void enviar()}>
            <Send className="size-4" /> {enviando ? "Enviando…" : "Enviar"}
          </Boton>
        </div>
      </section>

      <Regla />

      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <Titulo>Lo que ya mandaste</Titulo>
          <Apoyo>
            Cada aviso <strong>se borra solo</strong> cuando todas lo abren, y a la semana
            aunque no lo hayan abierto. Son frases del día, no un archivo.
          </Apoyo>
        </div>
        {historial.cargando ? null : (historial.datos ?? []).length === 0 ? (
          <Vacio>Nada pendiente. Lo que mandaste y ya leyeron desaparece de aquí.</Vacio>
        ) : (
          <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
            {(historial.datos ?? []).map((a) => (
              <li key={a.ulid} className="flex flex-col gap-1.5 py-4">
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <span className="text-menor font-medium">{a.titulo}</span>
                  <span className="flex items-center gap-3">
                    <span className="text-micro text-tinta-suave">{fecha(a.enviadoEn)}</span>
                    <Chip tono={a.leidas === a.enviadas ? "exito" : "neutro"}>
                      {a.leidas} de {a.enviadas} lo abrieron
                    </Chip>
                  </span>
                </div>
                <p className="medida text-menor text-tinta-media">{a.cuerpo}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
