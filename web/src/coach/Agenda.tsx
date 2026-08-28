/** Agenda de la coach: calendario con alta, edición y cancelación de citas.
 *
 *  Tres vistas sobre la rejilla de `Calendario.tsx`, que no sabe nada de la API. El solape
 *  lo decide `app/dominio/agenda.py`. Cancelar exige motivo porque la alumna lo va a leer.
 */

import { CalendarPlus, ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";

import { Calendario, CalendarioMes, type CitaEnRejilla } from "@/coach/Calendario";
import { Dialogo } from "@/componentes/Dialogo";
import { AvisoSinServidor, CargandoPantalla } from "@/componentes/Estado";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Entrada,
  Etiqueta,
  Portada,
  Selector,
} from "@/componentes/primitivas";
import { useNavigate } from "react-router-dom";

import { ErrorApi, api, type AgendaApi, type CitaApi, type FilaCarteraApi } from "@/lib/api";
import { cartera as carteraDeEjemplo } from "@/lib/datos";
import { usarApiConRespaldo } from "@/lib/usarApi";
import { cn } from "@/lib/utils";
import { useIdioma } from "@/lib/idioma";

/* ------------------------------------------------------------------ Tipos --- */

type TipoCita = "consulta" | "bloqueo";
type EstadoCita = "agendada" | "confirmada" | "realizada" | "cancelada";
type Modalidad = "presencial" | "video" | "telefono";
type Vista = "dia" | "semana" | "mes";

interface Cita {
  id: string;
  titulo: string;
  tipo: TipoCita;
  estado: EstadoCita;
  modalidad: Modalidad;
  alumnaUlid: string | null;
  /** ISO local `YYYY-MM-DDTHH:mm`, en la zona de la coach. */
  iniciaEn: string;
  terminaEn: string;
  notas: string;
  motivoCancelacion: string | null;
}

const ROTULO_MODALIDAD: Record<Modalidad, string> = {
  video: "Videollamada",
  presencial: "Presencial",
  telefono: "Teléfono",
};

const DURACION_MINIMA_MIN = 10;
const DURACION_MAXIMA_MIN = 8 * 60;

const CITAS_INICIALES: Cita[] = [
  { id: "c1", titulo: "Consulta de seguimiento", tipo: "consulta", estado: "confirmada", modalidad: "video", alumnaUlid: "01JAL0003", iniciaEn: "2026-08-17T09:00", terminaEn: "2026-08-17T09:45", notas: "Revisar técnica de sentadilla.", motivoCancelacion: null },
  { id: "c2", titulo: "Revisión de chequeos de agosto", tipo: "bloqueo", estado: "agendada", modalidad: "presencial", alumnaUlid: null, iniciaEn: "2026-08-17T17:00", terminaEn: "2026-08-17T19:00", notas: "", motivoCancelacion: null },
  { id: "c3", titulo: "Alta de nueva alumna", tipo: "consulta", estado: "agendada", modalidad: "video", alumnaUlid: "01JAL0006", iniciaEn: "2026-08-19T11:30", terminaEn: "2026-08-19T12:30", notas: "Primer contacto, explicar el método.", motivoCancelacion: null },
  { id: "c4", titulo: "Grabar clips de técnica (glúteo)", tipo: "bloqueo", estado: "agendada", modalidad: "presencial", alumnaUlid: null, iniciaEn: "2026-08-20T16:00", terminaEn: "2026-08-20T18:00", notas: "", motivoCancelacion: null },
  { id: "c5", titulo: "Consulta de ajuste", tipo: "consulta", estado: "cancelada", modalidad: "telefono", alumnaUlid: "01JAL0005", iniciaEn: "2026-08-21T10:00", terminaEn: "2026-08-21T10:30", notas: "", motivoCancelacion: "La alumna se enfermó, se reagenda la próxima semana." },
];

/* ------------------------------------------------------------- Utilidades --- */

const p2 = (n: number) => String(n).padStart(2, "0");

