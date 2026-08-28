/** Tabla «PROYECCIÓN PÉRDIDA DE GRASA»
 *
 *  Formato y cálculos fieles a «Calculadora del Fitness.xlsm» (hoja «Calculo bajar de peso »,
 *  rango G5:J10 y celdas auxiliares H106:H117).
 *
 *  Todos los campos son editables interactivamente: al modificar cualquier celda (kilos
 *  por bajar, pérdida semanal, porcentaje semanal, días o límites recomendados), los
 *  demás valores y el déficit calórico se recalculan automáticamente de forma bidireccional.
 *
 *  La paleta de estilos y colores respeta 100 % el sistema de diseño del resto de la aplicación.
 */

import { RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";

import { Aviso } from "@/componentes/primitivas";
import type { Composicion, Energia } from "@/lib/calculadora";
import { num } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";

interface TablaProyeccionPerdidaProps {
  comp: Composicion;
  energia: Energia;
  porcentajeGrasaObjetivo: number;
  onPorcentajeGrasaObjetivo?: (pct: number) => void;
  ajustePct: number;
  onAjustePct?: (pct: number) => void;
}

export function TablaProyeccionPerdida({
  comp,
  energia,
  porcentajeGrasaObjetivo,
  onPorcentajeGrasaObjetivo,
  ajustePct,
  onAjustePct,
}: TablaProyeccionPerdidaProps) {
  const { t } = useIdioma();

  // Estado para overrides opcionales de límites de recomendación
  const [customRecMin, setCustomRecMin] = useState<string | null>(null);
  const [customRecMax, setCustomRecMax] = useState<string | null>(null);

  // Estados temporales de entrada para edición fluida
  const [inputKgBajar, setInputKgBajar] = useState<string>("");
  const [inputPerdidaSemanal, setInputPerdidaSemanal] = useState<string>("");
  const [inputPctSemanal, setInputPctSemanal] = useState<string>("");
  const [inputDias, setInputDias] = useState<string>("");
  const [inputGrasaObj, setInputGrasaObj] = useState<string>("");

  // Fórmulas exactas de Excel (Calculadora del Fitness.xlsm)
  const peso = comp.pesoKg;
  const grasaActualFraccion = comp.porcentajeGrasa;
  const masaGrasaActual = peso * grasaActualFraccion; // C14
  const masaGrasaObjetivo =
    grasaActualFraccion > 0 ? (porcentajeGrasaObjetivo * masaGrasaActual) / grasaActualFraccion : 0; // H109
  const kgGrasaPorBajar = Math.max(0, masaGrasaActual - masaGrasaObjetivo); // H108
  const kgMlgQueSePierden = kgGrasaPorBajar * 0.2; // H106 = H108 * 20%
  const kgTotalesPorBajar = kgGrasaPorBajar + kgMlgQueSePierden; // H6 = H108 + H106

  const grasaPura = kgGrasaPorBajar * 0.87;
  const proteinaPura = kgMlgQueSePierden * 0.3;
  const kcalTotales = (grasaPura * 9 + proteinaPura * 4) * 1000; // H113

  const recMinDefecto = peso * 0.005; // H7: C7 * 0.5%
  const recMaxDefecto = peso * 0.01; // I7: C7 * 1.0%

  const recMin = customRecMin !== null && !isNaN(Number(customRecMin)) ? Number(customRecMin) : recMinDefecto;
  const recMax = customRecMax !== null && !isNaN(Number(customRecMax)) ? Number(customRecMax) : recMaxDefecto;

  const deficitPctEfectivo = ajustePct < 0 ? Math.abs(ajustePct) / 100 : 0.28;
  const deficitDiario =
    energia.ajusteDiarioKcal < 0
      ? -energia.ajusteDiarioKcal
      : energia.mantenimientoKcal * deficitPctEfectivo;
  const deficitSemanal = deficitDiario * 7;

  // Pérdida semanal según déficit (H8 / H117)
  const perdidaSemanalKg =
    kcalTotales > 0 && deficitSemanal > 0 ? (deficitSemanal * kgTotalesPorBajar) / kcalTotales : 0;
  // % de pérdida de peso semanal según déficit (H9)
  const pctSemanal = peso > 0 ? (perdidaSemanalKg / peso) * 100 : 0;
  // Días para bajar grasa objetivo según déficit (H10)
  const diasEstimados = deficitDiario > 0 ? kcalTotales / deficitDiario : 0;

  // Sincronizar inputs cuando cambian los cálculos base
  useEffect(() => {
    setInputKgBajar(num(kgTotalesPorBajar, 3));
  }, [kgTotalesPorBajar]);

  useEffect(() => {
    setInputPerdidaSemanal(perdidaSemanalKg > 0 ? `-${num(perdidaSemanalKg, 3)}` : "0.000");
  }, [perdidaSemanalKg]);

  useEffect(() => {
    setInputPctSemanal(pctSemanal > 0 ? `-${num(pctSemanal, 2)}%` : "0.00%");
  }, [pctSemanal]);

  useEffect(() => {
    setInputDias(diasEstimados > 0 ? `-${Math.round(diasEstimados)}` : "0");
  }, [diasEstimados]);

  useEffect(() => {
    setInputGrasaObj(num(porcentajeGrasaObjetivo * 100, 1));
  }, [porcentajeGrasaObjetivo]);

  // Manejo de edición de Kilos aproximados por bajar
  const aplicarKgBajar = (valStr: string) => {
    const val = parseFloat(valStr.replace(",", "."));
    if (isNaN(val) || val <= 0 || !onPorcentajeGrasaObjetivo) return;
    // Si H6 = 1.2 * (MG - MG_obj) => MG_obj = MG - (H6 / 1.2)
    const nuevaGrasaPorBajar = val / 1.2;
    const nuevaMasaGrasaObj = Math.max(0, masaGrasaActual - nuevaGrasaPorBajar);
    const nuevoPctObj = nuevaMasaGrasaObj / peso;
    onPorcentajeGrasaObjetivo(Math.min(grasaActualFraccion - 0.005, Math.max(0.03, nuevoPctObj)));
  };

  // Manejo de edición de % Grasa Objetivo directamente
  const aplicarPctGrasaObj = (valStr: string) => {
    const val = parseFloat(valStr.replace(",", "."));
    if (isNaN(val) || val <= 0 || !onPorcentajeGrasaObjetivo) return;
    onPorcentajeGrasaObjetivo(Math.min(grasaActualFraccion - 0.005, Math.max(0.03, val / 100)));
  };

  // Manejo de edición de Pérdida Semanal
  const aplicarPerdidaSemanal = (valStr: string) => {
    const val = Math.abs(parseFloat(valStr.replace(",", ".")));
    if (isNaN(val) || val <= 0 || !onAjustePct || energia.mantenimientoKcal <= 0) return;
    const dias = (kgTotalesPorBajar / val) * 7;
    const deficitDiarioReq = kcalTotales / dias;
    const nuevoAjuste = -Math.round((deficitDiarioReq / energia.mantenimientoKcal) * 100);
    onAjustePct(Math.min(-1, Math.max(-50, nuevoAjuste)));
  };

  // Manejo de edición de % de Pérdida Semanal
  const aplicarPctSemanal = (valStr: string) => {
    const val = Math.abs(parseFloat(valStr.replace("%", "").replace(",", ".")));
    if (isNaN(val) || val <= 0 || !onAjustePct || energia.mantenimientoKcal <= 0) return;
    const kgSemanal = (val / 100) * peso;
    const dias = (kgTotalesPorBajar / kgSemanal) * 7;
    const deficitDiarioReq = kcalTotales / dias;
    const nuevoAjuste = -Math.round((deficitDiarioReq / energia.mantenimientoKcal) * 100);
    onAjustePct(Math.min(-1, Math.max(-50, nuevoAjuste)));
  };

  // Manejo de edición de Días Estimados
  const aplicarDias = (valStr: string) => {
    const val = Math.abs(parseFloat(valStr.replace("-", "").replace(",", ".")));
    if (isNaN(val) || val <= 0 || !onAjustePct || energia.mantenimientoKcal <= 0) return;
    const deficitDiarioReq = kcalTotales / val;
    const nuevoAjuste = -Math.round((deficitDiarioReq / energia.mantenimientoKcal) * 100);
    onAjustePct(Math.min(-1, Math.max(-50, nuevoAjuste)));
  };

  // Restablecer límites y cálculos
  const restablecer = () => {
    setCustomRecMin(null);
    setCustomRecMax(null);
    if (onAjustePct) onAjustePct(-28);
  };

  const dentroDeLoRecomendado = perdidaSemanalKg >= recMin && perdidaSemanalKg <= recMax;

  return (
    <section className="flex flex-col gap-3">
      {/* Contenedor principal de la tabla estilo editorial / Excel */}
      <div className="overflow-hidden rounded-marco border border-linea bg-fondo shadow-xs">
        {/* Cabecera de la tabla */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-linea bg-tinta px-4 py-3 text-fondo dark:bg-tinta-suave/20 dark:text-tinta">
          <h3 className="cifra text-menor font-bold tracking-wider uppercase">
            {t("PROYECCIÓN PÉRDIDA DE GRASA")}
          </h3>
          <div className="flex items-center gap-3">
            {onPorcentajeGrasaObjetivo ? (
              <div className="flex items-center gap-1.5 text-micro">
                <span className="opacity-80">{t("Meta grasa:")}</span>
                <input
                  type="text"
                  value={inputGrasaObj}
                  onChange={(e) => setInputGrasaObj(e.target.value)}
                  onBlur={() => aplicarPctGrasaObj(inputGrasaObj)}
                  onKeyDown={(e) => e.key === "Enter" && aplicarPctGrasaObj(inputGrasaObj)}
                  className="cifra h-6 w-14 rounded-marco border border-fondo/30 bg-fondo/10 px-1.5 text-center font-bold text-fondo placeholder:text-fondo/50 focus:border-acento focus:bg-fondo focus:text-tinta focus:outline-none dark:border-tinta/30 dark:bg-tinta/10 dark:text-tinta"
                  title={t("Porcentaje de grasa objetivo")}
                />
                <span className="font-semibold">%</span>
              </div>
            ) : null}
            <button
              type="button"
              onClick={restablecer}
              className="flex items-center gap-1 rounded-marco px-2 py-1 text-micro text-fondo/80 transition-colors hover:bg-fondo/10 hover:text-fondo dark:text-tinta/80 dark:hover:bg-tinta/10"
              title={t("Restablecer a valores automáticos")}
            >
              <RotateCcw className="size-3" /> {t("Auto")}
            </button>
          </div>
        </div>

        {/* Tabla responsive con todas las filas y celdas editables */}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-menor">
            <tbody className="divide-y divide-linea">
              {/* FILA 1: Kilos aproximados por bajar */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                <th
                  scope="row"
                  className="w-1/2 border-r border-linea bg-fondo-sutil/60 p-3 font-semibold text-tinta"
                >
                  {t("Kilos aproximados X bajar para llegar % grasa objetivo:")}
                </th>
                <td colSpan={2} className="border-r border-linea p-1.5 text-center">
                  <input
                    type="text"
                    value={inputKgBajar}
                    onChange={(e) => setInputKgBajar(e.target.value)}
                    onBlur={() => aplicarKgBajar(inputKgBajar)}
                    onKeyDown={(e) => e.key === "Enter" && aplicarKgBajar(inputKgBajar)}
                    className="cifra h-9 w-full rounded-marco bg-fondo px-2 text-center text-menor font-bold text-tinta transition-all hover:bg-fondo-sutil focus:border focus:border-acento focus:bg-fondo focus:outline-none"
                    title={t("Kilos totales estimados a bajar (editable)")}
                  />
                </td>
                <td className="w-12 border-r border-linea bg-fondo-sutil/40 p-3 text-center font-medium text-tinta-suave">
                  Kg
                </td>
                <td className="w-10 bg-fondo-sutil/20 p-3" />
              </tr>

              {/* FILA 2: Reducción semanal recomendada (Mínimo y Máximo) */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                <th
                  scope="row"
                  className="border-r border-linea bg-fondo-sutil/60 p-3 font-semibold text-tinta"
                >
                  {t("Reducción de peso semanal recomendada (0.5 a 1.0%)")}
                </th>
                <td className="border-r border-linea p-1.5 text-center">
                  <input
                    type="text"
                    value={customRecMin !== null ? customRecMin : num(recMin, 3)}
                    onChange={(e) => setCustomRecMin(e.target.value)}
                    className="cifra h-9 w-full rounded-marco bg-acento-sutil/60 px-2 text-center text-menor font-bold text-acento-texto transition-all hover:bg-acento-sutil focus:border focus:border-acento focus:bg-fondo focus:text-tinta focus:outline-none"
                    title={t("Mínimo recomendado (0.5% del peso semanal, editable)")}
                  />
                </td>
                <td className="border-r border-linea p-1.5 text-center">
                  <input
                    type="text"
                    value={customRecMax !== null ? customRecMax : num(recMax, 3)}
                    onChange={(e) => setCustomRecMax(e.target.value)}
                    className="cifra h-9 w-full rounded-marco bg-acento-sutil/60 px-2 text-center text-menor font-bold text-acento-texto transition-all hover:bg-acento-sutil focus:border focus:border-acento focus:bg-fondo focus:text-tinta focus:outline-none"
                    title={t("Máximo recomendado (1.0% del peso semanal, editable)")}
                  />
                </td>
                <td className="border-r border-linea bg-fondo-sutil/40 p-3 text-center font-medium text-tinta-suave">
                  Kg
                </td>
                <td className="bg-fondo-sutil/20 p-3" />
              </tr>

              {/* FILA 3: Pérdida de peso semanal según déficit */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                <th
                  scope="row"
                  className="border-r border-linea bg-fondo-sutil/60 p-3 font-semibold text-tinta"
                >
                  {t("Pérdida de peso semanal según déficit")}
                </th>
                <td colSpan={2} className="border-r border-linea p-1.5 text-center">
                  <input
                    type="text"
                    value={inputPerdidaSemanal}
                    onChange={(e) => setInputPerdidaSemanal(e.target.value)}
                    onBlur={() => aplicarPerdidaSemanal(inputPerdidaSemanal)}
                    onKeyDown={(e) => e.key === "Enter" && aplicarPerdidaSemanal(inputPerdidaSemanal)}
                    className="cifra h-9 w-full rounded-marco bg-acento-sutil px-2 text-center text-menor font-bold text-acento-texto transition-all hover:bg-acento-sutil/80 focus:border focus:border-acento focus:bg-fondo focus:text-tinta focus:outline-none"
                    title={t("Pérdida semanal en Kg según déficit (editable: ajusta el déficit del plan)")}
                  />
                </td>
                <td className="border-r border-linea bg-fondo-sutil/40 p-3 text-center font-medium text-tinta-suave">
                  Kg
                </td>
                <td className="bg-fondo-sutil/20 p-3" />
              </tr>

              {/* FILA 4: % de pérdida de peso semanal según déficit */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                <th
                  scope="row"
                  className="border-r border-linea bg-fondo-sutil/60 p-3 font-semibold text-tinta"
                >
                  {t("% de pérdida de peso semanal según déficit")}
                </th>
                <td colSpan={2} className="border-r border-linea p-1.5 text-center">
                  <input
                    type="text"
                    value={inputPctSemanal}
                    onChange={(e) => setInputPctSemanal(e.target.value)}
                    onBlur={() => aplicarPctSemanal(inputPctSemanal)}
                    onKeyDown={(e) => e.key === "Enter" && aplicarPctSemanal(inputPctSemanal)}
                    className="cifra h-9 w-full rounded-marco bg-exito-sutil px-2 text-center text-menor font-bold text-exito transition-all hover:bg-exito-sutil/80 focus:border focus:border-exito focus:bg-fondo focus:text-tinta focus:outline-none"
                    title={t("Porcentaje de pérdida semanal relativo al peso (editable)")}
                  />
                </td>
                <td className="border-r border-linea bg-fondo-sutil/40 p-3 text-center font-medium text-tinta-suave">
                  Kg
                </td>
                <td className="bg-fondo-sutil/20 p-3" />
              </tr>

              {/* FILA 5: Días para bajar grasa objetivo según déficit */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                <th
                  scope="row"
                  className="border-r border-linea bg-fondo-sutil/60 p-3 font-semibold text-tinta"
                >
                  {t("Días para bajar grasa objetivo  según déficit:")}
                </th>
                <td colSpan={2} className="border-r border-linea p-1.5 text-center">
                  <input
                    type="text"
                    value={inputDias}
                    onChange={(e) => setInputDias(e.target.value)}
                    onBlur={() => aplicarDias(inputDias)}
                    onKeyDown={(e) => e.key === "Enter" && aplicarDias(inputDias)}
                    className="cifra h-9 w-full rounded-marco bg-fondo px-2 text-center text-menor font-bold text-tinta transition-all hover:bg-fondo-sutil focus:border focus:border-acento focus:bg-fondo focus:outline-none"
                    title={t("Días estimados para alcanzar el objetivo (editable: ajusta el déficit)")}
                  />
                </td>
                <td className="border-r border-linea bg-fondo-sutil/40 p-3 text-center font-medium text-tinta-suave">
                  -
                </td>
                <td className="bg-fondo-sutil/20 p-3" />
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Alerta de validación de ritmo saludable */}
      <Aviso tono={dentroDeLoRecomendado ? "exito" : "atencion"}>
{dentroDeLoRecomendado
        ? t(
            "Ritmo saludable: la pérdida de {perdida} kg/sem está dentro del rango recomendado ({min} a {max} kg por semana).",
            {
              perdida: num(perdidaSemanalKg, 2),
              min: num(recMin, 2),
              max: num(recMax, 2),
            },
          )
        : t(
            "Fuera del ritmo recomendado ({min} a {max} kg/sem). Ajusta los días o el déficit para que sea sostenible.",
            { min: num(recMin, 2), max: num(recMax, 2) },
          )}
      </Aviso>
    </section>
  );
}
