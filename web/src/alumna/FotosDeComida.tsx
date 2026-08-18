/** Fotos de las comidas: las manda la alumna y se borran solas a las 36 horas.
 *
 *  La ventana corta va escrita en la pantalla: es lo único que hace razonable pedirle a
 *  alguien que fotografíe lo que come. Si su coach no le pide fotos, esto no aparece.
 */

import { Camera, Clock, Trash2 } from "lucide-react";
import { useRef, useState } from "react";

import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Chip,
  Entrada,
  Titulo,
  Vacio,
} from "@/componentes/primitivas";
import {
  ErrorApi,
  api,
  urlDeFotoDeComida,
  type FotoDeComidaApi,
  type FotosDeComidaApi,
} from "@/lib/api";
import { fecha } from "@/lib/formato";
import { usarApi } from "@/lib/usarApi";

/** Cuánto le queda a una foto, en palabras. */
function cuantoLeQueda(expiraEn: string): string {
  const minutos = Math.round((new Date(expiraEn).getTime() - Date.now()) / 60000);
  if (minutos <= 0) return "se está borrando";
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  return horas < 24 ? `${horas} h` : `${Math.floor(horas / 24)} d ${horas % 24} h`;
}

export function FotosDeComida() {
  const carga = usarApi<FotosDeComidaApi>((s) => api.alumna.fotosDeComida(s));
  const [tiempo, setTiempo] = useState("");
  const [nota, setNota] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);
  const entrada = useRef<HTMLInputElement>(null);

  const d = carga.datos;
  // Sin frecuencia no hay nada que pedirle: la pantalla ni siquiera aparece.
  if (carga.cargando || !d || d.frecuencia === "ninguna") return null;

  async function subir(archivo: File) {
    setFallo(null);
    setOcupado(true);
    try {
      await api.alumna.subirFotoDeComida(archivo, tiempo, nota);
      setTiempo("");
      setNota("");
      carga.recargar();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo subir la foto.");
    } finally {
      setOcupado(false);
      if (entrada.current) entrada.current.value = "";
    }
  }

  async function borrar(ulid: string) {
    setFallo(null);
    try {
      await api.alumna.borrarFotoDeComida(ulid);
      carga.recargar();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo borrar.");
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <Titulo>Fotos de tus comidas</Titulo>
        {d.cumplido ? (
          <Chip tono="exito">Al corriente</Chip>
        ) : (
          <Chip tono="espera">Te toca</Chip>
        )}
      </div>

      <Apoyo>
        {d.rotulo}. {d.hasta ? `Tienes hasta el ${fecha(d.hasta)}.` : ""} Cada foto{" "}
        <strong>se borra sola a las 36 horas</strong> de que la mandas.
      </Apoyo>

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="fc-tiempo" etiqueta="Qué comida es">
          <Entrada
            id="fc-tiempo"
            value={tiempo}
            onChange={(e) => setTiempo(e.target.value)}
            placeholder="Comida del martes"
          />
        </Campo>
        <Campo id="fc-nota" etiqueta="Nota (opcional)">
          <Entrada
            id="fc-nota"
            value={nota}
            onChange={(e) => setNota(e.target.value)}
            placeholder="Me quedé con hambre."
          />
        </Campo>
      </div>

      <input
        ref={entrada}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => {
          const archivo = e.target.files?.[0];
          if (archivo) void subir(archivo);
        }}
      />
      <div>
        <Boton disabled={ocupado} onClick={() => entrada.current?.click()}>
          <Camera className="size-4" /> {ocupado ? "Subiendo…" : "Tomar o elegir foto"}
        </Boton>
      </div>

      {fallo ? <Aviso tono="error">{fallo}</Aviso> : null}

      {d.fotos.length === 0 ? (
        <Vacio>No tienes fotos vigentes.</Vacio>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-3">
          {d.fotos.map((f) => (
            <Tarjeta key={f.ulid} f={f} onBorrar={() => void borrar(f.ulid)} />
          ))}
        </ul>
      )}
    </section>
  );
}

function Tarjeta({ f, onBorrar }: { f: FotoDeComidaApi; onBorrar: () => void }) {
  return (
    <li className="flex flex-col overflow-hidden rounded-marco border border-linea">
      <img
        src={urlDeFotoDeComida(f.ulid)}
        alt={f.tiempo ?? "Foto de comida"}
        className="aspect-square w-full object-cover"
      />
      <div className="flex flex-1 flex-col gap-1.5 p-3">
        {f.tiempo ? <span className="text-menor font-medium">{f.tiempo}</span> : null}
        {f.nota ? <span className="text-micro text-tinta-media">{f.nota}</span> : null}
        {f.comentario ? (
          <span className="border-l-2 border-l-acento pl-2 text-micro text-tinta-media">
            {f.comentario}
          </span>
        ) : null}
        <span className="mt-auto flex items-center justify-between gap-2 pt-1">
          <span className="flex items-center gap-1 text-micro text-tinta-suave">
            <Clock className="size-3" /> {cuantoLeQueda(f.expiraEn)}
          </span>
          <Boton tono="discreto" medida="icono" aria-label="Borrar ahora" onClick={onBorrar}>
            <Trash2 className="size-3.5" />
          </Boton>
        </span>
      </div>
    </li>
  );
}
