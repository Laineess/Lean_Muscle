/** Edición del contenido del plan: tiempos de comida y días de entrenamiento.
 *
 *  El estado vive aquí y sube al constructor al guardar. La suma de lo capturado se compara
 *  contra el objetivo que calculó la calculadora: sin esa comparación, la coach arma un menú
 *  de 1 400 kcal creyendo que va por 1 850 y no se entera hasta el mes siguiente.
 */

import { Plus } from "lucide-react";
import { useEffect, useState } from "react";

import {
  BuscadorAlimento,
  BuscadorEjercicio,
  FilaEditable,
  escalar,
  type AlimentoEnPlan,
  type EjercicioEnPlan,
} from "@/coach/BuscadorCatalogo";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Chip,
  Entrada,
  Etiqueta,
  Titulo,
  Vacio,
} from "@/componentes/primitivas";
import { num } from "@/lib/formato";

export interface TiempoDeComida {
  nombre: string;
  hora: string;
  kcal: number;
  alimentos: AlimentoEnPlan[];
}

export interface DiaDeEntrenamiento {
  nombre: string;
  ejercicios: EjercicioEnPlan[];
}

/** Margen aceptable entre lo capturado y el objetivo, en fracción. */
const TOLERANCIA = 0.05;

function sumar(alimentos: AlimentoEnPlan[]) {
  return alimentos.reduce(
    (a, x) => ({
      kcal: a.kcal + x.kcal,
      p: a.p + x.p,
      c: a.c + x.c,
      g: a.g + x.g,
    }),
    { kcal: 0, p: 0, c: 0, g: 0 },
  );
}

/** Cantidad de un alimento ya agregado. El texto se edita libre y solo se emite cuando es un
 *  número mayor que cero: si no, borrar para reescribir dejaría la fila en 0 kcal. */
function Cantidad({
  id,
  cantidad,
  unidad,
  onCambio,
}: {
  id: string;
  cantidad: number;
  unidad: string;
  onCambio: (cantidad: number) => void;
}) {
  const [texto, setTexto] = useState(String(cantidad));
  useEffect(() => setTexto(String(cantidad)), [cantidad]);

  return (
    <span className="flex items-center gap-1.5">
      <Entrada
        id={id}
        type="number"
        min={0}
        step="any"
        inputMode="decimal"
        aria-label="Cantidad"
        value={texto}
        onChange={(e) => {
          setTexto(e.target.value);
          const valor = Number.parseFloat(e.target.value);
          if (valor > 0) onCambio(valor);
        }}
        onBlur={() => setTexto(String(cantidad))}
        className="h-9 w-20 px-2 text-right text-menor"
      />
      <span className="text-micro text-tinta-suave">{unidad}</span>
    </span>
  );
}

/* ------------------------------------------------------------- Nutrición --- */

