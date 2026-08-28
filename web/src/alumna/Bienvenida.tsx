/** Lo primero que ve una alumna nueva: quién la va a acompañar, y luego el cuestionario.
 *
 *  El orden importa: se le piden lesiones y medicación a alguien que todavía no sabe con
 *  quién habla. El núcleo clínico no se puede quitar; encima van las preguntas de su coach.
 */

import { ArrowRight, Check } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Casilla,
  Entrada,
  Etiqueta,
  Portada,
  Regla,
  Selector,
  Titulo,
  Vacio,
} from "@/componentes/primitivas";
import {
  ErrorApi,
  api,
  urlDeFotoDeCoach,
  type CuestionarioApi,
  type NucleoClinicoApi,
  type PreguntaApi,
  type EstadoDeSolicitudApi,
  type PresentacionApi,
} from "@/lib/api";
import { BotonSalir } from "@/componentes/Seguridad";
import { num } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
import { usarApi } from "@/lib/usarApi";
import { cn } from "@/lib/utils";

const ROTULO_CONSENTIMIENTO: Record<string, [string, string]> = {
  terminos: ["Términos y Condiciones", "/legal/terminos"],
  privacidad: ["Aviso de Privacidad", "/legal/privacidad"],
  datos_salud: ["Tratamiento de mis datos de salud", "/legal/privacidad"],
  protocolo_foto: ["Protocolo fotográfico", "/legal/privacidad"],
};

const CAMPOS_CLINICOS: [keyof NucleoClinicoApi, string, string][] = [
  ["lesiones", "Lesiones o cirugías", "Esguince de tobillo en 2023, ya recuperado."],
  ["condiciones", "Condiciones médicas", "Hipotiroidismo controlado."],
  ["medicacion", "Medicación", "Levotiroxina 50 mcg diaria."],
  ["restricciones", "Alergias y restricciones", "Intolerancia a la lactosa. No como mariscos."],
];

export function Bienvenida() {
  const { t } = useIdioma();
  const navegar = useNavigate();
  const presentacion = usarApi<PresentacionApi>((s) => api.alumna.presentacion(s));
  const cuestionario = usarApi<CuestionarioApi>((s) => api.alumna.cuestionario(s));
  // Una solicitud del registro abierto todavía no tiene chequeo que abrir: al terminar
  // vuelve a su recorrido, donde le toca reservar consulta.
  const solicitud = usarApi<EstadoDeSolicitudApi>((s) => api.alumna.solicitud(s));
  const [paso, setPaso] = useState<"presentacion" | "cuestionario">("presentacion");

  if (presentacion.cargando || cuestionario.cargando || solicitud.cargando)
    return <Vacio>{t("Un momento…")}</Vacio>;

  const p = presentacion.datos;
  const c = cuestionario.datos;
  if (!c) {
    return (
      <Aviso tono="error" titulo={t("No se pudo abrir el cuestionario")}>
        {t("Vuelve a intentarlo en un momento.")}
      </Aviso>
    );
  }

  // Sin presentación escrita no se interpone una pantalla vacía entre ella y el formulario.
  const hayPresentacion = Boolean(p?.activa && (p.titulo || p.texto || p.tieneFoto));
  if (paso === "presentacion" && hayPresentacion && p) {
    return <Presentacion p={p} onSeguir={() => setPaso("cuestionario")} />;
  }

  const esSolicitud = solicitud.datos?.esSolicitud ?? false;

  return (
    <Cuestionario
      c={c}
      esSolicitud={esSolicitud}
      onListo={() => {
        cuestionario.recargar();
        // Directo a su primer chequeo, no al panel: sin peso ni medidas su coach no puede
        // calcular nada, y mandarla al inicio solo aplaza el único paso que falta.
        void navegar(esSolicitud ? "/solicitud" : "/chequeo", { replace: true });
      }}
    />
  );
}

/* ------------------------------------------------------------ Presentación --- */

