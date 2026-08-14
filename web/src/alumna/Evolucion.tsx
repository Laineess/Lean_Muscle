/** Evolución: comparativa visual, gráficas e historial.
 *
 *  Con retención de 4 meses, un chequeo viejo conserva sus números pero ya no su foto. La
 *  pantalla lo dice en lugar de fingir que la tiene: prometer un «antes y después» que el
 *  sistema ya borró es peor que explicar por qué no está.
 */

import { useState } from "react";

import { AvisoSinServidor, Cargando } from "@/componentes/Estado";
import { Grafica } from "@/componentes/Grafica";
import { Apoyo, Aviso, Boton, Chip, Etiqueta, Portada, Regla, Selector, Titulo, Vacio } from "@/componentes/primitivas";
import { api, type ChequeoApi, type InicioAlumnaApi } from "@/lib/api";
import { HOY, chequeos as chequeosEjemplo } from "@/lib/datos";
import { delta, fecha, fechaCorta, num, porcentaje } from "@/lib/formato";
import { usarApiConRespaldo } from "@/lib/usarApi";
import {
  ANGULOS,
  ROTULO_ESTADO,
  ROTULO_MEDIDA,
  type Angulo,
  type EstadoChequeo,
  type TipoMedida,
} from "@/lib/tipos";

const DIAS_RETENCION = 120;

function estaPurgada(iso: string): boolean {
  return (new Date(HOY).getTime() - new Date(iso).getTime()) / 86_400_000 > DIAS_RETENCION;
}

