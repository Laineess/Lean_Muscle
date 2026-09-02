/** Tabla «CÁLCULO DE REFEEDS»
 *
 *  Formato y cálculos fieles a «Calculadora del Fitness.xlsm» (hoja «Calculo bajar de peso »,
 *  rango G12:J14, celdas G14, H14 y J14).
 *
 *  Muestra la relación entre el déficit del día bajo, los días de refeed (0, 1 o 2) y el
 *  déficit promedio semanal resultante.
 *
 *  Todos los campos son editables interactivamente y recalculan en tiempo real.
 *  La paleta de estilos y colores respeta 100 % el sistema de diseño del resto de la aplicación.
 */

import { RotateCcw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { num } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";

interface TablaRefeedsProps {
  diaBajoPct: number; // porcentaje positivo, ej. 26
  onDiaBajoPct: (val: number) => void;
  diasRefeed: number; // 0, 1 o 2
  onDiasRefeed: (val: number) => void;
  refeedPct?: number; // déficit del día de refeed, por defecto 0 (mantenimiento)
  onRefeedPct?: (val: number) => void;
}

export function TablaRefeeds({
  diaBajoPct,
  onDiaBajoPct,
  diasRefeed,
  onDiasRefeed,
  refeedPct = 0,
}: TablaRefeedsProps) {
  const { t } = useIdioma();
  const diaBajoPositivo = Math.abs(diaBajoPct);

  // Único campo capturado de esta tabla: el % de déficit del día bajo. El promedio semanal
  // es un derivado y se muestra en solo-lectura para que no cambie solo ni pise lo capturado.
  const [inputDiaBajo, setInputDiaBajo] = useState<string>(String(diaBajoPositivo));
  const enfocadoDiaBajo = useRef(false);

  // Cálculo del déficit promedio semanal: J14 = (G14*(7-H14) + H14*I14) / 7
  const diasBajos = Math.max(0, 7 - diasRefeed);
  const promedioSemanal =
    diasRefeed === 0
      ? diaBajoPositivo
      : (diaBajoPositivo * diasBajos + refeedPct * diasRefeed) / 7;

  useEffect(() => {
    if (!enfocadoDiaBajo.current) setInputDiaBajo(String(diaBajoPositivo));
  }, [diaBajoPositivo]);

  // Manejo de edición de % déficit día bajo
  const aplicarDiaBajo = (valStr: string) => {
    const val = Math.abs(parseFloat(valStr.replace("%", "").replace(",", ".")));
    if (isNaN(val)) return;
    onDiaBajoPct(-Math.round(val));
  };
  const terminarDiaBajo = () => {
    enfocadoDiaBajo.current = false;
    aplicarDiaBajo(inputDiaBajo);
  };

  // Restablecer a 1 día de refeed
  const restablecer = () => {
    onDiasRefeed(1);
    onDiaBajoPct(-26);
  };

  return (
    <section className="flex flex-col gap-3">
      {/* Contenedor principal de la tabla */}
      <div className="overflow-hidden rounded-marco border border-linea bg-fondo shadow-xs">
        {/* Cabecera de la tabla */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-linea bg-tinta px-4 py-3 text-fondo dark:bg-tinta-suave/20 dark:text-tinta">
          <h3 className="cifra text-menor font-bold tracking-wider uppercase">
            {t("CÁLCULO DE REFEEDS")}
          </h3>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={restablecer}
              className="flex items-center gap-1 rounded-marco px-2 py-1 text-micro text-fondo/80 transition-colors hover:bg-fondo/10 hover:text-fondo dark:text-tinta/80 dark:hover:bg-tinta/10"
              title={t("Restablecer a 26% y 1 día de refeed")}
            >
              <RotateCcw className="size-3" /> {t("Auto (26% / 1d)")}
            </button>
          </div>
        </div>

        {/* Tabla responsive */}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-center text-menor">
            <thead>
              <tr className="border-b border-linea bg-fondo-sutil/70 text-tinta font-semibold">
                <th scope="col" className="w-1/3 border-r border-linea p-2.5">
                  {t("% de déficit día bajo")}
                </th>
                <th scope="col" className="w-1/3 border-r border-linea p-2.5">
                  {t("Días de Refeed")}
                </th>
                <th scope="col" className="w-1/3 p-2.5">
                  {t("Déficit promedio semanal")}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-linea">
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                {/* Col 1: % de déficit día bajo */}
                <td className="border-r border-linea bg-fondo p-2">
                  <div className="flex items-center justify-center">
                    <input
                      type="text"
                      value={inputDiaBajo}
                      onChange={(e) => {
                        const s = e.target.value;
                        setInputDiaBajo(s);
                        if (String(s).trim() !== "") aplicarDiaBajo(s);
                      }}
                      onFocus={() => {
                        enfocadoDiaBajo.current = true;
                      }}
                      onBlur={terminarDiaBajo}
                      onKeyDown={(e) => e.key === "Enter" && terminarDiaBajo()}
                      className="cifra h-10 w-24 rounded-marco bg-fondo px-2 text-center text-guia font-bold text-tinta transition-all hover:bg-fondo-sutil focus:border focus:border-acento focus:bg-fondo focus:outline-none"
                      title={t("% de déficit en los días bajos (editable)")}
                    />
                  </div>
                </td>

                {/* Col 2: Días de Refeed */}
                <td className="border-r border-linea bg-fondo p-2">
                  <div className="flex items-center justify-center">
                    <select
                      value={diasRefeed}
                      onChange={(e) => onDiasRefeed(Number(e.target.value))}
                      className="cifra h-10 w-24 rounded-marco bg-fondo px-2 text-center text-guia font-bold text-tinta transition-all hover:bg-fondo-sutil focus:border focus:border-acento focus:bg-fondo focus:outline-none cursor-pointer"
                      title={t("Días de refeed por semana (0, 1 o 2)")}
                    >
                      <option value={0}>0</option>
                      <option value={1}>1</option>
                      <option value={2}>2</option>
                    </select>
                  </div>
                </td>

                {/* Col 3: Déficit promedio semanal */}
                <td className="bg-acento-sutil/40 p-2">
                  <div className="flex items-center justify-center">
                    <span className="cifra inline-block h-10 px-2 text-center text-guia font-bold text-acento-texto">
                      {num(promedioSemanal, 1)}%
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
