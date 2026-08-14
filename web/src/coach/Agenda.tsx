/** Agenda de la coach: consultas y bloques de trabajo, con alta, edición y cancelación.
 *
 *  Dos citas no pueden solaparse aunque una sea consulta y la otra un bloque propio: el
 *  tiempo de la coach es uno solo. Esa regla se evalúa aquí para avisar de inmediato, y se
 *  vuelve a evaluar en el servidor (`app/dominio/agenda.py`), que es donde manda.
 *
 *  Cancelar exige motivo porque la alumna lo va a leer.
 */

import { CalendarPlus, ChevronLeft, ChevronRight, Video } from "lucide-react";
import { useMemo, useState } from "react";

import { Dialogo } from "@/componentes/Dialogo";
import { AvisoSinServidor, Cargando } from "@/componentes/Estado";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Chip,
  Entrada,
  Etiqueta,
  Portada,
  Selector,
  Vacio,
} from "@/componentes/primitivas";
import { ErrorApi, api, type CitaApi } from "@/lib/api";
import { cartera } from "@/lib/datos";
import { usarApiConRespaldo } from "@/lib/usarApi";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ Tipos --- */

type TipoCita = "consulta" | "bloqueo";
type EstadoCita = "agendada" | "confirmada" | "realizada" | "cancelada";
type Modalidad = "presencial" | "video" | "telefono";

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

const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

function lunesDe(fecha: Date): Date {
  const d = new Date(fecha);
  const desplazamiento = (d.getDay() + 6) % 7; // lunes = 0
  d.setDate(d.getDate() - desplazamiento);
  d.setHours(0, 0, 0, 0);
  return d;
}

function claveDia(iso: string): string {
  return iso.slice(0, 10);
}

function hora(iso: string): string {
  return iso.slice(11, 16);
}

function minutos(iso: string): number {
  const [h, m] = iso.slice(11, 16).split(":").map(Number);
  return (h ?? 0) * 60 + (m ?? 0);
}

function duracionMin(c: Pick<Cita, "iniciaEn" | "terminaEn">): number {
  return (
    (new Date(c.terminaEn).getTime() - new Date(c.iniciaEn).getTime()) / 60_000
  );
}

/** Solape de intervalos medio abiertos: una cita que empieza cuando termina otra no choca. */
function chocan(a: Pick<Cita, "iniciaEn" | "terminaEn">, b: Pick<Cita, "iniciaEn" | "terminaEn">): boolean {
  return a.iniciaEn < b.terminaEn && b.iniciaEn < a.terminaEn;
}

function buscarChoque(nueva: Cita, agenda: Cita[]): Cita | undefined {
  return agenda.find((c) => c.id !== nueva.id && c.estado !== "cancelada" && chocan(nueva, c));
}

function nombreAlumna(ulid: string | null): string | null {
  if (!ulid) return null;
  return cartera.find((a) => a.ulid === ulid)?.nombre ?? null;
}

const VACIA: Cita = {
  id: "",
  titulo: "",
  tipo: "consulta",
  estado: "agendada",
  modalidad: "video",
  alumnaUlid: null,
  iniciaEn: "2026-08-17T09:00",
  terminaEn: "2026-08-17T10:00",
  notas: "",
  motivoCancelacion: null,
};

/* ------------------------------------------------------------------ Vista --- */

/** Traduce la cita de la API al formato local: la interfaz trabaja en hora local y la API
 *  en UTC, así que el corte se hace aquí y no en cada componente. */
