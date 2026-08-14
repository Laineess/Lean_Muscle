/** Mi plan: nutrición y entrenamiento del ciclo vigente.
 *
 *  El bloqueo por pago vive en el servidor (`app/dominio/ciclo.py`): esta pantalla solo
 *  refleja lo que decide la API. Un cliente comprometido no debe poder saltarlo, así que si
 *  el ciclo está bloqueado la API ni siquiera envía el contenido del plan.
 */

import { useState } from "react";
import { Link } from "react-router-dom";

import { AvisoSinServidor, Cargando } from "@/componentes/Estado";
import {
  Apoyo,
  Aviso,
  Boton,
  Chip,
  Etiqueta,
  Portada,
  Regla,
  Tarjeta,
  Titulo,
  Vacio,
} from "@/componentes/primitivas";
import { ErrorApi, api, descargarPdf, type PlanApi, type PlanesDeAlumnaApi } from "@/lib/api";
import { ciclo, historialClinico, planEntrenamiento, planNutricion } from "@/lib/datos";
import { fecha } from "@/lib/formato";
import { usarApiConRespaldo } from "@/lib/usarApi";
import { cn } from "@/lib/utils";

type Pestana = "nutricion" | "entrenamiento";

/** Datos de ejemplo para revisar la pantalla sin servidor. Desaparece con la API en pie. */
const RESPALDO: PlanesDeAlumnaApi = {
  nutricion: {
    tipo: "nutricion",
    ciclo: planNutricion.ciclo,
    estado: "publicado",
    publicadoEn: "2026-07-02T12:00:00Z",
    contenido: { notas: planNutricion.notas, tiempos: planNutricion.tiempos },
    kcalObjetivo: planNutricion.kcal,
    proteinaG: planNutricion.macros.proteinaG,
    carbohidratoG: planNutricion.macros.carbohidratoG,
    grasaG: planNutricion.macros.grasaG,
  },
  entrenamiento: {
    tipo: "entrenamiento",
    ciclo: planEntrenamiento.ciclo,
    estado: "publicado",
    publicadoEn: "2026-07-02T12:00:00Z",
    contenido: {
      notas: planEntrenamiento.notas,
      plantilla: planEntrenamiento.plantilla,
      dias: planEntrenamiento.dias,
    },
    kcalObjetivo: null,
    proteinaG: null,
    carbohidratoG: null,
    grasaG: null,
  },
  bloqueadoPorPago: ciclo.estadoPago !== "validado",
  motivoBloqueo: ciclo.estadoPago !== "validado" ? "pago" : null,
  restricciones: historialClinico.restricciones,
  lesiones: historialClinico.lesiones,
};

export function MiPlan() {
  const [pestana, setPestana] = useState<Pestana>("nutricion");
  const { datos, cargando, sinServidor, mensaje } = usarApiConRespaldo<PlanesDeAlumnaApi>(
    (senal) => api.alumna.plan(senal),
    RESPALDO,
  );

  if (cargando) return <Cargando que="tu plan" />;

  if (datos.bloqueadoPorPago) {
    const porPago = datos.motivoBloqueo === "pago" || datos.motivoBloqueo === null;
    return (
      <div className="flex max-w-md flex-col gap-6">
        <Etiqueta>Ciclo {datos.nutricion?.ciclo ?? ciclo.numero}</Etiqueta>
        <Portada>
          {datos.motivoBloqueo === "ciclo_vencido" ? "Tu ciclo terminó" : "Tu plan está en pausa"}
        </Portada>
        <Apoyo>
          {datos.motivoBloqueo === "ciclo_vencido"
            ? "Tu plan se libera otra vez cuando empiece el ciclo nuevo. Habla con tu coach para renovarlo."
            : datos.motivoBloqueo === "sin_ciclo"
              ? "Todavía no tienes un ciclo abierto. Tu coach lo activa al darte de alta."
              : "Tu comprobante todavía no ha sido validado. En cuanto tu coach lo confirme, tu plan se desbloquea solo."}
        </Apoyo>
        {porPago ? (
          <div>
            <Boton asChild>
              <Link to="/inicio">Subir comprobante</Link>
            </Boton>
          </div>
        ) : null}
      </div>
    );
  }

  const activo = pestana === "nutricion" ? datos.nutricion : datos.entrenamiento;

  return (
    <div className="flex flex-col gap-10">
      {sinServidor ? <AvisoSinServidor mensaje={mensaje} /> : null}

      <header className="flex flex-col gap-3">
        <Etiqueta>
          Ciclo {activo?.ciclo ?? ciclo.numero}
          {activo?.publicadoEn ? ` · publicado el ${fecha(activo.publicadoEn.slice(0, 10))}` : ""}
        </Etiqueta>
        <Portada>Mi plan</Portada>
      </header>

      <div role="tablist" aria-label="Tipo de plan" className="flex gap-6 border-b border-linea">
        {(
          [
            ["nutricion", "Nutrición"],
            ["entrenamiento", "Entrenamiento"],
          ] as const
        ).map(([id, rotulo]) => (
          <button
            key={id}
            role="tab"
            aria-selected={pestana === id}
            onClick={() => setPestana(id)}
            className={cn(
              "-mb-px border-b-2 pb-3 text-menor font-medium transition-colors",
              pestana === id
                ? "border-acento text-tinta"
                : "border-transparent text-tinta-suave hover:text-tinta",
            )}
          >
            {rotulo}
          </button>
        ))}
      </div>

      {activo === null ? (
        <Vacio>
          Tu coach todavía no publica este plan. Te avisamos en cuanto esté.
        </Vacio>
      ) : pestana === "nutricion" ? (
        <Nutricion plan={activo} restricciones={datos.restricciones} />
      ) : (
        <Entrenamiento plan={activo} lesiones={datos.lesiones} />
      )}
    </div>
  );
}

