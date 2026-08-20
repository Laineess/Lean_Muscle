/** Finanzas de la coach: contabilidad de gestión, no fiscal.
 *
 *  Responde «¿mi negocio gana dinero?», y por eso no hay IVA desglosado ni folios. Los
 *  ingresos que nacen de un pago validado llegan marcados y no se editan aquí.
 */

import { Lock, Plus } from "lucide-react";
import { useState } from "react";

import { Comprobantes } from "@/coach/Comprobantes";
import { Dialogo } from "@/componentes/Dialogo";
import { AvisoSinServidor, CargandoPantalla } from "@/componentes/Estado";
import { Grafica } from "@/componentes/Grafica";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Chip,
  Dato,
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
  type AlumnaConCobrosApi,
  type CobroApi2,
  type MovimientoApi,
  type MovimientoNuevoApi,
  type PanelFinancieroApi,
} from "@/lib/api";
import { fecha, num, pesos, porcentaje } from "@/lib/formato";
import { usarApi, usarApiConRespaldo } from "@/lib/usarApi";
import { cn } from "@/lib/utils";

const CATEGORIAS = {
  ingreso: [
    ["ciclo", "Ciclo mensual"],
    ["consulta", "Consulta suelta"],
    ["otro_ingreso", "Otro ingreso"],
  ],
  gasto: [
    ["plataforma", "Plataforma"],
    ["equipo", "Equipo"],
    ["local", "Local"],
    ["formacion", "Formación"],
    ["publicidad", "Publicidad"],
    ["impuestos", "Impuestos"],
    ["otro_gasto", "Otro gasto"],
  ],
} as const;

const ROTULO_CATEGORIA: Record<string, string> = Object.fromEntries(
  [...CATEGORIAS.ingreso, ...CATEGORIAS.gasto].map(([id, rotulo]) => [id, rotulo]),
);

const VACIO: PanelFinancieroApi = {
  ingresos: 0,
  gastos: 0,
  utilidad: 0,
  margen: 0,
  ingresoPorAlumna: 0,
  proyeccionMensual: 0,
  alumnasActivas: 0,
  porMes: [],
  ingresosPorCategoria: [],
  gastosPorCategoria: [],
  movimientos: [],
};