function Presentacion({ p, onSeguir }: { p: PresentacionApi; onSeguir: () => void }) {
  const { t } = useIdioma();
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-8">
      <header className="flex flex-col items-center gap-5 text-center">
        {p.tieneFoto ? (
          <img
            src={urlDeFotoDeCoach()}
            alt={p.marca}
            className="size-32 rounded-full border border-linea object-cover"
          />
        ) : null}
        <div className="flex flex-col gap-2">
          <Etiqueta>{p.marca}</Etiqueta>
          <Portada>{p.titulo || t("Bienvenida")}</Portada>
        </div>
      </header>

      {/* Los párrafos son suyos tal como los escribió: no se reformatea nada. */}
      {p.texto ? (
        <div className="flex flex-col gap-4">
          {p.texto.split(/\n\s*\n/).map((parrafo, i) => (
            <p key={i} className="text-cuerpo leading-relaxed text-tinta-media">
              {parrafo}
            </p>
          ))}
        </div>
      ) : null}

      {p.ficha.length > 0 ? (
        <>
          <Regla />
          <dl className="grid gap-x-8 gap-y-5 sm:grid-cols-2">
            {p.ficha.map((d) => (
              <div key={d.rotulo} className="flex flex-col gap-1">
                <dt className="text-micro font-semibold uppercase tracking-[0.08em] text-tinta-suave">
                  {d.rotulo}
                </dt>
                <dd className="text-menor leading-relaxed">{d.valor}</dd>
              </div>
            ))}
          </dl>
        </>
      ) : null}

      <div className="flex justify-center pt-2">
        <Boton onClick={onSeguir}>
          {t("Empezar")} <ArrowRight className="size-4" />
        </Boton>
      </div>

      {/* El cuestionario bloquea el resto de la app hasta terminarlo. Sin salida, quien
          entra en la cuenta equivocada no puede ni volver al acceso. */}
      <div className="flex justify-center border-t border-linea pt-6">
        <BotonSalir />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------ Cuestionario --- */

function Cuestionario({
  c,
  esSolicitud,
  onListo,
}: {
  c: CuestionarioApi;
  /** Solo quien se registró sola elige plan: a las demás se lo asignó su coach al darlas de alta. */
  esSolicitud: boolean;
  onListo: () => void;
}) {
  const { t } = useIdioma();
  const [nucleo, setNucleo] = useState<NucleoClinicoApi>(c.nucleo);
  const [plan, setPlan] = useState<string | null>(c.planElegido);
  const [respuestas, setRespuestas] = useState<Record<string, string>>(() =>
    Object.fromEntries(c.respuestas.map((r) => [r.preguntaUlid, r.valor])),
  );
  const [aceptados, setAceptados] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);

  const faltanConsentimientos = c.consentimientosPendientes.filter(
    (tipo) => !aceptados.includes(tipo),
  );
  const faltanObligatorias = c.preguntas.filter(
    (q) => q.obligatoria && !(respuestas[q.ulid] ?? "").trim(),
  );
  const eligePlan = esSolicitud && c.planes.length > 0;
  const listo =
    faltanConsentimientos.length === 0 &&
    faltanObligatorias.length === 0 &&
    (!eligePlan || plan !== null);

  async function enviar() {
    setFallo(null);
    setEnviando(true);
    try {
      await api.alumna.enviarCuestionario({
        nucleo,
        tarifaUlid: plan,
        respuestas: Object.entries(respuestas).map(([preguntaUlid, valor]) => ({
          preguntaUlid,
          valor,
        })),
        consentimientos: aceptados,
      });
      onListo();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo guardar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-8">
      <header className="flex flex-col gap-3">
        <Etiqueta>{t("Antes de empezar")}</Etiqueta>
        <Portada>{t("Cuéntale a tu coach")}</Portada>
        <Apoyo>
          {t("De esto depende que tu plan sea seguro. Si algo cambia después, lo puedes editar desde tu cuenta.")}
        </Apoyo>
      </header>

      {/* ---- Núcleo clínico ---- */}
      <section className="flex flex-col gap-5">
        <Titulo>{t("Tu salud")}</Titulo>
        {CAMPOS_CLINICOS.map(([clave, rotulo, ejemplo]) => (
          <Campo key={clave} id={`cu-${clave}`} etiqueta={t(rotulo)}>
            <textarea
              id={`cu-${clave}`}
              rows={2}
              value={nucleo[clave] ?? ""}
              onChange={(e) => setNucleo((v) => ({ ...v, [clave]: e.target.value }))}
              placeholder={t(ejemplo)}
              className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
            />
          </Campo>
        ))}
        <Apoyo>{t("Si no aplica, déjalo vacío. Es mejor eso que escribir «nada».")}</Apoyo>
      </section>

      {/* ---- Preguntas de la coach ---- */}
      {c.preguntas.length > 0 ? (
        <>
          <Regla />
          <section className="flex flex-col gap-5">
            <Titulo>{t("Lo que tu coach quiere saber")}</Titulo>
            {c.preguntas.map((q) => (
              <Pregunta
                key={q.ulid}
                q={q}
                valor={respuestas[q.ulid] ?? ""}
                onCambio={(v) => setRespuestas((r) => ({ ...r, [q.ulid]: v }))}
              />
            ))}
          </section>
        </>
      ) : null}

      {/* ---- El plan que pide ---- */}
      {eligePlan ? (
        <>
          <Regla />
          <section className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <Titulo>{t("Qué plan quieres")}</Titulo>
              <Apoyo>
                {t("Es lo que le pides a tu coach. Ella lo confirma al aceptarte, y de ahí sale tu primer ciclo.")}
              </Apoyo>
            </div>
            <div className="flex flex-col gap-2">
              {c.planes.map((tarifa) => (
                <label
                  key={tarifa.ulid}
                  htmlFor={`pl-${tarifa.ulid}`}
                  className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-marco border p-4 transition-colors",
                    plan === tarifa.ulid ? "border-acento bg-acento-sutil" : "border-linea hover:border-tinta",
                  )}
                >
                  <input
                    id={`pl-${tarifa.ulid}`}
                    type="radio"
                    name="plan"
                    checked={plan === tarifa.ulid}
                    onChange={() => setPlan(tarifa.ulid)}
                    className="mt-0.5 size-5 shrink-0 accent-[var(--acento-texto)]"
                  />
                  <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="text-menor font-semibold">{tarifa.nombre}</span>
                      <span className="cifra text-menor">
                        ${num(tarifa.precio)} · {t("{dias} días", { dias: tarifa.dias })}
                      </span>
                    </span>
                    {tarifa.descripcion ? (
                      <span className="text-micro text-tinta-suave">{tarifa.descripcion}</span>
                    ) : null}
                  </span>
                </label>
              ))}
            </div>
          </section>
        </>
      ) : null}

      {/* ---- Consentimientos ---- */}
      {c.consentimientosPendientes.length > 0 ? (
        <>
          <Regla />
          <section className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <Titulo>{t("Permisos")}</Titulo>
              <Apoyo>
                {t("Guardamos la fecha y el texto exacto que aceptas. Puedes revocarlos cuando quieras desde tu cuenta.")}
              </Apoyo>
            </div>
            {c.consentimientosPendientes.map((tipo) => {
              const [rotulo, ruta] = ROTULO_CONSENTIMIENTO[tipo] ?? [tipo, "/legal/privacidad"];
              return (
                <Casilla
                  key={tipo}
                  id={`cu-c-${tipo}`}
                  titulo={t("Acepto {rotulo}", { rotulo: t(rotulo) })}
                  checked={aceptados.includes(tipo)}
                  onChange={(e) =>
                    setAceptados((v) =>
                      e.target.checked ? [...v, tipo] : v.filter((x) => x !== tipo),
                    )
                  }
                >
                  <Link to={ruta} className="underline underline-offset-2">
                    {t("Leerlo antes de aceptar")}
                  </Link>
                </Casilla>
              );
            })}
          </section>
        </>
      ) : null}

      {fallo ? <Aviso tono="error">{t(fallo)}</Aviso> : null}

      <div className="flex flex-col gap-2">
        <Boton disabled={!listo || enviando} onClick={() => void enviar()}>
          <Check className="size-4" /> {enviando ? t("Guardando…") : t("Listo")}
        </Boton>
        {!listo ? (
          <Apoyo>
            {faltanObligatorias.length > 0
              ? t("Falta contestar: {texto}", { texto: faltanObligatorias[0]!.texto })
              : t("Falta aceptar los permisos para poder continuar.")}
          </Apoyo>
        ) : null}
      </div>
    </div>
  );
}

