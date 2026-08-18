/** La calculadora con la forma de la hoja de cálculo original.
 *
 *  Mismos bloques, mismas etiquetas y la celda de la que sale cada número: la coach lleva
 *  años con ese archivo y así comprueba que calculamos lo que ella calculaba.
 *
 *  Los valores llegan calculados del servidor; aquí no se hace ni una cuenta.
 */

import { useState } from "react";

import { Aviso, Boton, Chip, Etiqueta, Titulo, Vacio } from "@/componentes/primitivas";
import { api, type BloqueDeHojaApi, type HojaDeCalculoApi } from "@/lib/api";
import { usarApi } from "@/lib/usarApi";
import { cn } from "@/lib/utils";

export function Hoja({ alumnaUlid }: { alumnaUlid: string }) {
  const carga = usarApi<HojaDeCalculoApi>((s) => api.coach.hoja(alumnaUlid, s), [alumnaUlid]);
  const [formulas, setFormulas] = useState(false);
  const [tablas, setTablas] = useState(false);

  if (carga.cargando) return <Vacio>Calculando…</Vacio>;
  const d = carga.datos;
  if (!d) {
    return <Aviso tono="error">No se pudo abrir la calculadora.</Aviso>;
  }
  if (d.falta) {
    return (
      <section className="flex flex-col gap-3">
        <Titulo>Calculadora</Titulo>
        <Aviso tono="atencion" titulo="Todavía no hay con qué calcular">
          {d.falta}
        </Aviso>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <Titulo>Calculadora</Titulo>
        </div>
        <div className="flex flex-wrap gap-2">
          <Boton tono="contorno" medida="chica" onClick={() => setFormulas((v) => !v)}>
            {formulas ? "Ocultar fórmulas" : "Ver fórmulas"}
          </Boton>
          <Boton tono="contorno" medida="chica" onClick={() => setTablas((v) => !v)}>
            {tablas ? "Ocultar tablas" : "Ver tablas"}
          </Boton>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {d.bloques.map((b) => (
          <BloqueHoja key={b.rango} b={b} formulas={formulas} />
        ))}
      </div>

      {tablas ? (
        <div className="grid gap-6 lg:grid-cols-2">
          {d.tablas.map((t) => (
            <div key={t.rango} className="flex flex-col gap-2">
              <div className="flex items-baseline justify-between gap-2">
                <Etiqueta>{t.titulo}</Etiqueta>
                <span className="cifra text-micro text-tinta-suave">{t.rango}</span>
              </div>
              <table className="w-full text-menor">
                <thead>
                  <tr className="border-b border-linea text-left">
                    {t.encabezados.map((h) => (
                      <th
                        key={h}
                        className="py-1.5 text-micro font-semibold uppercase tracking-[0.08em] text-tinta-suave"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {t.filas.map((fila, i) => (
                    <tr key={i} className="border-b border-linea/60">
                      {fila.map((celda, j) => (
                        <td key={j} className={cn("py-1.5", j > 0 && "cifra text-tinta-media")}>
                          {celda}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function BloqueHoja({ b, formulas }: { b: BloqueDeHojaApi; formulas: boolean }) {
  return (
    <article className="flex flex-col gap-2 rounded-marco border border-linea p-4">
      <div className="flex items-baseline justify-between gap-2">
        <Etiqueta>{b.titulo}</Etiqueta>
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
              <span className="min-w-0 flex-1 text-menor">{c.rotulo}</span>
              <span className="cifra text-menor font-semibold">{c.valor}</span>
              {c.unidad ? (
                <span className="w-12 text-micro text-tinta-suave">{c.unidad}</span>
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
        {b.celdas.filter((c) => c.capturado).length} capturados ·{" "}
        {b.celdas.filter((c) => !c.capturado).length} calculados
      </Chip>
    </article>
  );
}