export function Finanzas() {
  const [meses, setMeses] = useState(12);
  const [editando, setEditando] = useState<MovimientoApi | "nuevo" | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);

  const { datos, cargando, sinServidor, mensaje, recargar } = usarApiConRespaldo<PanelFinancieroApi>(
    (senal) => api.coach.finanzas(meses, senal),
    VACIO,
    [meses],
  );

  if (cargando) return <CargandoPantalla que="tus finanzas" cifras={4} filas={4} />;

  async function eliminar(m: MovimientoApi) {
    setFallo(null);
    try {
      await api.coach.eliminarMovimiento(m.ulid);
      recargar();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo eliminar.");
    }
  }

  const enPerdida = datos.utilidad < 0;

  return (
    <div className="flex flex-col gap-10">
      {sinServidor ? <AvisoSinServidor mensaje={mensaje} /> : null}
      {fallo ? <Aviso tono="error">{fallo}</Aviso> : null}

      {/* Antes que las cifras: un comprobante sin revisar es dinero que todavía no cuenta. */}
      <Comprobantes onCambio={recargar} />

      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-3">
          <Etiqueta>Últimos {meses} meses</Etiqueta>
          <Portada>Finanzas</Portada>
        </div>
        <div className="flex items-center gap-2">
          <Selector
            value={meses}
            onChange={(e) => setMeses(Number(e.target.value))}
            className="w-auto"
            aria-label="Periodo"
          >
            <option value={3}>3 meses</option>
            <option value={6}>6 meses</option>
            <option value={12}>12 meses</option>
            <option value={24}>24 meses</option>
          </Selector>
          <Boton onClick={() => setEditando("nuevo")}>
            <Plus className="size-4" /> Movimiento
          </Boton>
        </div>
      </header>

      {/* ---- Cifras ---- */}
      <section className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-4">
        <Dato rotulo="Ingresos" valor={pesos(datos.ingresos)} />
        <Dato rotulo="Gastos" valor={pesos(datos.gastos)} />
        <Dato
          rotulo="Utilidad"
          valor={pesos(datos.utilidad)}
          nota={`margen ${porcentaje(datos.margen)}`}
          direccion={enPerdida ? "sube" : "baja"}
        />
        <Dato
          rotulo="Por alumna"
          valor={pesos(datos.ingresoPorAlumna)}
          nota={`${datos.alumnasActivas} activas`}
        />
      </section>

      {enPerdida ? (
        <Aviso tono="error" titulo="El periodo cierra en pérdida">
          Gastaste {pesos(datos.gastos - datos.ingresos)} más de lo que ingresaste.
        </Aviso>
      ) : null}

      <Aviso tono="info" titulo={`Proyección: ${pesos(datos.proyeccionMensual)} al mes`}>
        Es lo que entraría si tus {datos.alumnasActivas} alumnas activas renovaran. **Es una
        proyección, no un dato**: no la cuentes como ingreso hasta que esté cobrada.
      </Aviso>

      <Regla />

      {/* ---- Evolución ---- */}
      {datos.porMes.length > 1 ? (
        <section className="flex flex-col gap-6">
          <Titulo>Mes a mes</Titulo>
          <div className="grid gap-10 sm:grid-cols-2">
            <article className="flex flex-col gap-2">
              <Etiqueta>Ingresos</Etiqueta>
              <Grafica
                puntos={datos.porMes.map((m) => ({ etiqueta: m.mes.slice(5), valor: m.ingresos }))}
                decimales={0}
              />
            </article>
            <article className="flex flex-col gap-2">
              <Etiqueta>Utilidad</Etiqueta>
              <Grafica
                puntos={datos.porMes.map((m) => ({ etiqueta: m.mes.slice(5), valor: m.utilidad }))}
                decimales={0}
              />
            </article>
          </div>
        </section>
      ) : null}

      {/* ---- Categorías ---- */}
      <section className="grid gap-8 sm:grid-cols-2">
        {(
          [
            ["En qué entra el dinero", datos.ingresosPorCategoria, datos.ingresos],
            ["En qué se va", datos.gastosPorCategoria, datos.gastos],
          ] as const
        ).map(([titulo, categorias, total]) => (
          <article key={titulo} className="flex flex-col gap-3">
            <Titulo>{titulo}</Titulo>
            {categorias.length === 0 ? (
              <Apoyo>Sin movimientos en el periodo.</Apoyo>
            ) : (
              <ul className="flex flex-col gap-2">
                {categorias.map((c) => (
                  <li key={c.categoria} className="flex flex-col gap-1">
                    <div className="flex items-baseline justify-between gap-3 text-menor">
                      <span>{ROTULO_CATEGORIA[c.categoria] ?? c.categoria}</span>
                      <span className="cifra font-semibold">{pesos(c.monto)}</span>
                    </div>
                    {/* Barra proporcional: leer 8 cifras cuesta más que ver 8 barras. */}
                    <div className="h-1 rounded-full bg-fondo-sutil">
                      <div
                        className="h-full rounded-full bg-tinta"
                        style={{ width: `${total ? (c.monto / total) * 100 : 0}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </article>
        ))}
      </section>

      <Regla />

      {/* ---- Movimientos ---- */}
      <section className="flex flex-col gap-4">
        <Titulo>Movimientos</Titulo>

        {datos.movimientos.length === 0 ? (
          <Vacio>Todavía no hay movimientos en este periodo.</Vacio>
        ) : (
          <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
            {datos.movimientos.map((m) => (
              <li key={m.ulid} className="flex flex-wrap items-center gap-4 py-3">
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-cuerpo">{m.concepto}</span>
                    {m.automatico ? (
                      <Chip>
                        <Lock className="size-3" /> De un pago
                      </Chip>
                    ) : null}
                  </div>
                  <Apoyo>
                    {fecha(m.fecha, { day: "numeric", month: "short", year: "numeric" })} ·{" "}
                    {ROTULO_CATEGORIA[m.categoria] ?? m.categoria}
                    {m.alumnaNombre ? ` · ${m.alumnaNombre}` : ""}
                  </Apoyo>
                </div>

                <span
                  className={cn(
                    "cifra shrink-0 font-semibold",
                    m.tipo === "gasto" && "text-tinta-media",
                  )}
                >
                  {m.tipo === "ingreso" ? "+" : "−"}
                  {pesos(m.monto)}
                </span>

                <div className="flex shrink-0 gap-1">
                  <Boton
                    tono="discreto"
                    medida="chica"
                    disabled={m.automatico}
                    title={m.automatico ? "Corrígelo en el pago que lo originó" : undefined}
                    onClick={() => setEditando(m)}
                  >
                    Editar
                  </Boton>
                  <Boton
                    tono="discreto"
                    medida="chica"
                    disabled={m.automatico}
                    onClick={() => void eliminar(m)}
                  >
                    Borrar
                  </Boton>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {editando ? (
        <FormMovimiento
          movimiento={editando === "nuevo" ? null : editando}
          onCerrar={() => setEditando(null)}
          onGuardado={recargar}
        />
      ) : null}
    </div>
  );
}

/** Buscador de alumna con sus cobros pendientes: es donde se concilia el dinero, y ese
 *  gesto único es lo que mantiene cuadrado el adeudo con lo registrado.
 */
function BuscadorDeCobro({
  alumna,
  cobro,
  onAlumna,
  onCobro,
}: {
  alumna: AlumnaConCobrosApi | null;
  cobro: CobroApi2 | null;
  onAlumna: (a: AlumnaConCobrosApi | null) => void;
  onCobro: (c: CobroApi2) => void;
}) {
  const [texto, setTexto] = useState("");
  const carga = usarApi<AlumnaConCobrosApi[]>(
    (senal) => api.coach.aQuienCobrar(texto, senal),
    [texto],
  );

  if (alumna) {
    return (
      <div className="flex flex-col gap-3 rounded-marco border border-linea p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-menor font-medium">{alumna.nombre}</span>
          <Boton tono="discreto" medida="chica" onClick={() => onAlumna(null)}>
            Cambiar
          </Boton>
        </div>
        <Etiqueta>Qué le cobras</Etiqueta>
        <ul className="flex flex-col gap-1">
          {alumna.pendientes.map((c) => (
            <li key={c.ulid}>
              <button
                type="button"
                onClick={() => onCobro(c)}
                className={cn(
                  "flex w-full items-center justify-between gap-3 rounded-marco border px-3 py-2 text-left text-menor transition-colors",
                  cobro?.ulid === c.ulid
                    ? "border-tinta bg-fondo-sutil"
                    : "border-linea hover:border-tinta",
                )}
              >
                <span className="flex min-w-0 flex-col">
                  <span className="truncate">{c.concepto}</span>
                  <span className="text-micro text-tinta-suave">
                    {fecha(c.fecha)}
                    {c.vencido ? " · vencido" : ""}
                  </span>
                </span>
                <span className="cifra font-semibold">${num(c.monto)}</span>
              </button>
            </li>
          ))}
        </ul>
        <Apoyo>Al registrarlo, ese cobro queda saldado y deja de contar como adeudo.</Apoyo>
      </div>
    );
  }

  const encontradas = carga.datos ?? [];

  return (
    <div className="flex flex-col gap-2">
      <Campo id="mv-alumna" etiqueta="¿De quién es el ingreso?">
        <Entrada
          id="mv-alumna"
          type="search"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Escribe un nombre…"
          autoComplete="off"
        />
      </Campo>

      {encontradas.length === 0 ? (
        <Apoyo>
          {carga.cargando ? "Buscando…" : "Nadie con cobros pendientes. Puedes registrarlo sin alumna."}
        </Apoyo>
      ) : (
        <ul className="flex max-h-48 flex-col gap-1 overflow-y-auto">
          {encontradas.map((a) => (
            <li key={a.ulid}>
              <button
                type="button"
                onClick={() => onAlumna(a)}
                className="flex w-full items-center justify-between gap-3 rounded-marco border border-linea px-3 py-2 text-left text-menor transition-colors hover:border-tinta"
              >
                <span className="flex min-w-0 flex-col">
                  <span className="truncate font-medium">{a.nombre}</span>
                  <span className="text-micro text-tinta-suave">
                    {a.plan ?? "sin plan"} · {a.pendientes.length} pendiente
                    {a.pendientes.length === 1 ? "" : "s"}
                  </span>
                </span>
                {a.adeudo > 0 ? <Chip tono="error">debe ${num(a.adeudo)}</Chip> : null}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function FormMovimiento({
  movimiento,
  onCerrar,
  onGuardado,
}: {
  movimiento: MovimientoApi | null;
  onCerrar: () => void;
  onGuardado: () => void;
}) {
  const hoy = new Date().toISOString().slice(0, 10);
  const [tipo, setTipo] = useState<"ingreso" | "gasto">(movimiento?.tipo ?? "gasto");
  const [categoria, setCategoria] = useState(movimiento?.categoria ?? "plataforma");
  const [monto, setMonto] = useState(movimiento ? String(movimiento.monto) : "");
  const [f, setF] = useState(movimiento?.fecha ?? hoy);
  const [concepto, setConcepto] = useState(movimiento?.concepto ?? "");
  const [nota, setNota] = useState(movimiento?.nota ?? "");
  const [error, setError] = useState<string | null>(null);

  // A quién se le cobra y qué cobro salda. Solo tiene sentido en un ingreso.
  const [alumna, setAlumna] = useState<AlumnaConCobrosApi | null>(null);
  const [cobro, setCobro] = useState<CobroApi2 | null>(null);

  const montoNum = Number.parseFloat(monto);
  const problema = !concepto.trim()
    ? "Escribe un concepto: sin él el movimiento no se entiende dentro de tres meses."
    : !montoNum || montoNum <= 0
      ? "El monto tiene que ser mayor que cero."
      : null;

  // Al cambiar de tipo, la categoría anterior deja de ser válida.
  function cambiarTipo(nuevo: "ingreso" | "gasto") {
    setTipo(nuevo);
    setCategoria(CATEGORIAS[nuevo][0][0]);
    if (nuevo === "gasto") {
      setAlumna(null);
      setCobro(null);
    }
  }

  /** Al elegir un cobro se llenan monto y concepto: teclearlos otra vez es como se acaba
   *  registrando un importe que no cuadra.
   */
  function tomarCobro(c: CobroApi2) {
    setCobro(c);
    setMonto(String(c.monto));
    setConcepto(c.concepto);
    setCategoria(c.motivo === "cita" ? "consulta" : "ciclo");
    setF(hoy);
  }

  async function guardar() {
    if (problema) {
      setError(problema);
      return;
    }
    setError(null);
    const cuerpo: MovimientoNuevoApi = {
      tipo,
      categoria,
      monto: montoNum,
      fecha: f,
      concepto: concepto.trim(),
      alumnaUlid: alumna?.ulid ?? null,
      nota: nota.trim() || null,
      cobroUlid: cobro?.ulid ?? null,
    };
    try {
      if (movimiento) await api.coach.editarMovimiento(movimiento.ulid, cuerpo);
      else await api.coach.crearMovimiento(cuerpo);
      onGuardado();
      onCerrar();
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo guardar.");
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={movimiento ? "Editar movimiento" : "Nuevo movimiento"}
      titulo={tipo === "ingreso" ? "Ingreso" : "Gasto"}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton medida="chica" onClick={() => void guardar()}>
            Guardar
          </Boton>
        </>
      }
    >
      {/* Al editar solo se enseña: el servidor no cambia el enlace, y un selector que no
          hace nada es peor que ninguno. */}
      {movimiento ? (
        movimiento.alumnaNombre ? (
          <Apoyo>
            Ingreso de <strong>{movimiento.alumnaNombre}</strong>. Para ligarlo a otra alumna,
            cancélalo y regístralo de nuevo.
          </Apoyo>
        ) : null
      ) : tipo === "ingreso" ? (
        /* El buscador va primero: elegir a quién se le cobra llena el resto del formulario. */
        <BuscadorDeCobro
          alumna={alumna}
          cobro={cobro}
          onAlumna={(a) => {
            setAlumna(a);
            setCobro(null);
          }}
          onCobro={tomarCobro}
        />
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="m-tipo" etiqueta="Tipo">
          <Selector
            id="m-tipo"
            value={tipo}
            onChange={(e) => cambiarTipo(e.target.value as "ingreso" | "gasto")}
          >
            <option value="gasto">Gasto</option>
            <option value="ingreso">Ingreso</option>
          </Selector>
        </Campo>
        <Campo id="m-categoria" etiqueta="Categoría">
          <Selector id="m-categoria" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
            {CATEGORIAS[tipo].map(([id, rotulo]) => (
              <option key={id} value={id}>
                {rotulo}
              </option>
            ))}
          </Selector>
        </Campo>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="m-monto" etiqueta="Monto" sufijo="MXN">
          <Entrada
            id="m-monto"
            type="number"
            step="0.01"
            min={0}
            value={monto}
            onChange={(e) => setMonto(e.target.value)}
            className="rounded-r-none"
          />
        </Campo>
        <Campo id="m-fecha" etiqueta="Fecha">
          <Entrada id="m-fecha" type="date" value={f} onChange={(e) => setF(e.target.value)} />
        </Campo>
      </div>

      <Campo
        id="m-concepto"
        etiqueta="Concepto"
        ayuda="Escríbelo para tu yo de dentro de tres meses."
      >
        <Entrada
          id="m-concepto"
          value={concepto}
          onChange={(e) => setConcepto(e.target.value)}
          placeholder="Suscripción de MyFittPlan · agosto"
        />
      </Campo>

      <Campo id="m-nota" etiqueta="Nota (opcional)">
        <Entrada id="m-nota" value={nota} onChange={(e) => setNota(e.target.value)} />
      </Campo>

      {error ? <Aviso tono="error">{error}</Aviso> : problema ? <Aviso tono="atencion">{problema}</Aviso> : null}

      <Apoyo>
        Esto es contabilidad de gestión, para saber si tu negocio gana dinero. No sustituye tu
        contabilidad fiscal: pídele a tu contador lo que necesite.
      </Apoyo>
    </Dialogo>
  );
}
