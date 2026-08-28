/** Bandeja de solicitudes: quién llegó por la liga y todavía no está decidido.
 *
 *  Aparte de la cartera a propósito. Una solicitud no es una alumna —no cuenta contra el
 *  límite, no tiene ciclo ni chequeo— y mezclarlas haría que la coach viera como suya a
 *  gente que todavía no aceptó.
 *
 *  Aceptar hace las tres cosas de un golpe: confirma su consulta, abre su ciclo con el plan
 *  que la coach confirme y le deja el chequeo disponible. Descartar le corta el acceso hoy
 *  y su expediente se borra a los siete días.
 */

import { Check, Clock, X } from "lucide-react";
import { useState } from "react";

import { Dialogo } from "@/componentes/Dialogo";
import { CargandoPantalla } from "@/componentes/Estado";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Chip,
  Etiqueta,
  Portada,
  Selector,
  Vacio,
} from "@/componentes/primitivas";
import {
  ErrorApi,
  api,
  urlDeComprobante,
  type PlanComercialApi,
  type RespuestaDeAlumnaApi,
  type SolicitudEnBandejaApi,
} from "@/lib/api";
import { fecha, horaLocal, num } from "@/lib/formato";
import { usarApi } from "@/lib/usarApi";
import { useIdioma } from "@/lib/idioma";

const ROTULO_PASO: Record<string, string> = {
  correo: "sin confirmar su correo",
  cuestionario: "contestando el cuestionario",
  cita: "eligiendo su consulta",
  comprobante: "pagando su inscripción",
  espera: "lista para que decidas",
  lista: "decidida",
};

const ROTULO_PAGO: Record<string, string> = {
  pendiente: "sin comprobante",
  en_revision: "comprobante por revisar",
  pagado: "pagada",
};

/** Días que faltan para que la solicitud se borre sola. */
function diasPara(iso: string): number {
  return Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000));
}