function claveDe(d: Date): string {
  return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`;
}

function lunesDe(fecha: Date): Date {
  const d = new Date(fecha);
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7)); // lunes = 0
  d.setHours(0, 0, 0, 0);
  return d;
}

function hora(iso: string): string {
  return iso.slice(11, 16);
}

function sumarMinutos(iso: string, minutos: number): string {
  const d = new Date(iso);
  d.setMinutes(d.getMinutes() + minutos);
  return `${claveDe(d)}T${p2(d.getHours())}:${p2(d.getMinutes())}`;
}

function duracionMin(c: Pick<Cita, "iniciaEn" | "terminaEn">): number {
  return (new Date(c.terminaEn).getTime() - new Date(c.iniciaEn).getTime()) / 60_000;
}

/** Solape de intervalos medio abiertos: una cita que empieza cuando termina otra no choca. */
function chocan(a: Pick<Cita, "iniciaEn" | "terminaEn">, b: Pick<Cita, "iniciaEn" | "terminaEn">): boolean {
  return a.iniciaEn < b.terminaEn && b.iniciaEn < a.terminaEn;
}

function buscarChoque(nueva: Cita, agenda: Cita[]): Cita | undefined {
  return agenda.find((c) => c.id !== nueva.id && c.estado !== "cancelada" && chocan(nueva, c));
}

/** Traduce la cita de la API al formato local: la interfaz trabaja en hora local y la API
 *  en UTC, así que el corte se hace aquí y no en cada componente. */
function deApi(c: CitaApi): Cita {
  const local = (iso: string) => {
    const d = new Date(iso);
    return `${claveDe(d)}T${p2(d.getHours())}:${p2(d.getMinutes())}`;
  };
  return {
    id: c.ulid,
    titulo: c.titulo,
    tipo: c.tipo,
    estado: c.estado,
    modalidad: c.modalidad,
    alumnaUlid: c.alumnaUlid,
    iniciaEn: local(c.iniciaEn),
    terminaEn: local(c.terminaEn),
    notas: c.notas ?? "",
    motivoCancelacion: c.motivoCancelacion,
  };
}

function aApi(c: Cita) {
  return {
    titulo: c.titulo,
    tipo: c.tipo,
    modalidad: c.modalidad,
    alumnaUlid: c.alumnaUlid,
    iniciaEn: new Date(c.iniciaEn).toISOString(),
    terminaEn: new Date(c.terminaEn).toISOString(),
    notas: c.notas || null,
  };
}

const VACIA: Cita = {
  id: "",
  titulo: "",
  tipo: "consulta",
  estado: "agendada",
  modalidad: "video",
  alumnaUlid: null,
  iniciaEn: "",
  terminaEn: "",
  notas: "",
  motivoCancelacion: null,
};

/* ------------------------------------------------------------------ Vista --- */

export function Agenda() {
  const { t } = useIdioma();
  // En teléfono se abre en día: siete columnas en una pantalla de 6 pulgadas no se leen.
  const [vista, setVista] = useState<Vista>(() =>
    typeof window !== "undefined" && window.innerWidth < 640 ? "dia" : "semana",
  );
  const [ancla, setAncla] = useState(() => new Date());
  const [editando, setEditando] = useState<Cita | null>(null);
  const [cancelando, setCancelando] = useState<Cita | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);

  /* ---- Qué rango se pide según la vista ---- */
  const rango = useMemo(() => {
    if (vista === "dia") {
      const d = new Date(ancla);
      d.setHours(0, 0, 0, 0);
      return { inicio: d, dias: 1 };
    }
    if (vista === "semana") return { inicio: lunesDe(ancla), dias: 7 };

    // El mes se pide completo con los días de relleno de las semanas de los extremos: si no,
    // el 31 de julio aparecería vacío en la primera fila de agosto.
    const primero = new Date(ancla.getFullYear(), ancla.getMonth(), 1);
    return { inicio: lunesDe(primero), dias: 42 };
  }, [vista, ancla]);

  const navegar = useNavigate();
  const desde = rango.inicio.toISOString();
  const carga = usarApiConRespaldo<AgendaApi>(
    (senal) => api.coach.agenda(desde, rango.dias, senal),
    { citas: [], cobros: [] },
    [desde, rango.dias],
  );

  // La cartera real, para el selector de alumna y para poner su nombre en cada cita.
  const alumnas = usarApiConRespaldo<FilaCarteraApi[]>(
    (senal) => api.coach.alumnas(senal),
    carteraDeEjemplo,
  );

  // Sin servidor se trabaja sobre los datos de ejemplo, en memoria. Con servidor, la
  // escritura va a la API y se recarga: el solape lo decide el dominio, no el navegador.
  const [enMemoria, setEnMemoria] = useState<Cita[]>(CITAS_INICIALES);
  // A la defensiva: durante un despliegue el navegador puede tener el paquete nuevo y el
  // servidor el viejo, y reventar aquí dejaba la pantalla en negro.
  const respuesta = carga.datos as AgendaApi | CitaApi[] | null;
  const citasApi = Array.isArray(respuesta) ? respuesta : (respuesta?.citas ?? []);
  const cobrosApi = Array.isArray(respuesta) ? [] : (respuesta?.cobros ?? []);

  const citas = carga.sinServidor ? enMemoria : citasApi.map(deApi);
  // Los cobros del rango. No son citas: no tienen hora ni ocupan hueco, solo marcan el día.
  const cobros = carga.sinServidor ? [] : cobrosApi;

  const nombreAlumna = (ulid: string | null) =>
    ulid ? (alumnas.datos.find((a) => a.ulid === ulid)?.nombre ?? null) : null;

  const dias = useMemo(
    () =>
      Array.from({ length: vista === "mes" ? 0 : rango.dias }, (_, i) => {
        const d = new Date(rango.inicio);
        d.setDate(d.getDate() + i);
        return claveDe(d);
      }),
    [rango, vista],
  );

  const enRejilla: CitaEnRejilla[] = citas.map((c) => ({
    id: c.id,
    titulo: c.titulo,
    subtitulo: nombreAlumna(c.alumnaUlid),
    iniciaEn: c.iniciaEn,
    terminaEn: c.terminaEn,
    tono: c.estado === "cancelada" ? "cancelada" : c.tipo === "consulta" ? "consulta" : "bloqueo",
  }));

  const consultas = citas.filter((c) => c.tipo === "consulta" && c.estado !== "cancelada").length;

  function mover(direccion: -1 | 1) {
    const d = new Date(ancla);
    if (vista === "dia") d.setDate(d.getDate() + direccion);
    else if (vista === "semana") d.setDate(d.getDate() + direccion * 7);
    else d.setMonth(d.getMonth() + direccion);
    setAncla(d);
  }

  const rotuloRango =
    vista === "mes"
      ? ancla.toLocaleDateString("es-MX", { month: "long", year: "numeric" })
      : vista === "dia"
        ? ancla.toLocaleDateString("es-MX", { weekday: "long", day: "numeric", month: "long" })
        : `${rango.inicio.toLocaleDateString("es-MX", { day: "numeric", month: "short" })} – ${new Date(
            rango.inicio.getTime() + 6 * 86_400_000,
          ).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" })}`;

  /** Ejecuta la mutación y recarga. El solape lo decide el servidor; la comprobación local
   *  solo avisa antes de enviar.
   */
  async function mutar(enApi: () => Promise<unknown>, enLocal: () => void) {
    setFallo(null);
    if (carga.sinServidor) {
      enLocal();
      return;
    }
    try {
      await enApi();
      carga.recargar();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : t("No se pudo guardar."));
    }
  }

  async function guardar(cita: Cita) {
    await mutar(
      () => (cita.id ? api.coach.editarCita(cita.id, aApi(cita)) : api.coach.agendar(aApi(cita))),
      () =>
        setEnMemoria((previas) =>
          cita.id
            ? previas.map((c) => (c.id === cita.id ? cita : c))
            : [...previas, { ...cita, id: crypto.randomUUID() }],
        ),
    );
    setEditando(null);
  }

  async function cancelar(cita: Cita, motivo: string) {
    await mutar(
      () => api.coach.cancelarCita(cita.id, motivo),
      () =>
        setEnMemoria((previas) =>
          previas.map((c) =>
            c.id === cita.id ? { ...c, estado: "cancelada", motivoCancelacion: motivo } : c,
          ),
        ),
    );
    setCancelando(null);
  }

  async function eliminar(id: string) {
    await mutar(
      () => api.coach.eliminarCita(id),
      () => setEnMemoria((previas) => previas.filter((c) => c.id !== id)),
    );
    setEditando(null);
  }

  /** Tocar un hueco abre el alta ya con esa hora puesta. Es el gesto que se usa el 90 % de
   *  las veces; obligar a teclear la fecha después de haber señalado el hueco sobra. */
  function abrirEn(iso: string) {
    setEditando({ ...VACIA, iniciaEn: iso, terminaEn: sumarMinutos(iso, 60) });
  }

  if (carga.cargando) return <CargandoPantalla que={t("tu agenda")} cifras={2} columnas={2} filas={4} />;

  return (
    <div className="flex flex-col gap-6">
      {carga.sinServidor ? <AvisoSinServidor mensaje={carga.mensaje} /> : null}
      {fallo ? (
        <Aviso tono="error" titulo={t("No se pudo guardar")}>
          {fallo}
        </Aviso>
      ) : null}

      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-3">
          <Etiqueta>
            {consultas} {consultas === 1 ? t("consulta agendada") : t("consultas agendadas")}
          </Etiqueta>
          <Portada>{t("Agenda")}</Portada>
        </div>
        <Boton onClick={() => abrirEn(`${dias[0] ?? claveDe(ancla)}T09:00`)}>
          <CalendarPlus className="size-4" /> {t("Agendar")}
        </Boton>
      </header>

      {/* ---- Barra de navegación: hoy, flechas, rango y cambio de vista ---- */}
      <div className="flex flex-wrap items-center gap-2">
        <Boton tono="contorno" medida="chica" onClick={() => setAncla(new Date())}>
          {t("Hoy")}
        </Boton>
        <div className="flex items-center">
          <Boton tono="discreto" medida="icono" onClick={() => mover(-1)} aria-label={t("Anterior")}>
            <ChevronLeft className="size-4" />
          </Boton>
          <Boton tono="discreto" medida="icono" onClick={() => mover(1)} aria-label={t("Siguiente")}>
            <ChevronRight className="size-4" />
          </Boton>
        </div>

        <p className="text-menor font-medium first-letter:uppercase">{rotuloRango}</p>

        <div
          role="tablist"
          aria-label={t("Vista del calendario")}
          className="ml-auto flex overflow-hidden rounded-marco border border-linea-fuerte"
        >
          {(["dia", "semana", "mes"] as const).map((v) => (
            <button
              key={v}
              role="tab"
              aria-selected={vista === v}
              onClick={() => setVista(v)}
              className={cn(
                "h-8 px-3 text-micro font-medium transition-colors",
                vista === v ? "bg-tinta text-fondo" : "text-tinta-media hover:bg-fondo-sutil",
              )}
            >
              {v === "dia" ? t("Día") : v === "semana" ? t("Semana") : t("Mes")}
            </button>
          ))}
        </div>
      </div>

      {vista === "mes" ? (
        <CalendarioMes
          ancla={ancla}
          citas={enRejilla}
          cobros={cobros.map((c) => ({
            ulid: c.ulid,
            fecha: c.fecha,
            alumna: c.alumna.split(" ")[0] ?? c.alumna,
            monto: c.monto,
            vencido: c.vencido,
          }))}
          onTocarCobro={(ulid) => {
            const cobro = cobros.find((c) => c.ulid === ulid);
            if (cobro) void navegar(`/coach/plan/${cobro.alumnaUlid}`);
          }}
          onTocarDia={(dia) => {
            setAncla(new Date(`${dia}T12:00:00`));
            setVista("dia");
          }}
          onTocarCita={(id) => setEditando(citas.find((c) => c.id === id) ?? null)}
        />
      ) : (
        <Calendario
          dias={dias}
          citas={enRejilla}
          onTocarHueco={abrirEn}
          onTocarCita={(id) => setEditando(citas.find((c) => c.id === id) ?? null)}
        />
      )}

      <div className="flex flex-wrap items-center gap-4">
        <Leyenda tono="bg-acento">{t("Consulta")}</Leyenda>
        <Leyenda tono="bg-tinta-suave">{t("Bloque de trabajo")}</Leyenda>
        <Apoyo>{t("Toca un hueco para agendar ahí.")}</Apoyo>
      </div>

      {editando ? (
        <FormularioCita
          cita={editando}
          agenda={citas}
          alumnas={alumnas.datos}
          onGuardar={guardar}
          onCancelarCita={(c) => {
            setEditando(null);
            setCancelando(c);
          }}
          onEliminar={eliminar}
          onCerrar={() => setEditando(null)}
        />
      ) : null}

      {cancelando ? (
        <FormularioCancelacion
          cita={cancelando}
          nombreAlumna={nombreAlumna(cancelando.alumnaUlid)}
          onConfirmar={cancelar}
          onCerrar={() => setCancelando(null)}
        />
      ) : null}
    </div>
  );
}

