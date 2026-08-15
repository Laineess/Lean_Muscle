/** Calendario de cobros de una alumna.
 *
 *  Tocar un día abre el formulario para programar qué se le cobra y cuánto. Es la única
 *  manera de generar un adeudo, y un adeudo vencido pausa el plan de la alumna: por eso el
 *  calendario vive en su expediente y no en finanzas, donde se registra lo ya cobrado.
 */

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";

import { Dialogo } from "@/componentes/Dialogo";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Chip,
  Entrada,
  Etiqueta,
  Selector,
  Titulo,
} from "@/componentes/primitivas";
import {
  ErrorApi,
  api,
  type CitaDeAlumnaApi,
  type CobroApi2,
  type MotivoDeCobro,
  type ServicioApi,
} from "@/lib/api";
import { fecha, num } from "@/lib/formato";
import { usarApi } from "@/lib/usarApi";
import { cn } from "@/lib/utils";

const MOTIVOS: [MotivoDeCobro, string][] = [
  ["mensualidad", "Mensualidad del plan"],
  ["inscripcion", "Inscripción"],
  ["cita", "Consulta"],
  ["material", "Material"],
  ["otro", "Otro concepto"],
];

const p2 = (n: number) => String(n).padStart(2, "0");
const claveDe = (d: Date) => `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`;

