/** Tabla «PROYECCIÓN AUMENTO DE MÚSCULO»
 *
 *  Formato y cálculos fieles a «Calculadora del Fitness.xlsm» (hoja «Calculo bajar de peso »,
 *  rango G16:J23).
 *
 *  Muestra las dos relaciones (2:1 y 1:1) en paralelo para comparar escenarios de ganancia.
 *  Todos los campos son editables interactivamente: semanas de aumento, aumento semanal,
 *  porcentaje mensual y totales de peso, músculo y grasa.
 *
 *  La paleta de estilos y colores respeta 100 % el sistema de diseño del resto de la aplicación.
 */

import { RotateCcw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Aviso } from "@/componentes/primitivas";

import type { Composicion, Energia } from "@/lib/calculadora";
import { num } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";

interface TablaProyeccionGananciaProps {
  comp: Composicion;
  energia: Energia;
  semanas: number;
  onSemanas: (sem: number) => void;
}

const KCAL_POR_KG_GANADO = 8400;

export function TablaProyeccionGanancia({
  comp,
  energia,
  semanas,
  onSemanas,
}: TablaProyeccionGananciaProps) {
  const { t } = useIdioma();
  const peso = comp.pesoKg;

  // Si el ajuste actual es superávit lo usa, de lo contrario usa una hipótesis positiva base (ej. +10% o semanal)
  const ajusteSemanalKcal =
    energia.ajusteSemanalKcal > 0
      ? energia.ajusteSemanalKcal
      : energia.mantenimientoKcal * 0.1 * 7;

  // Aumento semanal base: H17 = C23 / 8400
  const aumentoSemanalBase = Math.max(0.01, ajusteSemanalKcal / KCAL_POR_KG_GANADO);

  // Único campo capturado de esta tabla: las semanas. El resto son derivados y se muestran
  // en solo-lectura para que no cambien solos ni pisen lo capturado.
  const [inputSemanas, setInputSemanas] = useState<string>(String(semanas));
  const enfocadoSemanas = useRef(false);

  // Cálculos derivados
  const aumentoSemanal = aumentoSemanalBase;
  const musculoSemanalDosAUno = aumentoSemanal * 0.33; // H18 = H17 * 33%
  const musculoSemanalUnoAUno = aumentoSemanal * 0.5; // I18 = H17 * 50%
  const pctMensual = peso > 0 ? ((aumentoSemanal * 4) / peso) * 100 : 0; // H19 = H17 * 4 / C7

  const aumentoTotalKg = aumentoSemanal * semanas; // H21 = H17 * H20
  const musculoTotalDosAUno = musculoSemanalDosAUno * semanas; // H22 = H18 * H20
  const musculoTotalUnoAUno = musculoSemanalUnoAUno * semanas; // I22 = I18 * H20
  const grasaTotalDosAUno = Math.max(0, aumentoTotalKg - musculoTotalDosAUno); // H23 = H21 - H22
  const grasaTotalUnoAUno = Math.max(0, aumentoTotalKg - musculoTotalUnoAUno); // I23 = H21 - I22

  useEffect(() => {
    if (!enfocadoSemanas.current) setInputSemanas(String(semanas));
  }, [semanas]);

  // Manejo de edición de Semanas (único campo capturado de esta tabla)
  const aplicarSemanas = (valStr: string) => {
    const val = Math.max(1, Math.min(104, Math.round(Number(valStr.replace(",", ".")) || 1)));
    onSemanas(val);
  };
  const terminarSemanas = () => {
    enfocadoSemanas.current = false;
    aplicarSemanas(inputSemanas);
  };

  // Restablecer el campo capturado (semanas) a 20. No toca el ajuste global: el
  // superávit se edita en el panel «Ajuste calórico».
  const restablecer = () => {
    onSemanas(20);
  };

  // Solo se proyecta aumento cuando el ajuste global es efectivamente superávit
  // (ajusteSemanalKcal > 0). Si no, es una hipótesis inventada (10 %) y se oculta
  // la tabla para no confundir.
  const enSuperavit = energia.ajusteSemanalKcal > 0;
  if (!enSuperavit) {
    return (
      <section className="flex flex-col gap-3">
        <Aviso tono="info">
          {t(
            "Proyección de aumento no disponible: el ajuste actual no es superávit. El aumento solo se proyecta cuando el plan está en superávit.",
          )}
        </Aviso>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-3">
      {/* Contenedor principal de la tabla */}
      <div className="overflow-hidden rounded-marco border border-linea bg-fondo shadow-xs">
        {/* Cabecera de la tabla */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-linea bg-tinta px-4 py-3 text-fondo dark:bg-tinta-suave/20 dark:text-tinta">
          <h3 className="cifra text-menor font-bold tracking-wider uppercase">
            {t("PROYECCIÓN AUMENTO DE MÚSCULO")}
          </h3>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-micro">
              <span className="opacity-80">{t("Semanas:")}</span>
              <input
                type="text"
                value={inputSemanas}
                onChange={(e) => {
                  const s = e.target.value;
                  setInputSemanas(s);
                  if (String(s).trim() !== "") aplicarSemanas(s);
                }}
                onFocus={() => {
                  enfocadoSemanas.current = true;
                }}
                onBlur={terminarSemanas}
                onKeyDown={(e) => e.key === "Enter" && terminarSemanas()}
                className="cifra h-6 w-12 rounded-marco border border-fondo/30 bg-fondo/10 px-1 text-center font-bold text-fondo placeholder:text-fondo/50 focus:border-acento focus:bg-fondo focus:text-tinta focus:outline-none dark:border-tinta/30 dark:bg-tinta/10 dark:text-tinta"
                title={t("Semanas estimadas de volumen")}
              />
            </div>
            <button
              type="button"
              onClick={restablecer}
              className="flex items-center gap-1 rounded-marco px-2 py-1 text-micro text-fondo/80 transition-colors hover:bg-fondo/10 hover:text-fondo dark:text-tinta/80 dark:hover:bg-tinta/10"
              title={t("Restablecer a 20 semanas")}
            >
              <RotateCcw className="size-3" /> {t("Auto")}
            </button>
          </div>
        </div>

        {/* Tabla responsive con las dos relaciones (2:1 y 1:1) en paralelo */}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-menor">
            <tbody className="divide-y divide-linea">
              {/* FILA 1: Aumento de peso semanal según ajuste */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                <th
                  scope="row"
                  className="w-1/2 border-r border-linea bg-fondo-sutil/60 p-3 font-semibold text-tinta"
                >
                  {t("Aumento de peso semanal según ajuste:")}
                </th>
                <td colSpan={2} className="border-r border-linea p-1.5 text-center">
                  <span className="cifra inline-block h-9 px-2 text-center text-menor font-bold text-tinta">
                    {num(aumentoSemanal, 3)}
                  </span>
                </td>
                <td className="w-12 border-r border-linea bg-fondo-sutil/40 p-3 text-center font-medium text-tinta-suave">
                  Kg
                </td>
                <td className="w-48 bg-fondo-sutil/20 p-3" />
              </tr>

              {/* FILA 2: Aumento de músculo semanal estimado (2:1 vs 1:1) */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                <th
                  scope="row"
                  className="border-r border-linea bg-fondo-sutil/60 p-3 font-semibold text-tinta"
                >
                  {t("Aumento de músculo semanal estimado:")}
                </th>
                {/* 2:1 */}
                <td className="w-1/4 border-r border-linea p-2 text-center font-bold cifra text-tinta bg-fondo">
                  {num(musculoSemanalDosAUno, 3)}
                </td>
                {/* 1:1 */}
                <td className="w-1/4 border-r border-linea p-2 text-center font-bold cifra text-tinta bg-fondo">
                  {num(musculoSemanalUnoAUno, 3)}
                </td>
                <td colSpan={2} className="bg-fondo-sutil/40 p-3 text-center text-micro font-semibold text-tinta-media tracking-wide">
                  {t("Relación 2:1 / Relación 1:1")}
                </td>
              </tr>

              {/* FILA 3: Porcentage de aumento mensual */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                <th
                  scope="row"
                  className="border-r border-linea bg-fondo-sutil/60 p-3 font-semibold text-tinta"
                >
                  {t("Porcentage de aumento mensual:")}
                </th>
                <td colSpan={2} className="border-r border-linea p-1.5 text-center">
                  <span className="cifra inline-block h-9 px-2 text-center text-menor font-bold text-tinta">
                    {num(pctMensual, 2)}%
                  </span>
                </td>
                <td className="border-r border-linea bg-fondo-sutil/40 p-3 text-center font-medium text-tinta-suave">
                  Kg
                </td>
                <td className="bg-fondo-sutil/20 p-3" />
              </tr>

              {/* FILA 4: Semanas de aumento de peso */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                <th
                  scope="row"
                  className="border-r border-linea bg-fondo-sutil/60 p-3 font-semibold text-tinta"
                >
                  {t("Semanas de aumento de peso:")}
                </th>
                <td colSpan={2} className="border-r border-linea p-1.5 text-center bg-fondo">
                  <input
                    type="text"
                    value={inputSemanas}
                    onChange={(e) => {
                      const s = e.target.value;
                      setInputSemanas(s);
                      if (String(s).trim() !== "") aplicarSemanas(s);
                    }}
                    onFocus={() => {
                      enfocadoSemanas.current = true;
                    }}
                    onBlur={terminarSemanas}
                    onKeyDown={(e) => e.key === "Enter" && terminarSemanas()}
                    className="cifra h-9 w-full rounded-marco bg-fondo px-2 text-center text-cuerpo font-bold text-tinta transition-all hover:bg-fondo-sutil focus:border focus:border-acento focus:bg-fondo focus:outline-none"
                    title={t("Número de semanas para la proyección (editable)")}
                  />
                </td>
                <td className="border-r border-linea bg-fondo-sutil/40 p-3 text-center font-medium text-tinta-suave">
                  -
                </td>
                <td className="bg-fondo-sutil/20 p-3" />
              </tr>

              {/* FILA 5: Aumento de peso TOTAL estimado X semanas */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                <th
                  scope="row"
                  className="border-r border-linea bg-fondo-sutil/60 p-3 font-semibold text-tinta"
                >
                  {t("Aumento de peso TOTAL estimado X semanas:")}
                </th>
                <td colSpan={2} className="border-r border-linea p-1.5 text-center">
                  <span className="cifra inline-block h-9 px-2 text-center text-menor font-bold text-tinta">
                    {num(aumentoTotalKg, 3)}
                  </span>
                </td>
                <td className="border-r border-linea bg-fondo-sutil/40 p-3 text-center font-medium text-tinta-suave">
                  Kg
                </td>
                <td className="bg-fondo-sutil/20 p-3" />
              </tr>

              {/* FILA 6: Aumento de musculo estimado X semanas (2:1 vs 1:1) */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                <th
                  scope="row"
                  className="border-r border-linea bg-fondo-sutil/60 p-3 font-semibold text-tinta"
                >
                  {t("Aumento de musculo estimado X semanas:")}
                </th>
                {/* 2:1 */}
                <td className="border-r border-linea p-2 text-center font-bold cifra text-tinta bg-fondo">
                  {num(musculoTotalDosAUno, 3)}
                </td>
                {/* 1:1 */}
                <td className="border-r border-linea p-2 text-center font-bold cifra text-tinta bg-fondo">
                  {num(musculoTotalUnoAUno, 3)}
                </td>
                <td colSpan={2} className="bg-fondo-sutil/40 p-3 text-center text-micro font-semibold text-tinta-media tracking-wide">
                  {t("Relación 2:1 / Relación 1:1")}
                </td>
              </tr>

              {/* FILA 7: Aumento de grasa X semanas (2:1 vs 1:1) */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                <th
                  scope="row"
                  className="border-r border-linea bg-fondo-sutil/60 p-3 font-semibold text-tinta"
                >
                  {t("Aumento de grasa X semanas:")}
                </th>
                {/* 2:1 */}
                <td className="border-r border-linea p-2 text-center font-bold cifra text-tinta bg-fondo">
                  {num(grasaTotalDosAUno, 3)}
                </td>
                {/* 1:1 */}
                <td className="border-r border-linea p-2 text-center font-bold cifra text-tinta bg-fondo">
                  {num(grasaTotalUnoAUno, 3)}
                </td>
                <td colSpan={2} className="bg-fondo-sutil/40 p-3 text-center text-micro font-semibold text-tinta-media tracking-wide">
                  {t("Relación 2:1 / Relación 1:1")}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