function Leyenda({ tono, children }: { tono: string; children: string }) {
  return (
    <span className="flex items-center gap-2 text-micro text-tinta-media">
      <span className={cn("h-3 w-1 rounded-full", tono)} />
      {children}
    </span>
  );
}

/* ------------------------------------------------------------ Formulario --- */

function FormularioCita({
  cita,
  agenda,
  alumnas,
  onGuardar,
  onCancelarCita,
  onEliminar,
  onCerrar,
}: {
  cita: Cita;
  agenda: Cita[];
  alumnas: FilaCarteraApi[];
  onGuardar: (c: Cita) => void;
  onCancelarCita: (c: Cita) => void;
  onEliminar: (id: string) => void;
  onCerrar: () => void;
}) {
  const { t } = useIdioma();
  const [borrador, setBorrador] = useState<Cita>(cita);
  const esNueva = !cita.id;

  const cambiar = <K extends keyof Cita>(campo: K, valor: Cita[K]) =>
    setBorrador((b) => ({ ...b, [campo]: valor }));

  // Las mismas guardas que aplica el servidor, para avisar antes de enviar.
  const duracion = duracionMin(borrador);
  const choque = buscarChoque(borrador, agenda);

  const problema =
    !borrador.titulo.trim()
      ? t("Ponle un título: es lo que ve la paciente en su recordatorio.")
      : borrador.terminaEn <= borrador.iniciaEn
        ? t("La hora de fin tiene que ser posterior a la de inicio.")
        : duracion < DURACION_MINIMA_MIN
          ? t("Muy corta. El mínimo son {min} minutos.", { min: DURACION_MINIMA_MIN })
          : duracion > DURACION_MAXIMA_MIN
            ? t("Más de 8 horas: revisa que la fecha de fin sea la correcta.")
            : !borrador.alumnaUlid
              ? t("Elige de quién es: toda cita va también al expediente de la paciente.")
              : null;

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={esNueva ? t("Nueva cita") : t("Editar cita")}
      titulo={esNueva ? t("Agendar") : borrador.titulo || t("Sin título")}
      pie={
        <>
          {!esNueva && borrador.estado !== "cancelada" ? (
            <Boton tono="peligro" medida="chica" onClick={() => onCancelarCita(borrador)}>
              {t("Cancelar cita")}
            </Boton>
          ) : null}
          {!esNueva ? (
            <Boton tono="discreto" medida="chica" onClick={() => onEliminar(borrador.id)}>
              {t("Eliminar")}
            </Boton>
          ) : null}
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            {t("Cerrar")}
          </Boton>
          <Boton
            medida="chica"
            disabled={problema !== null || choque !== undefined}
            onClick={() => onGuardar(borrador)}
          >
            {esNueva ? t("Agendar") : t("Guardar")}
          </Boton>
        </>
      }
    >
      <Campo id="cita-titulo" etiqueta={t("Título")}>
        <Entrada
          id="cita-titulo"
          value={borrador.titulo}
          onChange={(e) => cambiar("titulo", e.target.value)}
          placeholder={t("Consulta de seguimiento")}
        />
      </Campo>

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="cita-tipo" etiqueta={t("Tipo")}>
          <Selector
            id="cita-tipo"
            value={borrador.tipo}
            onChange={(e) => {
              // La alumna no se limpia al cambiar de tipo: toda cita es de alguien, y un
              // bloque de trabajo también se le agenda a una persona concreta.
              setBorrador((b) => ({ ...b, tipo: e.target.value as TipoCita }));
            }}
          >
            <option value="consulta">{t("Consulta con paciente")}</option>
            <option value="bloqueo">{t("Bloque de trabajo")}</option>
          </Selector>
        </Campo>

        <Campo id="cita-modalidad" etiqueta={t("Modalidad")}>
          <Selector
            id="cita-modalidad"
            value={borrador.modalidad}
            onChange={(e) => cambiar("modalidad", e.target.value as Modalidad)}
          >
            {(Object.keys(ROTULO_MODALIDAD) as Modalidad[]).map((m) => (
              <option key={m} value={m}>
                {t(ROTULO_MODALIDAD[m])}
              </option>
            ))}
          </Selector>
        </Campo>
      </div>

      <Campo id="cita-alumna" etiqueta={t("Paciente")}>
          <Selector
            id="cita-alumna"
            value={borrador.alumnaUlid ?? ""}
            onChange={(e) => cambiar("alumnaUlid", e.target.value || null)}
          >
            <option value="">{t("Elige una…")}</option>
            {alumnas.map((a) => (
              <option key={a.ulid} value={a.ulid}>
                {a.nombre}
              </option>
            ))}
        </Selector>
      </Campo>

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="cita-inicia" etiqueta={t("Empieza")}>
          <Entrada
            id="cita-inicia"
            type="datetime-local"
            value={borrador.iniciaEn}
            onChange={(e) => {
              // Mover el inicio arrastra el fin y conserva la duración: es lo que se espera
              // al reagendar, y evita dejar una cita con fin anterior al inicio.
              const previa = duracionMin(borrador);
              setBorrador((b) => ({
                ...b,
                iniciaEn: e.target.value,
                terminaEn: sumarMinutos(e.target.value, previa > 0 ? previa : 60),
              }));
            }}
          />
        </Campo>
        <Campo
          id="cita-termina"
          etiqueta={t("Termina")}
          ayuda={duracion > 0 ? t("{min} minutos", { min: duracion }) : undefined}
        >
          <Entrada
            id="cita-termina"
            type="datetime-local"
            value={borrador.terminaEn}
            onChange={(e) => cambiar("terminaEn", e.target.value)}
          />
        </Campo>
      </div>

      <div className="flex flex-wrap gap-2">
        {[30, 45, 60, 90].map((min) => (
          <Boton
            key={min}
            tono={duracion === min ? "solido" : "contorno"}
            medida="chica"
            onClick={() => cambiar("terminaEn", sumarMinutos(borrador.iniciaEn, min))}
          >
            {min} min
          </Boton>
        ))}
      </div>

      <Campo id="cita-notas" etiqueta={t("Notas")}>
        <textarea
          id="cita-notas"
          value={borrador.notas}
          onChange={(e) => cambiar("notas", e.target.value)}
          rows={3}
          className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
          placeholder={t("Qué quieres cubrir en esta cita")}
        />
      </Campo>

      {choque ? (
        <Aviso tono="error" titulo={t("Ya tienes algo a esa hora")}>
          {t("«{titulo}», de {inicio} a {fin}. Mueve una de las dos.", {
            titulo: choque.titulo,
            inicio: hora(choque.iniciaEn),
            fin: hora(choque.terminaEn),
          })}
        </Aviso>
      ) : problema ? (
        <Aviso tono="atencion">{problema}</Aviso>
      ) : null}

      {borrador.estado === "cancelada" && borrador.motivoCancelacion ? (
        <Aviso tono="info" titulo={t("Cita cancelada")}>
          {borrador.motivoCancelacion}
        </Aviso>
      ) : null}
    </Dialogo>
  );
}