function Nutricion({ plan, restricciones }: { plan: PlanApi; restricciones: string | null }) {
  const kcal = plan.kcalObjetivo ?? 0;
  const kp = (plan.proteinaG ?? 0) * 4;
  const kc = (plan.carbohidratoG ?? 0) * 4;
  const kg = (plan.grasaG ?? 0) * 9;
  const total = kp + kc + kg || 1;
  const tiempos = plan.contenido.tiempos ?? [];

  return (
    <div className="flex flex-col gap-10">
      {/* Cifra grande primero: es lo que ella busca al abrir. */}
      <section className="flex flex-col gap-5">
        <div className="flex flex-col gap-1">
          <Etiqueta>Tu objetivo del día</Etiqueta>
          <p className="cifra text-cifra font-semibold tracking-[-0.03em]">
            {kcal}
            <span className="ml-2 text-guia font-medium text-tinta-suave">kcal</span>
          </p>
        </div>

        <div className="flex h-2 overflow-hidden rounded-full border border-linea">
          <div style={{ width: `${(kp / total) * 100}%` }} className="bg-tinta" />
          <div style={{ width: `${(kc / total) * 100}%` }} className="bg-tinta-suave" />
          <div style={{ width: `${(kg / total) * 100}%` }} className="bg-acento" />
        </div>
        <dl className="flex flex-wrap gap-x-8 gap-y-2 text-menor">
          {(
            [
              ["Proteína", plan.proteinaG ?? 0, kp, "bg-tinta"],
              ["Carbohidratos", plan.carbohidratoG ?? 0, kc, "bg-tinta-suave"],
              ["Grasa", plan.grasaG ?? 0, kg, "bg-acento"],
            ] as const
          ).map(([rotulo, gramos, kcalMacro, color]) => (
            <div key={rotulo} className="flex items-center gap-2">
              <span className={cn("size-2 rounded-full", color)} />
              <dt className="text-tinta-media">{rotulo}</dt>
              <dd className="cifra font-semibold">
                {gramos} g · {Math.round((kcalMacro / total) * 100)} %
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <Regla />

      <section className="flex flex-col gap-8">
        {tiempos.map((t) => (
          <article key={t.nombre} className="flex flex-col gap-3">
            <div className="flex items-baseline justify-between gap-4">
              <h3 className="text-guia font-semibold">
                {t.nombre}
                <span className="ml-1 text-menor font-normal text-tinta-suave">{t.hora}</span>
              </h3>
              <Chip>{t.kcal} kcal</Chip>
            </div>
            <ul className="flex flex-col divide-y divide-linea border-y border-linea">
              {t.alimentos.map((a) => (
                <li key={a.nombre} className="flex items-baseline justify-between gap-4 py-2.5">
                  <span className="text-cuerpo">{a.nombre}</span>
                  <span className="cifra shrink-0 text-menor text-tinta-media">
                    {a.porcion} · {a.kcal} kcal
                  </span>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </section>

      {plan.contenido.notas ? (
        <Tarjeta acentuada className="flex flex-col gap-2">
          <Etiqueta>Notas de tu coach</Etiqueta>
          <p className="medida text-cuerpo leading-relaxed">{plan.contenido.notas}</p>
        </Tarjeta>
      ) : null}

      {restricciones ? (
        <Aviso tono="info" titulo="Tus restricciones">
          {restricciones} Salen de tu cuestionario; si cambian, actualízalas en tu cuenta.
        </Aviso>
      ) : null}

      <BotonPdf
        ruta="/documentos/plan-nutricion"
        nombre={`plan-nutricion-ciclo-${plan.ciclo}.pdf`}
        rotulo="Descargar mi plan en PDF"
        ayuda="Para imprimirlo o llevarlo al súper sin depender de la señal."
      />
    </div>
  );
}

/** Descarga con su propio estado: generar un PDF tarda, y un botón que no responde parece
 *  roto aunque esté trabajando. */
function BotonPdf({
  ruta,
  nombre,
  rotulo,
  ayuda,
}: {
  ruta: string;
  nombre: string;
  rotulo: string;
  ayuda: string;
}) {
  const [bajando, setBajando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function bajar() {
    setError(null);
    setBajando(true);
    try {
      await descargarPdf(ruta, nombre);
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo generar el documento.");
    } finally {
      setBajando(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div>
        <Boton tono="contorno" disabled={bajando} onClick={() => void bajar()}>
          {bajando ? "Generando…" : rotulo}
        </Boton>
      </div>
      {error ? <Aviso tono="error">{error}</Aviso> : <p className="text-micro text-tinta-suave">{ayuda}</p>}
    </div>
  );
}

function Entrenamiento({ plan, lesiones }: { plan: PlanApi; lesiones: string | null }) {
  const dias = plan.contenido.dias ?? [];

  return (
    <div className="flex flex-col gap-10">
      {plan.contenido.plantilla ? (
        <div className="flex flex-col gap-1">
          <Etiqueta>Plantilla base</Etiqueta>
          <Titulo>{plan.contenido.plantilla}</Titulo>
          <Apoyo>{dias.length} días por semana</Apoyo>
        </div>
      ) : null}

      <section className="flex flex-col gap-10">
        {dias.map((d, i) => (
          <article key={d.nombre} className="flex flex-col gap-3">
            <div className="flex items-baseline justify-between gap-4">
              <h3 className="text-guia font-semibold">{d.nombre}</h3>
              {i === 0 ? <Chip tono="espera">Hoy</Chip> : null}
            </div>
            <ul className="flex flex-col divide-y divide-linea border-y border-linea">
              {d.ejercicios.map((e) => (
                <li key={e.nombre} className="flex flex-col gap-1 py-3">
                  <div className="flex items-baseline justify-between gap-4">
                    <span className="text-cuerpo font-medium">{e.nombre}</span>
                    <span className="cifra shrink-0 text-menor text-tinta-media">
                      {e.series} × {e.reps} · {e.carga}
                    </span>
                  </div>
                  {e.nota ? <p className="filete text-menor text-tinta-media">{e.nota}</p> : null}
                </li>
              ))}
            </ul>
          </article>
        ))}
      </section>

      {plan.contenido.notas ? (
        <Tarjeta acentuada className="flex flex-col gap-2">
          <Etiqueta>Notas de ejecución</Etiqueta>
          <p className="medida text-cuerpo leading-relaxed">{plan.contenido.notas}</p>
        </Tarjeta>
      ) : null}

      {lesiones ? (
        <Aviso tono="error" titulo="Ojo con esto">
          {lesiones} Si duele, para.
        </Aviso>
      ) : null}

      <BotonPdf
        ruta="/documentos/rutina"
        nombre={`rutina-ciclo-${plan.ciclo}.pdf`}
        rotulo="Descargar mi rutina en PDF"
        ayuda="Trae una columna en blanco para anotar tus cargas a mano en el gimnasio."
      />
    </div>
  );
}
