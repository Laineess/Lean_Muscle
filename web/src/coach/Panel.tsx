/** Panel de la coach: qué le toca hoy. Primero la bandeja de validación, que es la guarda
 *  del método: sin validar el chequeo anterior no puede publicar plan nuevo.
 */

import { ArrowRight, BellRing, Inbox } from "lucide-react";
import { Link } from "react-router-dom";

import {
  AvisoSinServidor,
  Cargando,
  EsqueletoCifras,
  EsqueletoLista,
  EsqueletoPortada,
} from "@/componentes/Estado";
import { Apoyo, Aviso, Boton, Chip, Dato, Etiqueta, Portada, Regla, Titulo, Vacio } from "@/componentes/primitivas";
import { api, type ResumenPanelApi } from "@/lib/api";
import { cartera, coach as coachEjemplo } from "@/lib/datos";
import { delta, diaSemana, fecha, hoyIso, num, pesos } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
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
  const { t } = useIdioma();
  const { datos: p, cargando, sinServidor, mensaje } = usarApiConRespaldo<ResumenPanelApi>(
    (senal) => api.coach.panel(senal),
    RESPALDO,
  );

  if (cargando)
    return (
      <Cargando
        que={t("tu panel")}
        esqueleto={
          <div className="flex flex-col gap-12">
            <EsqueletoPortada />
            <EsqueletoCifras cuantas={4} />
            <EsqueletoLista filas={3} />
          </div>
        }
      />
    );

  const porValidar = p.porValidar;
  const conAlerta = p.conAlerta;

  return (
    <div className="flex flex-col gap-12">
      {sinServidor ? <AvisoSinServidor mensaje={mensaje} /> : null}
      <header className="flex flex-col gap-3">
        <Etiqueta>
          {diaSemana(hoyIso())} · {t("plan {plan}", { plan: p.plan })}
        </Etiqueta>
        <Portada>{t("Buen día, {nombre}", { nombre: p.coach?.split(" ")[0] ?? "" })}</Portada>
      </header>

      <section className="escalona grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-4">
        <Dato rotulo={t("Por validar")} valor={String(porValidar.length)} nota={t("chequeos esperando")} />
        <Dato
          rotulo={t("Pacientes activos")}
          valor={String(p.activas)}
          unidad={`/ ${p.limiteAlumnas}`}
          nota={t("de tu plan")}
        />
        <Dato
          rotulo={t("Por cobrar")}
          valor={String(p.porCobrar)}
          nota={t("{monto} en riesgo", { monto: pesos(p.porCobrar * p.precioCiclo) })}
        />
        <Dato
          rotulo={t("Ingreso del mes")}
          valor={pesos(p.activas * p.precioCiclo)}
          nota={t("proyectado")}
        />
      </section>

      <Regla />

      {/* ---- Bandeja de validación ---- */}
      <section className="flex flex-col gap-5">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <Titulo icono={Inbox}>{t("Bandeja de validación")}</Titulo>
          <Apoyo>{t("Sin validar el chequeo anterior no puedes publicar plan nuevo.")}</Apoyo>
        </div>

        {/* Una lista vacía dejaba una caja con bordes y nada dentro, que se lee como error. */}
        {porValidar.length === 0 ? <Vacio>{t("No tienes chequeos esperando. Al día.")}</Vacio> : null}

        <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea empty:hidden empty:border-0">
          {porValidar.map((a) => {
            const d = a.pesoKg !== null && a.pesoPrevio !== null ? delta(a.pesoKg, a.pesoPrevio, "kg") : null;
            return (
              <li key={a.ulid} className="flex flex-wrap items-center gap-4 py-4">
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-cuerpo font-medium">{a.nombre}</span>
                    {a.alerta === "outlier" ? <Chip tono="error">{t("Outlier")}</Chip> : null}
                  </div>
                  <Apoyo>
                    {t("Enviado el {fecha} · {peso} kg", {
                      fecha: fecha(a.chequeoFecha!),
                      peso: num(a.pesoKg),
                    })}
                    {d ? ` · ${d.texto} ${t("vs. mes pasado")}` : ""}
                  </Apoyo>
                </div>
                <Boton asChild tono="contorno" medida="chica">
                  <Link to={`/coach/validar/${a.ulid}`}>
                    {t("Revisar")} <ArrowRight className="size-3.5" />
                  </Link>
                </Boton>
              </li>
            );
          })}
        </ul>
      </section>

      {/* ---- Alertas ---- */}
      <section className="flex flex-col gap-5">
        <Titulo icono={BellRing}>{t("Necesitan que intervengas")}</Titulo>
        {conAlerta.length === 0 ? <Vacio>{t("Ninguna alumna necesita que intervengas hoy.")}</Vacio> : null}
        <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea empty:hidden empty:border-0">
          {conAlerta.map((a) => (
            <li key={a.ulid} className="flex flex-wrap items-center gap-4 py-4">
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <span className="text-cuerpo font-medium">{a.nombre}</span>
                <Apoyo>
                  {t("Ciclo {ciclo}", { ciclo: a.ciclo })}
                  {a.ultimoAcceso ? ` · ${t("último acceso {fecha}", { fecha: fecha(a.ultimoAcceso) })}` : ""}
                </Apoyo>
              </div>
              <Chip tono={a.alerta === "outlier" ? "error" : "espera"}>
                {t(ROTULO_ALERTA[a.alerta!])}
              </Chip>
            </li>
          ))}
        </ul>
      </section>

      <Aviso tono="atencion" titulo={t("Recordatorio del método")}>
        {t(
          "Tú revisas postura y vestimenta: el sistema solo mide nitidez y luz. Si ves flexión, abdomen contraído o ropa fuera de protocolo, recházalo con causa.",
        )}
      </Aviso>

      <div>
        <Boton asChild tono="contorno">
          <Link to="/coach/alumnas">{t("Ver todas mis pacientes")}</Link>
        </Boton>
      </div>
    </div>
  );
}