export function EditorNutricion({
  tiempos,
  onCambio,
  objetivoKcal,
  objetivoMacros,
}: {
  tiempos: TiempoDeComida[];
  onCambio: (tiempos: TiempoDeComida[]) => void;
  objetivoKcal: number;
  objetivoMacros: { proteina: number; carbohidrato: number; grasa: number } | null;
}) {
  const [agregandoEn, setAgregandoEn] = useState<number | null>(null);

  const capturado = sumar(tiempos.flatMap((t) => t.alimentos));
  const desvio = objetivoKcal ? Math.abs(capturado.kcal - objetivoKcal) / objetivoKcal : 0;
  const cuadra = objetivoKcal > 0 && desvio <= TOLERANCIA;

  function actualizar(i: number, cambio: Partial<TiempoDeComida>) {
    onCambio(tiempos.map((t, j) => (j === i ? { ...t, ...cambio } : t)));
  }

  function agregarAlimento(i: number, alimento: AlimentoEnPlan) {
    const alimentos = [...tiempos[i]!.alimentos, alimento];
    actualizar(i, { alimentos, kcal: sumar(alimentos).kcal });
  }

  function quitarAlimento(i: number, k: number) {
    const alimentos = tiempos[i]!.alimentos.filter((_, j) => j !== k);
    actualizar(i, { alimentos, kcal: sumar(alimentos).kcal });
  }

  function cambiarCantidad(i: number, k: number, cantidad: number) {
    const alimentos = tiempos[i]!.alimentos.map((a, j) =>
      j === k ? escalar(a.nombre, a.base, cantidad, a.unidad) : a,
    );
    actualizar(i, { alimentos, kcal: sumar(alimentos).kcal });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <Titulo>Tiempos de comida</Titulo>
          <Apoyo>Los macros salen del catálogo: tú eliges el alimento y la cantidad.</Apoyo>
        </div>
        <Boton
          tono="contorno"
          medida="chica"
          onClick={() =>
            onCambio([
              ...tiempos,
              { nombre: `Tiempo ${tiempos.length + 1}`, hora: "12:00", kcal: 0, alimentos: [] },
            ])
          }
        >
          <Plus className="size-3.5" /> Tiempo
        </Boton>
      </div>

      {/* La comparación contra el objetivo es lo que evita armar un menú que no cuadra. */}
      {objetivoKcal > 0 ? (
        <Aviso tono={cuadra ? "exito" : capturado.kcal === 0 ? "info" : "atencion"}>
          <strong className="block font-semibold">
            {capturado.kcal} de {objetivoKcal} kcal capturadas
          </strong>
          {capturado.kcal === 0
            ? "Agrega alimentos y verás cómo se acerca al objetivo."
            : cuadra
              ? "Cuadra con el objetivo."
              : `Faltan ${objetivoKcal - capturado.kcal > 0 ? objetivoKcal - capturado.kcal : 0} kcal${
                  capturado.kcal > objetivoKcal
                    ? ` — te pasaste por ${capturado.kcal - objetivoKcal}`
                    : ""
                }.`}
          {objetivoMacros ? (
            <span className="mt-1 block text-micro">
              Proteína {num(capturado.p, 0)} / {objetivoMacros.proteina} g · Carbos{" "}
              {num(capturado.c, 0)} / {objetivoMacros.carbohidrato} g · Grasa {num(capturado.g, 0)} /{" "}
              {objetivoMacros.grasa} g
            </span>
          ) : null}
        </Aviso>
      ) : null}

      {tiempos.length === 0 ? (
        <Vacio>Todavía no hay tiempos de comida. Agrega el primero.</Vacio>
      ) : (
        tiempos.map((t, i) => {
          const total = sumar(t.alimentos);
          return (
            <article key={i} className="flex flex-col gap-3 rounded-marco border border-linea p-4">
              <div className="flex flex-wrap items-end gap-3">
                <Campo id={`t-nombre-${i}`} etiqueta="Tiempo">
                  <Entrada
                    id={`t-nombre-${i}`}
                    value={t.nombre}
                    onChange={(e) => actualizar(i, { nombre: e.target.value })}
                    className="max-w-48"
                  />
                </Campo>
                <Campo id={`t-hora-${i}`} etiqueta="Hora">
                  <Entrada
                    id={`t-hora-${i}`}
                    type="time"
                    value={t.hora}
                    onChange={(e) => actualizar(i, { hora: e.target.value })}
                    className="max-w-32"
                  />
                </Campo>
                <Chip className="mb-2.5">{total.kcal} kcal</Chip>
                <Boton
                  tono="discreto"
                  medida="chica"
                  className="mb-1.5 ml-auto"
                  onClick={() => onCambio(tiempos.filter((_, j) => j !== i))}
                >
                  Quitar tiempo
                </Boton>
              </div>

              {t.alimentos.length === 0 ? (
                <Apoyo>Sin alimentos todavía.</Apoyo>
              ) : (
                <ul className="flex flex-col divide-y divide-linea border-y border-linea">
                  {t.alimentos.map((a, k) => (
                    <FilaEditable
                      key={`${a.nombre}-${k}`}
                      className="items-center"
                      onQuitar={() => quitarAlimento(i, k)}
                    >
                      <span className="text-menor">{a.nombre}</span>
                      <span className="flex flex-wrap items-center gap-2">
                        <Cantidad
                          id={`t-${i}-a-${k}`}
                          cantidad={a.cantidad}
                          unidad={a.unidad}
                          onCambio={(valor) => cambiarCantidad(i, k, valor)}
                        />
                        <span className="cifra text-micro text-tinta-suave">
                          {a.kcal} kcal · P {a.p} C {a.c} G {a.g}
                        </span>
                      </span>
                    </FilaEditable>
                  ))}
                </ul>
              )}

              <div>
                <Boton tono="contorno" medida="chica" onClick={() => setAgregandoEn(i)}>
                  <Plus className="size-3.5" /> Alimento
                </Boton>
              </div>
            </article>
          );
        })
      )}

      {agregandoEn !== null ? (
        <BuscadorAlimento
          onElegir={(a) => agregarAlimento(agregandoEn, a)}
          onCerrar={() => setAgregandoEn(null)}
        />
      ) : null}
    </div>
  );
}

/* --------------------------------------------------------- Entrenamiento --- */

