/** Panel de la coach: qué le toca hoy. Primero la bandeja de validación, que es la guarda
 *  del método: sin validar el chequeo anterior no puede publicar plan nuevo.
 */

import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

import { AvisoSinServidor, Cargando } from "@/componentes/Estado";
import { Apoyo, Aviso, Boton, Chip, Dato, Etiqueta, Portada, Regla, Titulo } from "@/componentes/primitivas";
import { api, type ResumenPanelApi } from "@/lib/api";
import { cartera, coach as coachEjemplo } from "@/lib/datos";
import { delta, diaSemana, fecha, num, pesos } from "@/lib/formato";
import { usarApiConRespaldo } from "@/lib/usarApi";

const ROTULO_ALERTA = {
  outlier: "Outlier de peso",
  pago: "Pago pendiente",
  inactividad: "3 días sin entrar",
} as const;

/** Datos de ejemplo, para poder revisar las pantallas sin el servidor en pie.
 *  Desaparece cuando la API sea el único origen. */
const RESPALDO: ResumenPanelApi = {
  coach: coachEjemplo.nombre,
  marca: coachEjemplo.marca,
  plan: coachEjemplo.plan,
  limiteAlumnas: coachEjemplo.limiteAlumnas,
  precioCiclo: coachEjemplo.precioCiclo,
  porValidar: cartera.filter((a) => a.chequeoEstado === "pendiente_evaluacion"),
  conAlerta: cartera.filter((a) => a.alerta !== null),
  activas: cartera.filter((a) => a.estado === "activa").length,
  porCobrar: cartera.filter((a) => a.pago === "pendiente").length,
};

export function Panel() {
  const { datos: p, cargando, sinServidor, mensaje } = usarApiConRespaldo<ResumenPanelApi>(
    (senal) => api.coach.panel(senal),
    RESPALDO,
  );

  if (cargando) return <Cargando que="tu panel" />;

  const porValidar = p.porValidar;
  const conAlerta = p.conAlerta;

  return (
    <div className="flex flex-col gap-12">
      {sinServidor ? <AvisoSinServidor mensaje={mensaje} /> : null}
      <header className="flex flex-col gap-3">
        <Etiqueta>
          {diaSemana("2026-08-13")} · plan {p.plan}
        </Etiqueta>
        <Portada>Buen día, {p.coach.split(" ")[0]}</Portada>
      </header>

      <section className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-4">
        <Dato rotulo="Por validar" valor={String(porValidar.length)} nota="chequeos esperando" />
        <Dato
          rotulo="Alumnas activas"
          valor={String(p.activas)}
          unidad={`/ ${p.limiteAlumnas}`}
          nota="de tu plan"
        />
        <Dato
          rotulo="Por cobrar"
          valor={String(p.porCobrar)}
          nota={`${pesos(p.porCobrar * p.precioCiclo)} en riesgo`}
        />
        <Dato
          rotulo="Ingreso del mes"
          valor={pesos(p.activas * p.precioCiclo)}
          nota="proyectado"
        />
      </section>

      <Regla />

      {/* ---- Bandeja de validación ---- */}
      <section className="flex flex-col gap-5">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <Titulo>Bandeja de validación</Titulo>
          <Apoyo>Sin validar el chequeo anterior no puedes publicar plan nuevo.</Apoyo>
        </div>

        <ul className="flex flex-col divide-y divide-linea border-y border-linea">
          {porValidar.map((a) => {
            const d = a.pesoKg !== null && a.pesoPrevio !== null ? delta(a.pesoKg, a.pesoPrevio, "kg") : null;
            return (
              <li key={a.ulid} className="flex flex-wrap items-center gap-4 py-4">
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-cuerpo font-medium">{a.nombre}</span>
                    {a.alerta === "outlier" ? <Chip tono="error">Outlier</Chip> : null}
                  </div>
                  <Apoyo>
                    Enviado el {fecha(a.chequeoFecha!)} · {num(a.pesoKg)} kg
                    {d ? ` · ${d.texto} vs. mes pasado` : ""}
                  </Apoyo>
                </div>
                <Boton asChild tono="contorno" medida="chica">
                  <Link to={`/coach/validar/${a.ulid}`}>
                    Revisar <ArrowRight className="size-3.5" />
                  </Link>
                </Boton>
              </li>
            );
          })}
        </ul>
      </section>

      {/* ---- Alertas ---- */}
      <section className="flex flex-col gap-5">
        <Titulo>Necesitan que intervengas</Titulo>
        <ul className="flex flex-col divide-y divide-linea border-y border-linea">
          {conAlerta.map((a) => (
            <li key={a.ulid} className="flex flex-wrap items-center gap-4 py-4">
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <span className="text-cuerpo font-medium">{a.nombre}</span>
                <Apoyo>
                  Ciclo {a.ciclo}
                  {a.ultimoAcceso ? ` · último acceso ${fecha(a.ultimoAcceso)}` : ""}
                </Apoyo>
              </div>
              <Chip tono={a.alerta === "outlier" ? "error" : "espera"}>
                {ROTULO_ALERTA[a.alerta!]}
              </Chip>
            </li>
          ))}
        </ul>
      </section>

      <Aviso tono="atencion" titulo="Recordatorio del método">
        Tú revisas postura y vestimenta: el sistema solo mide nitidez y luz. Si ves flexión,
        abdomen contraído o ropa fuera de protocolo, recházalo con causa.
      </Aviso>

      <div>
        <Boton asChild tono="contorno">
          <Link to="/coach/alumnas">Ver todas mis alumnas</Link>
        </Boton>
      </div>
    </div>
  );
}