export function CalendarioDeCobros({
  alumnaUlid,
  precioSugerido,
  nombreDelPlan = null,
}: {
  alumnaUlid: string;
  /** El precio de su plan. Es el monto que se propone al programar una mensualidad. */
  precioSugerido: number | null;
  /** Su nombre, para explicar de dónde salió el importe. */
  nombreDelPlan?: string | null;
}) {
  const carga = usarApi<CobroApi2[]>((senal) => api.coach.cobros(alumnaUlid, senal), [alumnaUlid]);
  // Las consultas que su coach le agendó. Es la misma cita que sale en la agenda, vista
  // desde su expediente: sin esto, la coach tendría que recordar de memoria qué agendó.
  const citas = usarApi<CitaDeAlumnaApi[]>(
    (senal) => api.coach.citasDeAlumna(alumnaUlid, senal),
    [alumnaUlid],
  );
  const [ancla, setAncla] = useState(() => new Date());
  const [dia, setDia] = useState<string | null>(null);

  const cobros = carga.datos ?? [];
  const hoy = claveDe(new Date());

  const primero = new Date(ancla.getFullYear(), ancla.getMonth(), 1);
  const desplazamiento = (primero.getDay() + 6) % 7; // la semana empieza en lunes
  const celdas = Array.from({ length: 42 }, (_, i) => {
    const d = new Date(primero);
    d.setDate(1 - desplazamiento + i);
    return { clave: claveDe(d), numero: d.getDate(), delMes: d.getMonth() === ancla.getMonth() };
  });

  const porDia = new Map<string, CobroApi2[]>();
  for (const c of cobros) porDia.set(c.fecha, [...(porDia.get(c.fecha) ?? []), c]);

  const consultas = new Map<string, CitaDeAlumnaApi>();
  for (const c of citas.datos ?? []) {
    if (c.estado !== "cancelada") consultas.set(c.iniciaEn.slice(0, 10), c);
  }
  const proximasConsultas = [...consultas.values()].slice(-4);

  const adeudo = cobros.filter((c) => c.vencido).reduce((s, c) => s + c.monto, 0);

  function mover(d: -1 | 1) {
    const nuevo = new Date(ancla);
    nuevo.setMonth(nuevo.getMonth() + d);
    setAncla(nuevo);
  }

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <Titulo>Cobros</Titulo>
        {adeudo > 0 ? <Chip tono="error">debe ${num(adeudo)}</Chip> : null}
      </div>
      <Apoyo>
        Toca un día para programar un cobro. Uno vencido le pausa el plan. El cuadrito marca
        una consulta agendada.
      </Apoyo>

      <div className="flex items-center justify-between gap-2">
        <Boton tono="discreto" medida="icono" onClick={() => mover(-1)} aria-label="Mes anterior">
          <ChevronLeft className="size-4" />
        </Boton>
        <span className="text-menor font-medium first-letter:uppercase">
          {ancla.toLocaleDateString("es-MX", { month: "long", year: "numeric" })}
        </span>
        <Boton tono="discreto" medida="icono" onClick={() => mover(1)} aria-label="Mes siguiente">
          <ChevronRight className="size-4" />
        </Boton>
      </div>

      <div className="overflow-hidden rounded-marco border border-linea">
        <div className="grid grid-cols-7 border-b border-linea">
          {["L", "M", "X", "J", "V", "S", "D"].map((d, i) => (
            <div key={i} className="py-1 text-center text-micro text-tinta-suave">
              {d}
            </div>
          ))}
        </div>
        <div className="grid grid-cols-7">
          {celdas.map((celda) => {
            const delDia = porDia.get(celda.clave) ?? [];
            const hayVencido = delDia.some((c) => c.vencido);
            const hayPagado = delDia.some((c) => c.estado === "pagado");
            const consulta = consultas.get(celda.clave);
            return (
              <button
                key={celda.clave}
                type="button"
                onClick={() => setDia(celda.clave)}
                className={cn(
                  "flex min-h-11 flex-col items-center justify-center gap-0.5 border-t border-l border-linea transition-colors hover:bg-fondo-sutil",
                  !celda.delMes && "text-tinta-suave",
                  celda.clave === hoy && "font-semibold",
                )}
              >
                <span className="cifra text-micro">{celda.numero}</span>
                <span className="flex items-center gap-0.5">
                  {delDia.length > 0 ? (
                    <span
                      className={cn(
                        "size-1.5 rounded-full",
                        hayVencido ? "bg-peligro" : hayPagado ? "bg-exito" : "bg-acento",
                      )}
                    />
                  ) : null}
                  {/* La consulta va con otra forma, no otro color: el color ya significa
                      el estado del cobro y dos escalas en el mismo punto no se leen. */}
                  {consulta ? <span className="size-1.5 rounded-[1px] bg-tinta-media" /> : null}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {proximasConsultas.length > 0 ? (
        <div className="flex flex-col gap-2">
          <Etiqueta>Consultas agendadas</Etiqueta>
          <ul className="flex flex-col divide-y divide-linea border-y border-linea">
            {proximasConsultas.map((c) => (
              <li key={c.ulid} className="flex items-baseline justify-between gap-2 py-2">
                <span className="text-micro">{c.titulo}</span>
                <span className="cifra text-micro text-tinta-media">
                  {fecha(c.iniciaEn.slice(0, 10))} · {c.iniciaEn.slice(11, 16)}
                </span>
              </li>
            ))}
          </ul>
          <Apoyo>
            Su chequeo se abre tres días antes de cada una y se cierra tres después.
          </Apoyo>
        </div>
      ) : (
        <Apoyo>
          Sin consultas agendadas. Hasta que le agendes una desde tu agenda, no puede
          capturar su chequeo.
        </Apoyo>
      )}

      {cobros.length > 0 ? (
        <ul className="flex flex-col divide-y divide-linea border-y border-linea">
          {cobros.slice(-4).map((c) => (
            <li key={c.ulid} className="flex items-baseline justify-between gap-2 py-2">
              <span className="flex min-w-0 flex-col">
                <span className="truncate text-micro">{c.concepto}</span>
                <span className="text-micro text-tinta-suave">{fecha(c.fecha)}</span>
              </span>
              <span className="flex items-baseline gap-2">
                <span className="cifra text-micro font-semibold">${num(c.monto)}</span>
                {c.estado === "pagado" ? (
                  <Chip tono="exito">pagado</Chip>
                ) : c.vencido ? (
                  <Chip tono="error">vencido</Chip>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      {dia ? (
        <FormularioDeCobro
          alumnaUlid={alumnaUlid}
          dia={dia}
          existentes={porDia.get(dia) ?? []}
          precioSugerido={precioSugerido}
          nombreDelPlan={nombreDelPlan}
          onCerrar={() => setDia(null)}
          onCambio={() => {
            setDia(null);
            carga.recargar();
          }}
        />
      ) : null}
    </section>
  );
}

function FormularioDeCobro({
  alumnaUlid,
  dia,
  existentes,
  precioSugerido,
  nombreDelPlan,
  onCerrar,
  onCambio,
}: {
  alumnaUlid: string;
  dia: string;
  existentes: CobroApi2[];
  precioSugerido: number | null;
  nombreDelPlan: string | null;
  onCerrar: () => void;
  onCambio: () => void;
}) {
  const [motivo, setMotivo] = useState<MotivoDeCobro>("mensualidad");
  const [monto, setMonto] = useState(precioSugerido ?? 0);
  const [concepto, setConcepto] = useState("");
  const servicios = usarApi<ServicioApi[]>((s) => api.coach.servicios(s));
  const delMotivo = (servicios.datos ?? []).filter((x) => x.activo && x.motivo === motivo);

  /** El precio que corresponde solo, si no hay ambigüedad.
   *
   *  La mensualidad sale del plan que contrató la alumna. Los demás motivos, de su lista de
   *  precios, y únicamente cuando hay uno: con dos o más hay que elegir, y con ninguno se
   *  teclea a mano. Es lo que evita preguntar cuando la respuesta es una sola.
   */
  const unico =
    motivo === "mensualidad"
      ? precioSugerido !== null
        ? { precio: precioSugerido, nombre: nombreDelPlan ?? "" }
        : null
      : delMotivo.length === 1
        ? { precio: delMotivo[0]!.precio, nombre: delMotivo[0]!.nombre }
        : null;

  // Se aplica al cambiar de motivo, no en cada render: si no, la coach no podría corregir
  // el importe sin que se le revirtiera al instante.
  useEffect(() => {
    if (!unico) return;
    setMonto(unico.precio);
    setConcepto(unico.nombre);
    // El efecto depende solo del motivo a propósito: es el gesto que dispara el relleno.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [motivo, servicios.datos, precioSugerido]);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function programar() {
    setError(null);
    setEnviando(true);
    try {
      await api.coach.programarCobro(alumnaUlid, {
        fecha: dia,
        motivo,
        concepto: concepto.trim() || null,
        monto,
        nota: null,
      });
      onCambio();
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo programar el cobro.");
    } finally {
      setEnviando(false);
    }
  }

  async function cancelar(ulid: string) {
    setError(null);
    try {
      await api.coach.cancelarCobro(ulid);
      onCambio();
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo cancelar.");
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta="Programar cobro"
      titulo={fecha(dia)}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            Cerrar
          </Boton>
          <Boton medida="chica" disabled={enviando || monto <= 0} onClick={() => void programar()}>
            Programar
          </Boton>
        </>
      }
    >
      {existentes.length > 0 ? (
        <div className="flex flex-col gap-2">
          <Etiqueta>Ya programado ese día</Etiqueta>
          <ul className="flex flex-col divide-y divide-linea border-y border-linea">
            {existentes.map((c) => (
              <li key={c.ulid} className="flex items-center justify-between gap-3 py-2">
                <span className="text-menor">{c.concepto}</span>
                <span className="flex items-center gap-3">
                  <span className="cifra font-semibold">${num(c.monto)}</span>
                  {c.estado === "pagado" ? (
                    <Chip tono="exito">pagado</Chip>
                  ) : (
                    <Boton tono="discreto" medida="chica" onClick={() => void cancelar(c.ulid)}>
                      Quitar
                    </Boton>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <Campo id="cb-motivo" etiqueta="Motivo">
        <Selector
          id="cb-motivo"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value as MotivoDeCobro)}
        >
          {MOTIVOS.map(([valor, rotulo]) => (
            <option key={valor} value={valor}>
              {rotulo}
            </option>
          ))}
        </Selector>
      </Campo>

      {delMotivo.length > 1 ? (
        <Campo
          id="cb-servicio"
          etiqueta="De tu lista de precios"
          ayuda="Al elegir uno se llenan el importe y el concepto. Puedes cambiarlos después."
        >
          <Selector
            id="cb-servicio"
            value=""
            onChange={(e) => {
              const elegido = delMotivo.find((x) => x.ulid === e.target.value);
              if (!elegido) return;
              setMonto(elegido.precio);
              setConcepto(elegido.nombre);
            }}
          >
            <option value="">Elige uno…</option>
            {delMotivo.map((x) => (
              <option key={x.ulid} value={x.ulid}>
                {x.nombre} · ${num(x.precio)}
              </option>
            ))}
          </Selector>
        </Campo>
      ) : unico ? (
        <Apoyo>
          Importe tomado de {motivo === "mensualidad" ? "su plan" : "tu lista de precios"}:{" "}
          <strong className="font-semibold">{unico.nombre}</strong>. Cámbialo si esta vez es
          distinto.
        </Apoyo>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="cb-monto" etiqueta="Monto" sufijo="MXN">
          <Entrada
            id="cb-monto"
            type="number"
            min={1}
            value={monto}
            onChange={(e) => setMonto(Number(e.target.value))}
            className="rounded-r-none"
          />
        </Campo>
        <Campo
          id="cb-concepto"
          etiqueta="Concepto (opcional)"
          ayuda="Si lo dejas vacío se usa el motivo."
        >
          <Entrada
            id="cb-concepto"
            value={concepto}
            onChange={(e) => setConcepto(e.target.value)}
            placeholder="Mensualidad de septiembre"
          />
        </Campo>
      </div>

      <Apoyo>
        La alumna lo ve en sus próximas fechas. Si llega el día y no ha pagado, su plan se
        pausa hasta que registres el ingreso.
      </Apoyo>

      {error ? <Aviso tono="error">{error}</Aviso> : null}
    </Dialogo>
  );
}