export function Solicitudes() {
  const { t } = useIdioma();
  const carga = usarApi<SolicitudEnBandejaApi[]>((s) => api.coach.solicitudes(s));
  const planes = usarApi<PlanComercialApi[]>((s) => api.coach.planes(s));
  const [decidiendo, setDecidiendo] = useState<SolicitudEnBandejaApi | null>(null);

  if (carga.cargando) return <CargandoPantalla que={t("tus solicitudes")} filas={3} />;

  const filas = carga.datos ?? [];
  const listas = filas.filter((f) => f.paso === "espera");
  const enCurso = filas.filter((f) => f.paso !== "espera");

  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta>{t("Llegaron por tu liga")}</Etiqueta>
        <Portada>{t("Solicitudes")}</Portada>
        <Apoyo>
          {t("Aceptar confirma su consulta, abre su ciclo y le deja el chequeo disponible. Ninguna cuenta contra tu límite hasta que la aceptes.")}
        </Apoyo>
      </header>

      {carga.error ? <Aviso tono="error">{carga.error.message}</Aviso> : null}

      {filas.length === 0 ? (
        <Vacio>
          {t("Nadie ha empezado su registro todavía. Comparte tu liga desde la pantalla de tus alumnas.")}
        </Vacio>
      ) : null}

      {listas.length > 0 ? (
        <section className="flex flex-col gap-4">
          <Etiqueta>{t("Te toca decidir")}</Etiqueta>
          <ul className="flex flex-col gap-4">
            {listas.map((f) => (
              <li key={f.ulid}>
                <Tarjeta solicitud={f} onDecidir={() => setDecidiendo(f)} />
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {enCurso.length > 0 ? (
        <section className="flex flex-col gap-4">
          <Etiqueta>{t("Todavía en su recorrido")}</Etiqueta>
          <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
            {enCurso.map((f) => (
              <li
                key={f.ulid}
                className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3"
              >
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="text-menor font-medium">{f.nombre}</span>
                  <span className="text-micro text-tinta-suave">
                    {t(ROTULO_PASO[f.paso] ?? f.paso)}
                  </span>
                </span>
                {f.borraEn ? (
                  <Chip tono={diasPara(f.borraEn) <= 2 ? "espera" : "neutro"}>
                    {t("se borra en {dias} d", { dias: diasPara(f.borraEn) })}
                  </Chip>
                ) : null}
              </li>
            ))}
          </ul>
          <Apoyo>
            {t("Si no terminan, su registro se borra solo y no queda nada suyo. Se les avisa dos días antes.")}
          </Apoyo>
        </section>
      ) : null}

      {decidiendo ? (
        <Decision
          solicitud={decidiendo}
          planes={(planes.datos ?? []).filter((p) => p.activa)}
          onCerrar={() => setDecidiendo(null)}
          onHecho={() => {
            setDecidiendo(null);
            carga.recargar();
          }}
        />
      ) : null}
    </div>
  );
}

/* ------------------------------------------------------------ Tarjeta --- */

function Tarjeta({
  solicitud,
  onDecidir,
}: {
  solicitud: SolicitudEnBandejaApi;
  onDecidir: () => void;
}) {
  const { t } = useIdioma();
  const [verRespuestas, setVerRespuestas] = useState(false);

  return (
    <article className="flex flex-col gap-4 rounded-marco border border-linea p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <span className="text-guia font-medium">{solicitud.nombre}</span>
          <span className="text-micro text-tinta-suave">
            {t("{edad} años · {correo}", { edad: solicitud.edad, correo: solicitud.correo })}
            {solicitud.whatsapp ? ` · ${solicitud.whatsapp}` : ""}
          </span>
        </div>
        <Boton medida="chica" onClick={onDecidir}>
          {t("Revisar")}
        </Boton>
      </div>

      <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-3">
        <Dato rotulo={t("Plan que pide")}>
          {solicitud.planPedido ?? "—"}
          {solicitud.precioPlan !== null ? (
            <span className="text-tinta-suave"> · ${num(solicitud.precioPlan)}</span>
          ) : null}
        </Dato>
        <Dato rotulo={t("Su consulta")}>
          {solicitud.citaIniciaEn
            ? `${fecha(solicitud.citaIniciaEn)} · ${horaLocal(solicitud.citaIniciaEn)}`
            : t("sin reservar")}
        </Dato>
        <Dato rotulo={t("Inscripción")}>
          {solicitud.montoInscripcion !== null ? `$${num(solicitud.montoInscripcion)}` : "—"}
          <span className="text-tinta-suave">
            {" · "}
            {ROTULO_PAGO[solicitud.estadoDelPago ?? ""] ? t(ROTULO_PAGO[solicitud.estadoDelPago ?? ""]!) : "—"}
          </span>
        </Dato>
      </dl>

      <div>
        <Boton
          tono="discreto"
          medida="chica"
          onClick={() => setVerRespuestas((v) => !v)}
        >
          {verRespuestas ? t("Ocultar lo que contestó") : t("Ver lo que contestó")}
        </Boton>
      </div>

      {verRespuestas ? <Respuestas alumnaUlid={solicitud.alumnaUlid} /> : null}
    </article>
  );
}

function Dato({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-micro uppercase tracking-[0.08em] text-tinta-suave">{rotulo}</dt>
      <dd className="text-menor">{children}</dd>
    </div>
  );
}

/** Lo que contestó. Se pide al abrirlo, no antes: cada lectura queda en la bitácora. */
function Respuestas({ alumnaUlid }: { alumnaUlid: string }) {
  const { t } = useIdioma();
  const carga = usarApi<RespuestaDeAlumnaApi[]>(
    (s) => api.coach.respuestasDeAlumna(alumnaUlid, s),
    [alumnaUlid],
  );

  if (carga.cargando) return <Apoyo>{t("Un momento…")}</Apoyo>;
  if (carga.error) return <Aviso tono="error">{carga.error.message}</Aviso>;

  const filas = carga.datos ?? [];
  if (filas.length === 0) return <Apoyo>{t("No contestó ninguna de tus preguntas.")}</Apoyo>;

  return (
    <dl className="flex flex-col divide-y divide-linea border-y border-linea">
      {filas.map((r) => (
        <div key={r.pregunta} className="flex flex-col gap-0.5 py-2">
          <dt className="text-micro text-tinta-suave">{r.pregunta}</dt>
          <dd className="text-menor">{r.valor || "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

/* ----------------------------------------------------------- Decisión --- */

function Decision({
  solicitud,
  planes,
  onCerrar,
  onHecho,
}: {
  solicitud: SolicitudEnBandejaApi;
  planes: PlanComercialApi[];
  onCerrar: () => void;
  onHecho: () => void;
}) {
  const { t } = useIdioma();
  const [plan, setPlan] = useState(solicitud.planPedidoUlid ?? "");
  const [validarPago, setValidarPago] = useState(solicitud.estadoDelPago === "en_revision");
  const [descartando, setDescartando] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);

  async function resolver(accion: "aceptar" | "descartar") {
    setFallo(null);
    setOcupado(true);
    try {
      if (accion === "aceptar") {
        await api.coach.aceptarSolicitud(solicitud.ulid, plan || null, validarPago);
      } else {
        await api.coach.descartarSolicitud(solicitud.ulid, motivo.trim());
      }
      onHecho();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : t("No se pudo completar."));
    } finally {
      setOcupado(false);
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={t("Solicitud")}
      titulo={solicitud.nombre}
      descripcion={`${solicitud.edad} años · ${solicitud.correo}`}
      pie={
        descartando ? (
          <>
            <Boton tono="contorno" medida="chica" onClick={() => setDescartando(false)}>
              {t("Volver")}
            </Boton>
            <Boton
              tono="peligro"
              medida="chica"
              disabled={ocupado || !motivo.trim()}
              onClick={() => void resolver("descartar")}
            >
              {t("Descartar y avisarle")}
            </Boton>
          </>
        ) : (
          <>
            <Boton tono="peligro" medida="chica" onClick={() => setDescartando(true)}>
              <X className="size-3.5" /> {t("Descartar")}
            </Boton>
            <Boton medida="chica" cargando={ocupado} onClick={() => void resolver("aceptar")}>
              {ocupado ? null : <Check className="size-3.5" />}
              {t("Aceptar")}
            </Boton>
          </>
        )
      }
    >
      {descartando ? (
        <>
          <Aviso tono="atencion" titulo={t("Pierde el acceso hoy")}>
            {t("Su registro y todo lo que capturó se borran en 7 días. La consulta que había reservado queda libre para otra.")}
          </Aviso>
          <Campo
            id="so-motivo"
            etiqueta={t("Por qué")}
            ayuda={t("Lo lee ella tal cual en su correo, así que escríbelo para ella.")}
          >
            <textarea
              id="so-motivo"
              rows={3}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder={t("Tu condición necesita seguimiento médico que yo no doy.")}
              className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
            />
          </Campo>
        </>
      ) : (
        <>
          <div className="flex flex-col gap-1">
            <span className="flex flex-wrap items-center gap-2 text-menor">
              <Clock className="size-3.5 text-tinta-suave" />
              {solicitud.citaIniciaEn
                ? t("Su consulta: {fecha} a las {hora}", { fecha: fecha(solicitud.citaIniciaEn), hora: horaLocal(solicitud.citaIniciaEn) })
                : t("Todavía no reserva consulta")}
            </span>
            <Apoyo>{t("Al aceptarla queda confirmada y se le avisa por correo.")}</Apoyo>
          </div>

          <Campo
            id="so-plan"
            etiqueta={t("Plan que le confirmas")}
            ayuda={
              solicitud.planPedido
                ? t("Ella pidió {plan}. De aquí sale el precio de su ciclo.", { plan: solicitud.planPedido })
                : t("De aquí sale el precio de su ciclo.")
            }
          >
            <Selector id="so-plan" value={plan} onChange={(e) => setPlan(e.target.value)}>
              <option value="">{t("Sin plan por ahora")}</option>
              {planes.map((p) => (
                <option key={p.ulid} value={p.ulid}>
                  {p.nombre} · ${num(p.precio)} · {p.dias} días
                </option>
              ))}
            </Selector>
          </Campo>

          {solicitud.cobroUlid && solicitud.estadoDelPago !== "pagado" ? (
            <div className="flex flex-col gap-3">
              <Campo id="so-pago" etiqueta={`Inscripción · $${num(solicitud.montoInscripcion ?? 0)}`}>
                <label className="flex items-center gap-2 text-menor">
                  <input
                    type="checkbox"
                    checked={validarPago}
                    onChange={(e) => setValidarPago(e.target.checked)}
                    disabled={solicitud.estadoDelPago !== "en_revision"}
                    className="size-4 accent-[var(--acento-texto)]"
                  />
                  {solicitud.estadoDelPago === "en_revision"
                    ? t("Dar por bueno el comprobante y registrar el ingreso")
                    : t("Todavía no sube comprobante: puedes aceptarla igual y queda el adeudo")}
                </label>
              </Campo>

              {solicitud.estadoDelPago === "en_revision" ? (
                <img
                  src={urlDeComprobante(solicitud.cobroUlid)}
                  alt={t("Comprobante de {nombre}", { nombre: solicitud.nombre })}
                  className="max-h-72 w-full rounded-marco border border-linea object-contain"
                />
              ) : null}

              {solicitud.montoLeido !== null &&
              solicitud.montoLeido !== solicitud.montoInscripcion ? (
                <Aviso tono="atencion" titulo={t("El importe leído no coincide")}>
                  {t("Esperabas {a} y la captura dice {b}. Compruébalo contra tu estado de cuenta.", {
                    a: num(solicitud.montoInscripcion ?? 0),
                    b: num(solicitud.montoLeido),
                  })}
                </Aviso>
              ) : null}
            </div>
          ) : null}

          <Etiqueta>
            {t("Al aceptarla entra a tu cartera y empieza a contar contra tu límite.")}
          </Etiqueta>
        </>
      )}

      {fallo ? <Aviso tono="error">{fallo}</Aviso> : null}
    </Dialogo>
  );
}
