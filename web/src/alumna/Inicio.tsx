/** Inicio de la alumna: qué le toca hoy.
 *
 *  Abre con el dato, no con adorno. Lo secundario —cuenta, mensajes, avisos— vive al pie
 *  para no gastar una pestaña en ello.
 */

import { ArrowRight, CalendarPlus, CalendarDays, Upload, Wallet } from "lucide-react";
import { useRef, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { cn } from "@/lib/utils";

import {
  AvisoSinServidor,
  Cargando,
  EsqueletoCifras,
  EsqueletoPortada,
  EsqueletoTarjeta,
} from "@/componentes/Estado";
import { Apoyo, Aviso, Boton, Chip, Dato, Etiqueta, Portada, Regla, Tarjeta, Titulo } from "@/componentes/primitivas";
import {
  ErrorApi,
  api,
  type CitaDeAlumnaApi,
  type CobroApi2,
  type InicioAlumnaApi,
} from "@/lib/api";
import { chequeos, ciclo, mensajes, alumna } from "@/lib/datos";
import { delta, diaSemana, fecha, horaLocal, num } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
import { usarApi, usarApiConRespaldo } from "@/lib/usarApi";
import { ROTULO_ESTADO, type EstadoChequeo } from "@/lib/tipos";
import { DatosBancarios } from "@/alumna/DatosBancarios";

/** Datos de ejemplo para revisar la pantalla sin servidor. Desaparece con la API en pie. */
const RESPALDO: InicioAlumnaApi = {
  perfil: {
    ulid: alumna.ulid,
    nombre: alumna.nombre,
    correo: alumna.email,
    estaturaCm: alumna.estaturaCm,
    plan: null,
    basculaRef: alumna.basculaRef,
    lugarRef: alumna.lugarRef,
    horaRef: alumna.horaRef,
    zonaHoraria: alumna.zonaHoraria,
    cuestionarioCompleto: true,
    estado: "activa",
    borraEn: null,
  },
  ciclo: {
    numero: ciclo.numero,
    iniciaEn: ciclo.iniciaEn,
    terminaEn: ciclo.terminaEn,
    estadoPago: ciclo.estadoPago,
    precio: ciclo.precio,
  },
  chequeos,
  ultimoFeedback: [...chequeos].reverse().find((c) => c.feedback)?.feedback ?? null,
  avisosSinLeer: 0,
  ultimoAviso: null,
  coach: "Mariana Cervantes",
  proximasCitas: [],
  plan: null,
};

export function Inicio() {
  const { t } = useIdioma();
  const { datos, cargando, sinServidor, mensaje, codigo } = usarApiConRespaldo<InicioAlumnaApi>(
    (senal) => api.alumna.inicio(senal),
    RESPALDO,
  );

  if (cargando)
    return (
      <Cargando
        que={t("tu inicio")}
        esqueleto={
          <div className="flex flex-col gap-12">
            <EsqueletoPortada />
            <EsqueletoCifras cuantas={3} />
            <EsqueletoTarjeta lineas={2} />
          </div>
        }
      />
    );

  // Se registró sola y su coach todavía no la acepta: su recorrido está en otra pantalla,
  // y el panel entero le respondería 403.
  if (codigo === "SOLICITUD_SIN_ACEPTAR") return <Navigate to="/solicitud" replace />;

  // Antes que nada: quién es su coach y qué necesita saber de ella. Sin esto el plan se
  // arma a ciegas, y pedirlo después es pedirlo cuando ya nadie lo contesta.
  if (!datos.perfil.cuestionarioCompleto) return <Navigate to="/bienvenida" replace />;

  const historico = datos.chequeos;

  // Sin un solo chequeo no hay nada que comparar, y el panel entero se apoya en el
  // último: sin esto la pantalla se quedaba en negro.
  if (historico.length === 0) {
    return <PrimerChequeo nombre={datos.perfil.nombre} coach={datos.coach} />;
  }

  const ultimo = historico.at(-1)!;
  const previo = historico.at(-2) ?? ultimo;
  const base = historico[0]!;
  const primerNombre = datos.perfil.nombre.split(" ")[0] ?? "";
  const nombreCoach = datos.coach.split(" ")[0] ?? "";

  const dPeso = delta(ultimo.pesoKg ?? 0, previo.pesoKg, "kg");
  const dCintura = delta(ultimo.medidas.cintura ?? 0, previo.medidas.cintura, "cm");
  const dTotal = delta(ultimo.pesoKg ?? 0, base.pesoKg, "kg");

  return (
    <div className="flex flex-col gap-12">
      {/* ---- Encabezado ---- */}
      <header className="flex flex-col gap-3">
        <Etiqueta>{diaSemana("2026-08-13")}</Etiqueta>
        <Portada>{t("Hola, {nombre}", { nombre: primerNombre })}</Portada>
        {datos.ciclo ? (
          <Apoyo>
            {t("Ciclo {n} · termina el {fecha}", {
              n: datos.ciclo.numero,
              fecha: fecha(datos.ciclo.terminaEn),
            })}
          </Apoyo>
        ) : null}
      </header>

      {sinServidor ? <AvisoSinServidor mensaje={mensaje} /> : null}

      {/* Dada de baja: lo primero que tiene que ver es hasta cuándo puede bajar lo suyo. */}
      {datos.perfil.estado === "baja" && datos.perfil.borraEn ? (
        <Aviso
          tono="error"
          titulo={t("Tu cuenta se cierra el {fecha}", { fecha: fecha(datos.perfil.borraEn) })}
        >
          {t("{coach} dio de baja tu cuenta. Hasta esa fecha puedes entrar y descargar lo tuyo; después se borra todo, incluidas tus fotos y tu historial.", {
            coach: nombreCoach,
          })}{" "}
          <a href="/api/documentos/evolucion" className="underline underline-offset-2">
            {t("Descargar mi expediente")}
          </a>
        </Aviso>
      ) : null}

      {datos.avisosSinLeer > 0 ? (
        <Aviso
          tono="atencion"
          titulo={
            datos.ultimoAviso ??
            (datos.avisosSinLeer === 1
              ? t("Tienes un aviso")
              : t("Tienes {n} avisos", { n: datos.avisosSinLeer }))
          }
        >
          <Link to="/avisos" className="underline underline-offset-2">
            {datos.avisosSinLeer === 1
              ? t("Ábrelo")
              : t("Ver tus {n} avisos", { n: datos.avisosSinLeer })}
          </Link>
        </Aviso>
      ) : null}

      <ProximasFechas ciclo={datos.ciclo} citas={datos.proximasCitas} />

      <SubirComprobante />

      {/* ---- Lo que toca hoy ---- */}
      <section className="filete flex flex-col gap-4">
        <Etiqueta>{datos.plan ? t("Hoy te toca") : t("Tu plan")}</Etiqueta>
        <div className="flex flex-col gap-1">
          {/* Sin plan publicado no se inventa uno: antes salía una rutina de ejemplo y una
              alumna recién dada de alta creía tener ejercicios asignados. */}
          <Titulo>{datos.plan?.primerDia ?? t("Todavía no tienes plan")}</Titulo>
          <Apoyo>
            {datos.plan
              ? [
                  datos.plan.diasEntrenamiento > 0
                    ? t("{n} días de entrenamiento", { n: datos.plan.diasEntrenamiento })
                    : null,
                  datos.plan.kcalObjetivo ? `${datos.plan.kcalObjetivo} kcal` : null,
                ]
                  .filter(Boolean)
                  .join(" · ")
              : t("{coach} lo está armando. Te avisamos en cuanto lo publique.", {
                  coach: nombreCoach,
                })}
          </Apoyo>
        </div>
        <div>
          <Boton asChild medida="grande" className="hunde">
            <Link to="/plan">
              {t("Abrir mi plan")} <ArrowRight className="size-4 transition-transform duration-[var(--mov-rapido)] ease-salida group-hover:translate-x-0.5" />
            </Link>
          </Boton>
        </div>
      </section>

      <Regla />

      {/* ---- Cifras ---- */}
      <section className="escalona grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-3">
        <Dato
          rotulo={t("Peso")}
          valor={num(ultimo.pesoKg)}
          unidad="kg"
          nota={dPeso ? t("{delta} desde julio", { delta: dPeso.texto }) : undefined}
          direccion={dPeso?.direccion}
        />
        <Dato
          rotulo={t("Cintura")}
          valor={num(ultimo.medidas.cintura)}
          unidad="cm"
          nota={dCintura ? t("{delta} desde julio", { delta: dCintura.texto }) : undefined}
          direccion={dCintura?.direccion}
        />
        <Dato
          rotulo={t("Desde que empezaste")}
          valor={num(Math.abs(dTotal?.valor ?? 0))}
          unidad="kg"
          nota={t("{signo} en {n} chequeos", {
            signo: (dTotal?.valor ?? 0) < 0 ? t("menos") : t("más"),
            n: historico.length,
          })}
        />
      </section>

      <Regla />

      {/* ---- Chequeo del mes ---- */}
      {ultimo.estado !== "validado" ? (
        <Tarjeta acentuada className="flex flex-col gap-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex flex-col gap-1">
              <Etiqueta>
                {t("Chequeo #{numero} · {fecha}", {
                  numero: ultimo.numero,
                  fecha: fecha(ultimo.fecha),
                })}
              </Etiqueta>
              <Titulo>{t("{coach} lo está revisando", { coach: nombreCoach })}</Titulo>
            </div>
            <Chip tono="espera">{t(ROTULO_ESTADO[ultimo.estado as EstadoChequeo])}</Chip>
          </div>
          <Apoyo className="medida">
            {t("Enviaste tus ocho medidas, tu peso y las tres fotos el {fecha}. En cuanto lo valide te avisamos y se libera tu plan del ciclo siguiente.", {
              fecha: fecha(ultimo.fecha),
            })}
          </Apoyo>
          <div className="flex flex-wrap gap-2">
            <Boton asChild tono="contorno">
              <Link to="/evolucion">{t("Ver lo que enviaste")}</Link>
            </Boton>
            <Boton asChild tono="discreto">
              <Link to="/chequeo">{t("Empezar el del mes que entra")}</Link>
            </Boton>
          </div>
        </Tarjeta>
      ) : null}

      {/* ---- Último feedback ---- */}
      {datos.ultimoFeedback ? (
        <section className="flex flex-col gap-3">
          <Etiqueta>{t("Lo último que te dijo {coach}", { coach: nombreCoach })}</Etiqueta>
          <blockquote className="medida text-guia leading-relaxed text-balance">
            «{datos.ultimoFeedback}»
          </blockquote>
          <Apoyo>{t("{n} mensajes en tu hilo", { n: mensajes.length })}</Apoyo>
        </section>
      ) : null}

      <Regla />

      {/* ---- Lo secundario, al pie: no gasta una pestaña ---- */}
    </div>
  );
}

/* ---------------------------------------------------- Próximas fechas --- */

const ROTULO_MODALIDAD: Record<string, string> = {
  video: "Videollamada",
  presencial: "Presencial",
  telefono: "Llamada",
};

/** Días que faltan por día calendario, no por horas: una cita de mañana a las 9 está a 14
 *  horas, pero lo que la alumna piensa es «mañana».
 */
function diasHasta(iso: string): number {
  const objetivo = new Date(iso);
  const hoy = new Date();
  objetivo.setHours(0, 0, 0, 0);
  hoy.setHours(0, 0, 0, 0);
  return Math.round((objetivo.getTime() - hoy.getTime()) / 86_400_000);
}

function cuando(dias: number): { clave: string; dias?: number } {
  if (dias <= 0) return { clave: "hoy" };
  if (dias === 1) return { clave: "mañana" };
  return { clave: "en {dias} días", dias };
}

/** El pago del ciclo y las consultas: las dos únicas fechas que tiene que recordar. */
function ProximasFechas({
  ciclo,
  citas,
}: {
  ciclo: InicioAlumnaApi["ciclo"];
  citas: CitaDeAlumnaApi[];
}) {
  const { t } = useIdioma();
  // Sin ciclo ni citas la sección sigue en pie: ahí vive el botón de reservar.
  const vacia = !ciclo && citas.length === 0;

  const diasParaPago = ciclo ? diasHasta(ciclo.terminaEn) : null;
  const vencido = diasParaPago !== null && diasParaPago < 0;
  const urgePago = diasParaPago !== null && diasParaPago >= 0 && diasParaPago <= 5;

  return (
    <section className="flex flex-col gap-4">
      <Etiqueta icono={CalendarDays}>{t("Próximas fechas")}</Etiqueta>

      <ul
        className={cn(
          "escalona flex flex-col divide-y divide-linea",
          !vacia && "border-y border-linea",
        )}
      >
        {ciclo ? (
          <li className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3">
            <span className="flex min-w-0 flex-col gap-0.5">
              <span className="text-menor font-medium">
                {ciclo.estadoPago === "validado"
                  ? t("Renovación de tu ciclo")
                  : t("Pago de tu ciclo")}
              </span>
              <span className="text-micro text-tinta-suave">
                {t("Ciclo {n}", { n: ciclo.numero })} · ${num(ciclo.precio)}
              </span>
            </span>
            <span className="flex items-baseline gap-3">
              <span className="cifra text-menor">{fecha(ciclo.terminaEn)}</span>
              <Chip tono={vencido ? "error" : urgePago ? "espera" : "neutro"}>
                {vencido
                  ? t("vencido")
                  : (() => {
                      const c = cuando(diasParaPago ?? 0);
                      return t(c.clave, { dias: c.dias ?? 0 });
                    })()}
              </Chip>
            </span>
          </li>
        ) : null}

        {citas.map((c) => {
          const dias = diasHasta(c.iniciaEn);
          const cita = cuando(dias);
          return (
            <li
              key={c.ulid}
              className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3"
            >
              <span className="flex min-w-0 flex-col gap-0.5">
                <span className="text-menor font-medium">{c.titulo}</span>
                <span className="text-micro text-tinta-suave">
                  {t(ROTULO_MODALIDAD[c.modalidad] ?? c.modalidad)}
                  {c.estado === "confirmada" ? ` · ${t("confirmada")}` : ""}
                </span>
              </span>
              <span className="flex items-baseline gap-3">
                <span className="cifra text-menor">
                  {fecha(c.iniciaEn)} · {horaLocal(c.iniciaEn)}
                </span>
                <Chip tono={dias <= 1 ? "espera" : "neutro"}>
                  {t(cita.clave, { dias: cita.dias ?? 0 })}
                </Chip>
              </span>
            </li>
          );
        })}
      </ul>

      <div className="flex flex-wrap items-center gap-3">
        <Boton asChild tono="contorno" medida="chica">
          <Link to="/reservar">
            <CalendarPlus className="size-3.5" /> {t("Reservar consulta")}
          </Link>
        </Boton>
        {citas.length === 0 ? (
          <Apoyo>{t("Todavía no tienes ninguna agendada.")}</Apoyo>
        ) : null}
      </div>
    </section>
  );
}

/* -------------------------------------------------- Comprobante de pago --- */

/** Lo que debe, con el botón para subir su comprobante. Elige contra qué cobro paga, así
 *  la coach lo recibe emparejado en vez de adivinar a qué corresponde.
 */
function SubirComprobante() {
  const { t } = useIdioma();
  const carga = usarApi<CobroApi2[]>((senal) => api.alumna.cobros(senal));
  const entrada = useRef<HTMLInputElement>(null);
  const [subiendo, setSubiendo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elegido, setElegido] = useState<string | null>(null);

  const cobros = (carga.datos ?? []).filter((c) => c.estado !== "pagado");
  if (cobros.length === 0) return null;

  async function subir(archivo: File) {
    if (!elegido) return;
    setError(null);
    setSubiendo(elegido);
    try {
      await api.alumna.subirComprobante(elegido, archivo);
      carga.recargar();
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo subir el comprobante.");
    } finally {
      setSubiendo(null);
      setElegido(null);
      if (entrada.current) entrada.current.value = "";
    }
  }

  return (
    <Tarjeta className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <Etiqueta icono={Wallet}>{t("Tus pagos")}</Etiqueta>
          <Titulo>
            {cobros.some((c) => c.vencido)
              ? t("Tienes un pago atrasado")
              : t("Lo que te toca pagar")}
          </Titulo>
        </div>
      </div>

      <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
        {cobros.map((c) => (
          <li key={c.ulid} className="flex flex-col gap-2 py-3">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <span className="flex min-w-0 flex-col gap-0.5">
                <span className="text-menor font-medium">{c.concepto}</span>
                <span className="text-micro text-tinta-suave">{fecha(c.fecha)}</span>
              </span>
              <span className="flex items-center gap-3">
                <span className="cifra font-semibold">${num(c.monto)}</span>
                {c.estado === "en_revision" ? (
                  <Chip tono="espera">{t("En revisión")}</Chip>
                ) : c.vencido ? (
                  <Chip tono="error">{t("Vencido")}</Chip>
                ) : null}
              </span>
            </div>

            {c.motivoRechazo ? (
              <Aviso tono="atencion" titulo={t("Tu coach pidió otro comprobante")}>
                {c.motivoRechazo}
              </Aviso>
            ) : null}

            {c.estado === "en_revision" ? (
              <Apoyo>{t("Tu coach lo está revisando. Te avisamos en cuanto lo confirme.")}</Apoyo>
            ) : (
              <div>
                <Boton
                  tono="contorno"
                  medida="chica"
                  cargando={subiendo === c.ulid}
                  disabled={subiendo !== null}
                  onClick={() => {
                    setElegido(c.ulid);
                    entrada.current?.click();
                  }}
                >
                  {subiendo === c.ulid ? null : <Upload className="size-3.5" />}
                  {t("Subir comprobante")}
                </Boton>
              </div>
            )}
          </li>
        ))}
      </ul>

      <DatosBancarios texto={cobros[0]?.datosBancarios} />

      <input
        ref={entrada}
        type="file"
        accept="image/*,application/pdf"
        className="hidden"
        onChange={(e) => {
          const archivo = e.target.files?.[0];
          if (archivo) void subir(archivo);
        }}
      />

      {error ? <Aviso tono="error">{t(error)}</Aviso> : null}

      <Apoyo>
        {t("Tu coach confirma cada pago contra su estado de cuenta. Un pago vencido pausa tu plan hasta que lo valide.")}
      </Apoyo>
    </Tarjeta>
  );
}

/** Lo que ve quien acaba de entrar y no se ha medido: es el último paso del alta, y sin su
 *  primer chequeo la coach no puede calcular nada.
 */
function PrimerChequeo({ nombre, coach }: { nombre: string; coach: string }) {
  const { t } = useIdioma();
  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta>{t("Ya casi")}</Etiqueta>
        <Portada>{t("Hola, {nombre}", { nombre: nombre.split(" ")[0] ?? "" })}</Portada>
        <Apoyo>
          {t("Falta lo último: tu primer chequeo. De ahí salen tu peso, tus medidas y el punto de partida con el que {coach} arma tu plan.", {
            coach: coach.split(" ")[0] ?? "",
          })}
        </Apoyo>
      </header>

      <section className="filete flex flex-col gap-4">
        <Etiqueta>{t("Qué te va a pedir")}</Etiqueta>
        <ul className="flex flex-col gap-2 text-menor text-tinta-media">
          <li>{t("Cómo llegas hoy: en ayunas, sin entrenar, recién despierta.")}</li>
          <li>{t("Tu peso.")}</li>
          <li>{t("Tus medidas: cintura, cadera, brazo y las demás.")}</li>
          <li>{t("Tres fotos. Se guardan sin cara y se borran a los cuatro meses, menos la primera y la última.")}</li>
        </ul>
        <Apoyo>{t("Son unos diez minutos. Puedes dejarlo a medias y seguir después.")}</Apoyo>
        <div>
          <Boton asChild medida="grande">
            <Link to="/chequeo">
              {t("Empezar mi chequeo")} <ArrowRight className="size-4" />
            </Link>
          </Boton>
        </div>
      </section>

      {/* Esta pantalla sustituye al inicio entero, y con él a su barra: sin salida, quien
          entra por error no puede ni volver al acceso. */}
      <Regla />
    </div>
  );
}
