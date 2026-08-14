/** Finanzas de la coach.
 *
 *  Contabilidad de gestión, no fiscal: responde «¿mi negocio gana dinero?», no sirve para
 *  declarar impuestos. Por eso no hay IVA desglosado ni folios.
 *
 *  Los ingresos que nacen de un pago validado llegan marcados como automáticos y **no se
 *  editan aquí**: corregirlos separaría el ingreso del cobro que lo originó.
 */

import { Lock, Plus } from "lucide-react";
import { useState } from "react";

import { Dialogo } from "@/componentes/Dialogo";
import { AvisoSinServidor, Cargando } from "@/componentes/Estado";
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
  type MovimientoApi,
  type MovimientoNuevoApi,
  type PanelFinancieroApi,
} from "@/lib/api";
import { fecha, pesos, porcentaje } from "@/lib/formato";
import { usarApiConRespaldo } from "@/lib/usarApi";
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

  if (cargando) return <Cargando que="tus finanzas" />;

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
          <ul className="flex flex-col divide-y divide-linea border-y border-linea">
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

  const montoNum = Number.parseFloat(monto);
  const problema = !concepto.trim()
    ? "Escribe un concepto: sin él el movimiento no se entiende dentro de tres meses."
    : !montoNum || montoNum <= 0
      ? "El monto tiene que ser mayor que cero."
      : null;

  // Al cambiar de tipo, la categoría anterior deja de ser válida.
  function cambiarTipo(nuevo: "ingreso" | "gasto") {
    setTipo(nuevo);
    setCategoria(CATEGORIAS[nuevo][0]![0]);
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
      alumnaUlid: null,
      nota: nota.trim() || null,
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
          placeholder="Suscripción de MyProgressPlan · agosto"
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