function FormularioCancelacion({
  cita,
  nombreAlumna,
  onConfirmar,
  onCerrar,
}: {
  cita: Cita;
  nombreAlumna: string | null;
  onConfirmar: (c: Cita, motivo: string) => void;
  onCerrar: () => void;
}) {
  const { t } = useIdioma();
  const [motivo, setMotivo] = useState("");

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={t("Cancelar cita")}
      titulo={cita.titulo}
      descripcion={`${hora(cita.iniciaEn)}–${hora(cita.terminaEn)}`}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            {t("Mejor no")}
          </Boton>
          <Boton
            tono="peligro"
            medida="chica"
            disabled={!motivo.trim()}
            onClick={() => onConfirmar(cita, motivo.trim())}
          >
            {t("Cancelar y avisar")}
          </Boton>
        </>
      }
    >
      <Apoyo>
        {nombreAlumna
          ? t("«{nombre}» recibirá un aviso con el motivo tal como lo escribas.", {
              nombre: nombreAlumna,
            })
          : t("El bloque se libera y la hora vuelve a quedar disponible.")}
      </Apoyo>

      <Campo id="motivo-cancelacion" etiqueta={t("Motivo")}>
        <textarea
          id="motivo-cancelacion"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          rows={3}
          className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
          placeholder={t("Se me empalmó una urgencia, te reagendo el jueves.")}
        />
      </Campo>
    </Dialogo>
  );
}
