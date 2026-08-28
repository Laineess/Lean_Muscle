/** La calculadora con la forma de la hoja de cálculo original.
 *
 *  Mismos bloques, mismas etiquetas y la celda de la que sale cada número: la coach lleva
 *  años con ese archivo y así comprueba que calculamos lo que ella calculaba.
 *
 *  Los valores llegan calculados del servidor; aquí no se hace ni una cuenta.
 */

import { Calculator } from "lucide-react";
import { useState } from "react";

import { Aviso, Boton, Chip, Etiqueta, Titulo, Vacio } from "@/componentes/primitivas";
import {
  api,
  type BloqueDeHojaApi,
  type HojaDeCalculoApi,
  type TablaDeHojaApi,
  type TramoDeImcApi,
} from "@/lib/api";
import { usarApi } from "@/lib/usarApi";
import { cn } from "@/lib/utils";
import { useIdioma } from "@/lib/idioma";

const TABLAS_OCULTAS = new Set([
  "Base del cálculo de proteína",
  "Proyección de aumento de músculo",
  "Ecuación de la tasa metabólica basal",
  "Constantes",
]);

export function Hoja({
  alumnaUlid,
  soloTablas = false,
}: {
  alumnaUlid: string;
  soloTablas?: boolean;
}) {
  const { t } = useIdioma();
  const carga = usarApi<HojaDeCalculoApi>((s) => api.coach.hoja(alumnaUlid, s), [alumnaUlid]);
  const [formulas, setFormulas] = useState(false);
  const [tablas, setTablas] = useState(false);

  if (carga.cargando) return <Vacio>{t("Calculando…")}</Vacio>;
  const d = carga.datos;
  if (!d) {
    return <Aviso tono="error">{t("No se pudo abrir la calculadora.")}</Aviso>;
  }
  if (d.falta) {
    return (
      <section className="flex flex-col gap-3">
        <Titulo icono={Calculator}>{t("Calculadora")}</Titulo>
        <Aviso tono="atencion" titulo={t("Todavía no hay con qué calcular")}>
          {d.falta}
        </Aviso>
      </section>
    );
  }

  if (soloTablas) return <TablasHoja datos={d} />;

  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <Titulo icono={Calculator}>{t("Calculadora")}</Titulo>
        </div>
        <div className="flex flex-wrap gap-2">
          <Boton tono="contorno" medida="chica" onClick={() => setFormulas((v) => !v)}>
            {formulas ? t("Ocultar fórmulas") : t("Ver fórmulas")}
          </Boton>
          <Boton tono="contorno" medida="chica" onClick={() => setTablas((v) => !v)}>
            {tablas ? t("Ocultar tablas") : t("Ver tablas")}
          </Boton>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {d.bloques.map((b) => (
          <BloqueHoja key={b.rango} b={b} formulas={formulas} />
        ))}
      </div>

      {tablas ? <TablasHoja datos={d} /> : null}
    </section>
  );
}

function TablasHoja({ datos }: { datos: HojaDeCalculoApi }) {
  return (
    <div className="flex flex-col gap-8 entra">
      {datos.escalaImc.length > 0 ? <EscalaDeImc tramos={datos.escalaImc} /> : null}
      <div className="grid gap-8 lg:grid-cols-2">
        {datos.tablas.filter((tabla) => !TABLAS_OCULTAS.has(tabla.titulo)).map((tabla) => (
          <TablaDeConsulta key={tabla.titulo} tabla={tabla} />
        ))}
      </div>
    </div>
  );
}

function BloqueHoja({ b, formulas }: { b: BloqueDeHojaApi; formulas: boolean }) {
  const { t } = useIdioma();
  return (
    <article className="flex flex-col gap-2 rounded-marco border border-linea p-4">
      <div className="flex items-baseline justify-between gap-2">
        <Etiqueta>{t(b.titulo)}</Etiqueta>
        <span className="cifra text-micro text-tinta-suave">{b.rango}</span>
      </div>
      <ul className="flex flex-col divide-y divide-linea/60">
        {b.celdas.map((c) => (
          <li key={c.celda} className="flex flex-col gap-0.5 py-2">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span
                className={cn(
                  "cifra w-11 shrink-0 text-micro",
                  // Lo capturado se distingue de lo calculado: es la diferencia entre un
                  // número que ella escribió y uno del que responde la fórmula.
                  c.capturado ? "font-semibold text-acento-texto" : "text-tinta-suave",
                )}
              >
                {c.celda}
              </span>
              <span className="min-w-0 flex-1 text-menor">{t(c.rotulo)}</span>
              <span className="cifra text-menor font-semibold">{t(c.valor)}</span>
              {c.unidad ? (
                <span className="w-12 text-micro text-tinta-suave">{t(c.unidad)}</span>
              ) : (
                <span className="w-12" />
              )}
            </div>
            {formulas && c.formula ? (
              <code className="ml-14 text-micro text-tinta-suave">{c.formula}</code>
            ) : null}
          </li>
        ))}
      </ul>
      <Chip className="w-fit">
        {b.celdas.filter((c) => c.capturado).length} {t("capturados")} ·{" "}
        {b.celdas.filter((c) => !c.capturado).length} {t("calculados")}
      </Chip>
    </article>
  );
}