function Pregunta({
  q,
  valor,
  onCambio,
}: {
  q: PreguntaApi;
  valor: string;
  onCambio: (valor: string) => void;
}) {
  const { t } = useIdioma();
  const etiqueta = q.obligatoria ? `${q.texto} *` : q.texto;

  if (q.tipo === "texto_largo") {
    return (
      <Campo id={`q-${q.ulid}`} etiqueta={etiqueta} {...(q.ayuda ? { ayuda: q.ayuda } : {})}>
        <textarea
          id={`q-${q.ulid}`}
          rows={3}
          value={valor}
          onChange={(e) => onCambio(e.target.value)}
          className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
        />
      </Campo>
    );
  }

  if (q.tipo === "opcion" || q.tipo === "si_no") {
    const opciones = q.tipo === "si_no" ? ["Sí", "No"] : q.opciones;
    return (
      <Campo id={`q-${q.ulid}`} etiqueta={etiqueta} {...(q.ayuda ? { ayuda: q.ayuda } : {})}>
        <Selector id={`q-${q.ulid}`} value={valor} onChange={(e) => onCambio(e.target.value)}>
          <option value="">{t("Elige una")}</option>
          {opciones.map((o) => (
            <option key={o} value={o}>
              {t(o)}
            </option>
          ))}
        </Selector>
      </Campo>
    );
  }

  return (
    <Campo id={`q-${q.ulid}`} etiqueta={etiqueta} {...(q.ayuda ? { ayuda: q.ayuda } : {})}>
      <Entrada
        id={`q-${q.ulid}`}
        type={q.tipo === "numero" ? "number" : "text"}
        value={valor}
        onChange={(e) => onCambio(e.target.value)}
      />
    </Campo>
  );
}