export function EditorEntrenamiento({
  dias,
  onCambio,
  plantilla,
  onPlantilla,
  lesiones,
}: {
  dias: DiaDeEntrenamiento[];
  onCambio: (dias: DiaDeEntrenamiento[]) => void;
  plantilla: string;
  onPlantilla: (v: string) => void;
  lesiones: string | null;
}) {
  const [agregandoEn, setAgregandoEn] = useState<number | null>(null);

  function actualizar(i: number, cambio: Partial<DiaDeEntrenamiento>) {
    onCambio(dias.map((d, j) => (j === i ? { ...d, ...cambio } : d)));
  }

  function actualizarEjercicio(i: number, k: number, cambio: Partial<EjercicioEnPlan>) {
    actualizar(i, {
      ejercicios: dias[i]!.ejercicios.map((e, j) => (j === k ? { ...e, ...cambio } : e)),
    });
  }

  const totalEjercicios = dias.reduce((a, d) => a + d.ejercicios.length, 0);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <Titulo>Estructura de la semana</Titulo>
          <Apoyo>
            {dias.length} días · {totalEjercicios} ejercicios
          </Apoyo>
        </div>
        <Boton
          tono="contorno"
          medida="chica"
          onClick={() =>
            onCambio([...dias, { nombre: `Día ${dias.length + 1}`, ejercicios: [] }])
          }
        >
          <Plus className="size-3.5" /> Día
        </Boton>
      </div>

      <Campo id="e-plantilla" etiqueta="Plantilla base" ayuda="Aparece en el PDF de la alumna.">
        <Entrada
          id="e-plantilla"
          value={plantilla}
          onChange={(e) => onPlantilla(e.target.value)}
          placeholder="Fuerza superior/inferior — 4 días"
        />
      </Campo>

      {lesiones ? (
        <Aviso tono="error" titulo="Cuidado con su historial">
          {lesiones}
        </Aviso>
      ) : null}

      {dias.length === 0 ? (
        <Vacio>Todavía no hay días. Agrega el primero.</Vacio>
      ) : (
        dias.map((d, i) => (
          <article key={i} className="flex flex-col gap-3 rounded-marco border border-linea p-4">
            <div className="flex flex-wrap items-end gap-3">
              <Campo id={`d-nombre-${i}`} etiqueta="Día">
                <Entrada
                  id={`d-nombre-${i}`}
                  value={d.nombre}
                  onChange={(e) => actualizar(i, { nombre: e.target.value })}
                  className="max-w-72"
                />
              </Campo>
              <Boton
                tono="discreto"
                medida="chica"
                className="mb-1.5 ml-auto"
                onClick={() => onCambio(dias.filter((_, j) => j !== i))}
              >
                Quitar día
              </Boton>
            </div>

            {d.ejercicios.length === 0 ? (
              <Apoyo>Sin ejercicios todavía.</Apoyo>
            ) : (
              <ul className="flex flex-col divide-y divide-linea border-y border-linea">
                {d.ejercicios.map((e, k) => (
                  <li key={`${e.nombre}-${k}`} className="flex flex-col gap-2 py-3">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-menor font-medium">{e.nombre}</span>
                      <Boton
                        tono="discreto"
                        medida="chica"
                        onClick={() =>
                          actualizar(i, {
                            ejercicios: d.ejercicios.filter((_, j) => j !== k),
                          })
                        }
                      >
                        Quitar
                      </Boton>
                    </div>

                    {/* Editable en línea: ajustar carga es lo que más se toca mes a mes. */}
                    <div className="grid gap-2 sm:grid-cols-4">
                      <Entrada
                        type="number"
                        min={1}
                        value={e.series}
                        onChange={(ev) =>
                          actualizarEjercicio(i, k, { series: Number(ev.target.value) })
                        }
                        aria-label="Series"
                        className="h-9"
                      />
                      <Entrada
                        value={e.reps}
                        onChange={(ev) => actualizarEjercicio(i, k, { reps: ev.target.value })}
                        aria-label="Repeticiones"
                        className="h-9"
                      />
                      <Entrada
                        value={e.carga}
                        onChange={(ev) => actualizarEjercicio(i, k, { carga: ev.target.value })}
                        aria-label="Carga"
                        placeholder="Carga"
                        className="h-9"
                      />
                      <Entrada
                        value={e.nota}
                        onChange={(ev) => actualizarEjercicio(i, k, { nota: ev.target.value })}
                        aria-label="Nota"
                        placeholder="Nota"
                        className="h-9"
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}

            <div>
              <Boton tono="contorno" medida="chica" onClick={() => setAgregandoEn(i)}>
                <Plus className="size-3.5" /> Ejercicio
              </Boton>
            </div>
          </article>
        ))
      )}

      {agregandoEn !== null ? (
        <BuscadorEjercicio
          lesiones={lesiones}
          onElegir={(e) =>
            actualizar(agregandoEn, { ejercicios: [...dias[agregandoEn]!.ejercicios, e] })
          }
          onCerrar={() => setAgregandoEn(null)}
        />
      ) : null}
    </div>
  );
}

export { Etiqueta };