export function Evolucion() {
  const [izquierda, setIzquierda] = useState(0);
  const [derecha, setDerecha] = useState(-1);
  const [angulo, setAngulo] = useState<Angulo>("frontal");

  // Misma llamada que Inicio: el historial completo viene en una sola petición.
  const { datos, cargando, sinServidor, mensaje } = usarApiConRespaldo<Pick<InicioAlumnaApi, "chequeos">>(
    (senal) => api.alumna.inicio(senal),
    { chequeos: chequeosEjemplo },
  );

  if (cargando) return <Cargando que="tu evolución" />;

  const chequeos = datos.chequeos;
  if (chequeos.length < 2) {
    return <Vacio>Con un solo chequeo todavía no hay nada que comparar. Vuelve el mes que entra.</Vacio>;
  }

  const iA = Math.min(izquierda, chequeos.length - 1);
  const iB = derecha < 0 ? chequeos.length - 1 : Math.min(derecha, chequeos.length - 1);
  const a = chequeos[iA]!;
  const b = chequeos[iB]!;

  return (
    <div className="flex flex-col gap-12">
      {sinServidor ? <AvisoSinServidor mensaje={mensaje} /> : null}

      <header className="flex flex-col gap-3">
        <Etiqueta>
          {chequeos.length} chequeos · desde {fecha(chequeos[0]!.fecha)}
        </Etiqueta>
        <Portada>Tu evolución</Portada>
      </header>

      <Aviso tono="atencion" titulo="Tus fotos de abril se borran en 15 días">
        La retención es de 4 meses. Si quieres conservarlas, descarga tu set completo antes.
      </Aviso>

      {/* ---- Comparativa ---- */}
      <section className="flex flex-col gap-5">
        <Titulo>Antes y ahora</Titulo>

        <div className="grid gap-3 sm:grid-cols-3">
          <label className="flex flex-col gap-1.5">
            <span className="text-micro font-semibold uppercase tracking-[0.08em] text-tinta-media">
              Comparar
            </span>
            <Selector value={iA} onChange={(e) => setIzquierda(Number(e.target.value))}>
              {chequeos.map((c, i) => (
                <option key={c.ulid} value={i}>
                  #{c.numero} · {fecha(c.fecha)}
                </option>
              ))}
            </Selector>
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-micro font-semibold uppercase tracking-[0.08em] text-tinta-media">
              Contra
            </span>
            <Selector value={iB} onChange={(e) => setDerecha(Number(e.target.value))}>
              {chequeos.map((c, i) => (
                <option key={c.ulid} value={i}>
                  #{c.numero} · {fecha(c.fecha)}
                </option>
              ))}
            </Selector>
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-micro font-semibold uppercase tracking-[0.08em] text-tinta-media">
              Ángulo
            </span>
            <Selector value={angulo} onChange={(e) => setAngulo(e.target.value as Angulo)}>
              {ANGULOS.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.rotulo}
                </option>
              ))}
            </Selector>
          </label>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Marco chequeo={a} rotulo="Antes" angulo={angulo} />
          <Marco chequeo={b} rotulo="Ahora" angulo={angulo} />
        </div>

        <dl className="flex flex-wrap justify-center gap-x-10 gap-y-4">
          {(
            [
              // `medidas` llega como diccionario, así que con índices sin verificar el tipo
              // es `number | undefined`. Un chequeo viejo puede no traer todas.
              ["Peso", b.pesoKg ?? 0, a.pesoKg ?? 0, "kg"],
              ["Cintura", b.medidas.cintura ?? 0, a.medidas.cintura ?? 0, "cm"],
              ["Abdomen", b.medidas.abdomen ?? 0, a.medidas.abdomen ?? 0, "cm"],
              ["Brazo", b.medidas.brazo ?? 0, a.medidas.brazo ?? 0, "cm"],
            ] as const
          ).map(([rotulo, actual, previo, unidad]) => {
            const d = delta(actual, previo, unidad);
            return (
              <div key={rotulo} className="flex flex-col items-center gap-0.5">
                <dt className="text-micro font-semibold uppercase tracking-[0.1em] text-tinta-suave">
                  {rotulo}
                </dt>
                <dd className="cifra text-guia font-semibold">{d?.texto ?? "—"}</dd>
              </div>
            );
          })}
        </dl>
      </section>

      <Regla />

      {/* ---- Gráficas: una serie por gráfica, sin leyendas que descifrar ---- */}
      <section className="flex flex-col gap-8">
        <Titulo>Tus números en el tiempo</Titulo>
        <div className="grid gap-10 sm:grid-cols-2">
          {(
            [
              ["Peso", "kg", (c: ChequeoApi) => c.pesoKg ?? 0],
              ["Cintura", "cm", (c: ChequeoApi) => c.medidas.cintura ?? 0],
              ["Abdomen", "cm", (c: ChequeoApi) => c.medidas.abdomen ?? 0],
              ["Brazo", "cm", (c: ChequeoApi) => c.medidas.brazo ?? 0],
            ] as const
          ).map(([rotulo, unidad, leer]) => (
            <article key={rotulo} className="flex flex-col gap-2">
              <Etiqueta>
                {rotulo} ({unidad})
              </Etiqueta>
              <Grafica
                puntos={chequeos.map((c) => ({ etiqueta: fechaCorta(c.fecha), valor: leer(c) }))}
                unidad={unidad}
              />
            </article>
          ))}
        </div>
        <Apoyo className="medida">
          El brazo subió mientras bajaba la cintura. Eso es recomposición: no es lo mismo que
          simplemente pesar menos.
        </Apoyo>
      </section>

      <Regla />

      {/* ---- Historial ---- */}
      <section className="flex flex-col gap-5">
        <div className="flex items-center justify-between gap-4">
          <Titulo>Todos tus registros</Titulo>
          <Boton tono="contorno" medida="chica">
            Descargar PDF
          </Boton>
        </div>

        <div className="flex flex-col gap-4">
          {[...chequeos].reverse().map((c) => (
            <article key={c.ulid} className="flex flex-col gap-3 border-b border-linea pb-4 last:border-0">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <h3 className="text-guia font-semibold">
                  Chequeo #{c.numero}
                  <span className="ml-2 text-menor font-normal text-tinta-suave">{fecha(c.fecha)}</span>
                </h3>
                <Chip tono={c.estado === "validado" ? "exito" : c.estado === "rechazado_calidad" ? "error" : "espera"}>
                  {ROTULO_ESTADO[c.estado as EstadoChequeo]}
                </Chip>
              </div>

              <dl className="flex flex-wrap gap-x-8 gap-y-2 text-menor">
                <Par rotulo="Peso" valor={`${num(c.pesoKg)} kg`} />
                {c.porcentajeGrasa !== null ? (
                  <Par rotulo="Grasa" valor={porcentaje(c.porcentajeGrasa)} />
                ) : null}
                {(["cintura", "abdomen", "cadera", "brazo"] as TipoMedida[]).map((m) => (
                  <Par key={m} rotulo={ROTULO_MEDIDA[m]} valor={`${num(c.medidas[m])} cm`} />
                ))}
              </dl>

              {c.feedback ? <p className="filete medida text-menor text-tinta-media">{c.feedback}</p> : null}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function Par({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt className="text-tinta-suave">{rotulo}</dt>
      <dd className="cifra font-semibold">{valor}</dd>
    </div>
  );
}

function Marco({
  chequeo,
  rotulo,
  angulo,
}: {
  chequeo: ChequeoApi;
  rotulo: string;
  angulo: Angulo;
}) {
  const purgada = estaPurgada(chequeo.fecha);
  return (
    <figure className="overflow-hidden rounded-marco border border-linea">
      <div className="grid aspect-3/4 place-items-center bg-fondo-sutil p-4 text-center">
        {purgada ? (
          <div className="flex flex-col gap-1.5">
            <strong className="text-menor font-semibold">Foto purgada</strong>
            <span className="text-micro text-tinta-suave">
              Se borró a los 4 meses. Tus medidas y tu peso siguen aquí.
            </span>
          </div>
        ) : (
          <span className="text-micro text-tinta-suave">
            {angulo} · {fechaCorta(chequeo.fecha)}
          </span>
        )}
      </div>
      <figcaption className="flex items-center justify-between gap-2 border-t border-linea px-3 py-2 text-micro font-medium">
        <span>{rotulo}</span>
        <span className="cifra text-tinta-media">{num(chequeo.pesoKg)} kg</span>
      </figcaption>
    </figure>
  );
}