/* ------------------------------------------------ Tablas de consulta --- */

/** La escala de índice de masa corporal, por tramos.
 *
 *  Agrupada y no fila por fila: son veinte valores y diecisiete de ellos repiten la
 *  clasificación de arriba. Los números siguen todos, el nombre no.
 */
function EscalaDeImc({ tramos }: { tramos: TramoDeImcApi[] }) {
  const { t } = useIdioma();
  return (
    <section className="flex flex-col gap-3">
      <Etiqueta>{t("Clasificación por índice de masa corporal")}</Etiqueta>
      <div className="grid gap-x-8 sm:grid-cols-2">
        {tramos.map((tr) => (
          <div
            key={tr.nombre}
            className="flex flex-col gap-1.5 border-b border-linea py-3 last:border-b-0 sm:last:border-b"
          >
            <div className="flex items-baseline justify-between gap-3">
              <span
                className={cn(
                  "text-menor font-semibold",
                  tr.suyo ? "text-acento-texto" : "text-tinta",
                )}
              >
                {t(tr.nombre)}
              </span>
              <span className="cifra text-micro text-tinta-suave">
                {tr.desde} – {tr.hasta}
              </span>
            </div>
            <div className="flex flex-wrap gap-1">
              {Array.from({ length: tr.hasta - tr.desde + 1 }, (_, i) => tr.desde + i).map((v) => (
                <span
                  key={v}
                  aria-current={v === tr.valor ? "true" : undefined}
                  className={cn(
                    "cifra min-w-7 rounded-marco border px-1.5 py-0.5 text-center text-micro font-medium",
                    // Solo el entero donde cae. Encender el tramo entero diría que está en
                    // sus seis valores a la vez.
                    v === tr.valor
                      ? "border-acento bg-acento text-[#0c0c0c] font-bold"
                      : tr.suyo
                        ? "border-acento/40 text-acento-texto"
                        : "border-linea text-tinta-media",
                  )}
                >
                  {v}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function TablaDeConsulta({ tabla }: { tabla: TablaDeHojaApi }) {
  const { t } = useIdioma();
  // El refeeds es dinámico ("Con el día bajo al 12 %."): se corta el número y se
  // vuelve a armar con la clave con marcador, en vez de cambiar cada porcentaje.
  const coincideNota = tabla.nota.match(/^Con el día bajo al (.+) %\.$/);
  const nota = coincideNota
    ? t("Con el día bajo al {pct} %", { pct: coincideNota[1] ?? "" })
    : t(tabla.nota);
  return (
    <section className="flex flex-col gap-2">
      <Etiqueta>{t(tabla.titulo)}</Etiqueta>
      <div className="overflow-x-auto">
        <table className="w-full text-menor">
          <thead>
            <tr className="border-b border-linea">
              {tabla.encabezados.map((h, j) => (
                <th
                  key={h || j}
                  scope="col"
                  className={cn(
                    "py-1.5 text-micro font-semibold uppercase tracking-[0.08em]",
                    j === 0 ? "text-left" : "pl-3 text-right",
                    j === tabla.columnaSuya ? "text-acento-texto" : "text-tinta-suave",
                  )}
                >
                  {t(h)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tabla.filas.map((fila) => (
              <tr
                key={fila.celdas[0]}
                className={cn(
                  "border-b border-linea/60 last:border-b-0",
                  fila.suya && "bg-acento-sutil",
                  fila.fuera && "bg-peligro-sutil",
                )}
              >
                {fila.celdas.map((celda, j) => (
                  <td
                    key={j}
                    className={cn(
                      "py-1.5",
                      j === 0 ? "text-left" : "cifra pl-3 text-right",
                      fila.suya && "font-semibold text-acento-texto",
                      fila.fuera && "font-semibold text-peligro",
                      !fila.suya && !fila.fuera && j > 0 && "text-tinta-media",
                      // Cuando lo suyo es la columna, solo esa se resalta.
                      j === tabla.columnaSuya && "font-semibold text-acento-texto",
                      j === 0 && fila.suya && "border-l-2 border-l-acento pl-2",
                      j === 0 && fila.fuera && "border-l-2 border-l-peligro pl-2",
                    )}
                  >
                    {j === 0 ? t(celda) : celda}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {tabla.nota ? <p className="text-micro text-tinta-suave">{nota}</p> : null}
    </section>
  );
}