function deApi(c: CitaApi): Cita {
  const local = (iso: string) => {
    const d = new Date(iso);
    const p = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
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

export function Agenda() {
  const [semana, setSemana] = useState(() => lunesDe(new Date("2026-08-17T12:00:00")));
  const [editando, setEditando] = useState<Cita | null>(null);
  const [cancelando, setCancelando] = useState<Cita | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);

  const desde = semana.toISOString();
  const carga = usarApiConRespaldo<CitaApi[]>(
    (senal) => api.coach.agenda(desde, 7, senal),
    [],
    [desde],
  );

  // Sin servidor se trabaja sobre los datos de ejemplo, en memoria. Con servidor, la
  // escritura va a la API y se recarga: el solape lo decide el dominio, no el navegador.
  const [enMemoria, setEnMemoria] = useState<Cita[]>(CITAS_INICIALES);
  const citas = carga.sinServidor ? enMemoria : carga.datos.map(deApi);
  const setCitas = setEnMemoria;

  const dias = useMemo(
    () =>
      DIAS.map((rotulo, i) => {
        const d = new Date(semana);
        d.setDate(d.getDate() + i);
        const clave = d.toISOString().slice(0, 10);
        return {
          rotulo,
          clave,
          numero: d.getDate(),
          citas: citas
            .filter((c) => claveDia(c.iniciaEn) === clave)
            .sort((a, b) => minutos(a.iniciaEn) - minutos(b.iniciaEn)),
        };
      }),
    [semana, citas],
  );

  const consultas = citas.filter((c) => c.tipo === "consulta" && c.estado !== "cancelada").length;

  function moverSemana(delta: number) {
    const d = new Date(semana);
    d.setDate(d.getDate() + delta * 7);
    setSemana(d);
  }

  /** Ejecuta la mutación contra la API y recarga; si no hay servidor, la aplica en memoria.
   *
   *  El solape lo decide el dominio del servidor, no el navegador: la comprobación local es
   *  solo para avisar antes de enviar. Si el servidor rechaza, su mensaje se muestra tal cual.
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
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo guardar.");
    }
  }

  async function guardar(cita: Cita) {
    await mutar(
      () => (cita.id ? api.coach.editarCita(cita.id, aApi(cita)) : api.coach.agendar(aApi(cita))),
      () =>
        setCitas((previas) =>
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
        setCitas((previas) =>
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
      () => setCitas((previas) => previas.filter((c) => c.id !== id)),
    );
    setEditando(null);
  }

  if (carga.cargando) return <Cargando que="tu agenda" />;

  return (
    <div className="flex flex-col gap-10">
      {carga.sinServidor ? <AvisoSinServidor mensaje={carga.mensaje} /> : null}
      {fallo ? (
        <Aviso tono="error" titulo="No se pudo guardar">
          {fallo}
        </Aviso>
      ) : null}

      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-3">
          <Etiqueta>
            {consultas} {consultas === 1 ? "consulta agendada" : "consultas agendadas"}
          </Etiqueta>
          <Portada>Agenda</Portada>
        </div>
        <Boton
          onClick={() => setEditando({ ...VACIA, iniciaEn: `${dias[0]!.clave}T09:00`, terminaEn: `${dias[0]!.clave}T10:00` })}
        >
          <CalendarPlus className="size-4" /> Agendar
        </Boton>
      </header>

      {/* ---- Navegación de semana ---- */}
      <div className="flex items-center justify-between gap-3">
        <Boton tono="contorno" medida="icono" onClick={() => moverSemana(-1)} aria-label="Semana anterior">
          <ChevronLeft className="size-4" />
        </Boton>
        <p className="text-menor font-medium">
          {new Date(dias[0]!.clave).toLocaleDateString("es-MX", { day: "numeric", month: "long" })} —{" "}
          {new Date(dias[6]!.clave).toLocaleDateString("es-MX", { day: "numeric", month: "long", year: "numeric" })}
        </p>
        <Boton tono="contorno" medida="icono" onClick={() => moverSemana(1)} aria-label="Semana siguiente">
          <ChevronRight className="size-4" />
        </Boton>
      </div>

      {/* ---- Rejilla semanal. En teléfono se apila un día tras otro. ---- */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {dias.map((dia) => (
          <section key={dia.clave} className="flex flex-col gap-2">
            <div className="flex items-baseline justify-between border-b border-linea pb-2">
              <h2 className="text-menor font-semibold">{dia.rotulo}</h2>
              <span className="cifra text-micro text-tinta-suave">{dia.numero}</span>
            </div>

            {dia.citas.length === 0 ? (
              <button
                onClick={() => setEditando({ ...VACIA, iniciaEn: `${dia.clave}T09:00`, terminaEn: `${dia.clave}T10:00` })}
                className="rounded-marco border border-dashed border-linea py-6 text-micro text-tinta-suave transition-colors hover:border-tinta hover:text-tinta"
              >
                Libre · agendar
              </button>
            ) : (
              <ul className="flex flex-col gap-2">
                {dia.citas.map((c) => (
                  <li key={c.id}>
                    <button
                      onClick={() => setEditando(c)}
                      className={cn(
                        "flex w-full flex-col gap-1 rounded-marco border border-linea border-l-2 p-3 text-left transition-colors hover:border-tinta",
                        c.estado === "cancelada"
                          ? "border-l-linea opacity-50"
                          : c.tipo === "consulta"
                            ? "border-l-acento"
                            : "border-l-tinta-suave",
                      )}
                    >
                      <span className="cifra text-micro font-semibold text-tinta-media">
                        {hora(c.iniciaEn)}–{hora(c.terminaEn)}
                      </span>
                      <span
                        className={cn(
                          "text-menor font-medium",
                          c.estado === "cancelada" && "line-through",
                        )}
                      >
                        {c.titulo}
                      </span>
                      {nombreAlumna(c.alumnaUlid) ? (
                        <span className="text-micro text-tinta-suave">{nombreAlumna(c.alumnaUlid)}</span>
                      ) : null}
                      <span className="flex flex-wrap items-center gap-1.5 pt-0.5">
                        {c.tipo === "bloqueo" ? <Chip>Bloque</Chip> : null}
                        {c.estado === "confirmada" ? <Chip tono="exito">Confirmada</Chip> : null}
                        {c.estado === "cancelada" ? <Chip tono="error">Cancelada</Chip> : null}
                        {c.modalidad === "video" && c.estado !== "cancelada" ? (
                          <Video className="size-3 text-tinta-suave" />
                        ) : null}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>

      {citas.length === 0 ? <Vacio>Tu semana está libre.</Vacio> : null}

      {editando ? (
        <FormularioCita
          cita={editando}
          agenda={citas}
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
          onConfirmar={cancelar}
          onCerrar={() => setCancelando(null)}
        />
      ) : null}
    </div>
  );
}

/* ------------------------------------------------------------ Formulario --- */

function FormularioCita({
  cita,
  agenda,
  onGuardar,
  onCancelarCita,
  onEliminar,
  onCerrar,
}: {
  cita: Cita;
  agenda: Cita[];
  onGuardar: (c: Cita) => void;
  onCancelarCita: (c: Cita) => void;
  onEliminar: (id: string) => void;
  onCerrar: () => void;
}) {
  const [borrador, setBorrador] = useState<Cita>(cita);
  const esNueva = !cita.id;

  const cambiar = <K extends keyof Cita>(campo: K, valor: Cita[K]) =>
    setBorrador((b) => ({ ...b, [campo]: valor }));

  // Las mismas guardas que aplica el servidor, para avisar antes de enviar.
  const duracion = duracionMin(borrador);
  const choque = buscarChoque(borrador, agenda);

  const problema =
    !borrador.titulo.trim()
      ? "Ponle un título: es lo que ve la alumna en su recordatorio."
      : borrador.terminaEn <= borrador.iniciaEn
        ? "La hora de fin tiene que ser posterior a la de inicio."
        : duracion < DURACION_MINIMA_MIN
          ? `Muy corta. El mínimo son ${DURACION_MINIMA_MIN} minutos.`
          : duracion > DURACION_MAXIMA_MIN
            ? "Más de 8 horas: revisa que la fecha de fin sea la correcta."
            : borrador.tipo === "consulta" && !borrador.alumnaUlid
              ? "Una consulta necesita alumna. Si es tiempo tuyo, cámbialo a bloque de trabajo."
              : null;

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={esNueva ? "Nueva cita" : "Editar cita"}
      titulo={esNueva ? "Agendar" : borrador.titulo || "Sin título"}
      pie={
        <>
          {!esNueva && borrador.estado !== "cancelada" ? (
            <Boton tono="peligro" medida="chica" onClick={() => onCancelarCita(borrador)}>
              Cancelar cita
            </Boton>
          ) : null}
          {!esNueva ? (
            <Boton tono="discreto" medida="chica" onClick={() => onEliminar(borrador.id)}>
              Eliminar
            </Boton>
          ) : null}
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            Cerrar
          </Boton>
          <Boton medida="chica" disabled={problema !== null || choque !== undefined} onClick={() => onGuardar(borrador)}>
            {esNueva ? "Agendar" : "Guardar"}
          </Boton>
        </>
      }
    >
      <Campo id="cita-titulo" etiqueta="Título">
        <Entrada
          id="cita-titulo"
          value={borrador.titulo}
          onChange={(e) => cambiar("titulo", e.target.value)}
          placeholder="Consulta de seguimiento"
        />
      </Campo>

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="cita-tipo" etiqueta="Tipo">
          <Selector
            id="cita-tipo"
            value={borrador.tipo}
            onChange={(e) => {
              const tipo = e.target.value as TipoCita;
              setBorrador((b) => ({ ...b, tipo, alumnaUlid: tipo === "bloqueo" ? null : b.alumnaUlid }));
            }}
          >
            <option value="consulta">Consulta con alumna</option>
            <option value="bloqueo">Bloque de trabajo</option>
          </Selector>
        </Campo>

        <Campo id="cita-modalidad" etiqueta="Modalidad">
          <Selector
            id="cita-modalidad"
            value={borrador.modalidad}
            onChange={(e) => cambiar("modalidad", e.target.value as Modalidad)}
          >
            {(Object.keys(ROTULO_MODALIDAD) as Modalidad[]).map((m) => (
              <option key={m} value={m}>
                {ROTULO_MODALIDAD[m]}
              </option>
            ))}
          </Selector>
        </Campo>
      </div>

      {borrador.tipo === "consulta" ? (
        <Campo id="cita-alumna" etiqueta="Alumna">
          <Selector
            id="cita-alumna"
            value={borrador.alumnaUlid ?? ""}
            onChange={(e) => cambiar("alumnaUlid", e.target.value || null)}
          >
            <option value="">Elige una…</option>
            {cartera.map((a) => (
              <option key={a.ulid} value={a.ulid}>
                {a.nombre}
              </option>
            ))}
          </Selector>
        </Campo>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="cita-inicia" etiqueta="Empieza">
          <Entrada
            id="cita-inicia"
            type="datetime-local"
            value={borrador.iniciaEn}
            onChange={(e) => cambiar("iniciaEn", e.target.value)}
          />
        </Campo>
        <Campo
          id="cita-termina"
          etiqueta="Termina"
          ayuda={duracion > 0 ? `${duracion} minutos` : undefined}
        >
          <Entrada
            id="cita-termina"
            type="datetime-local"
            value={borrador.terminaEn}
            onChange={(e) => cambiar("terminaEn", e.target.value)}
          />
        </Campo>
      </div>

      <Campo id="cita-notas" etiqueta="Notas">
        <textarea
          id="cita-notas"
          value={borrador.notas}
          onChange={(e) => cambiar("notas", e.target.value)}
          rows={3}
          className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
          placeholder="Qué quieres cubrir en esta cita"
        />
      </Campo>

      {choque ? (
        <Aviso tono="error" titulo="Ya tienes algo a esa hora">
          «{choque.titulo}», de {hora(choque.iniciaEn)} a {hora(choque.terminaEn)}. Mueve una de las dos.
        </Aviso>
      ) : problema ? (
        <Aviso tono="atencion">{problema}</Aviso>
      ) : null}

      {borrador.estado === "cancelada" && borrador.motivoCancelacion ? (
        <Aviso tono="info" titulo="Cita cancelada">
          {borrador.motivoCancelacion}
        </Aviso>
      ) : null}
    </Dialogo>
  );
}

function FormularioCancelacion({
  cita,
  onConfirmar,
  onCerrar,
}: {
  cita: Cita;
  onConfirmar: (c: Cita, motivo: string) => void;
  onCerrar: () => void;
}) {
  const [motivo, setMotivo] = useState("");

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta="Cancelar cita"
      titulo={cita.titulo}
      descripcion={`${hora(cita.iniciaEn)}–${hora(cita.terminaEn)}`}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            Mejor no
          </Boton>
          <Boton
            tono="peligro"
            medida="chica"
            disabled={!motivo.trim()}
            onClick={() => onConfirmar(cita, motivo.trim())}
          >
            Cancelar y avisar
          </Boton>
        </>
      }
    >
      <Apoyo>
        {nombreAlumna(cita.alumnaUlid)
          ? `${nombreAlumna(cita.alumnaUlid)} recibirá un aviso con el motivo tal como lo escribas.`
          : "El bloque se libera y la hora vuelve a quedar disponible."}
      </Apoyo>

      <Campo id="motivo-cancelacion" etiqueta="Motivo">
        <textarea
          id="motivo-cancelacion"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          rows={3}
          className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
          placeholder="Se me empalmó una urgencia, te reagendo el jueves."
        />
      </Campo>
    </Dialogo>
  );
}
