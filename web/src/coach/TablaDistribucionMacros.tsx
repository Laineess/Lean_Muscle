/** Tabla «PORCENTAJE DE DISTRIBUCIÓN DE MACROS»
 *
 *  Formato y cálculos fieles a «Calculadora del Fitness.xlsm» (hoja «Calculo bajar de peso »,
 *  rango B25:E32 y celdas auxiliares B93:B95, C30:C32).
 *
 *  Todos los campos son editables interactivamente:
 *  - Porcentajes (%) de cada macro (Carbohidratos, Proteínas, Grasas).
 *  - Gramos calculados directamente.
 *  - Gramos por kilo de peso corporal / MLG.
 *
 *  La paleta de estilos y colores respeta 100 % el sistema de diseño del resto de la aplicación.
 */

import { AlertCircle, CheckCircle2, RotateCcw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Chip } from "@/componentes/primitivas";
import {
  RANGO_GKG,
  type BaseProteina,
  type Composicion,
  type Energia,
  type Macro,
} from "@/lib/calculadora";
import { num } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
import { cn } from "@/lib/utils";

interface Reparto {
  carbohidrato: number; // en porcentaje 0-100
  proteina: number; // en porcentaje 0-100
  grasa: number; // en porcentaje 0-100
}

interface TablaDistribucionMacrosProps {
  comp: Composicion;
  energia: Energia;
  reparto: Reparto;
  onReparto: (nuevo: Reparto | ((prev: Reparto) => Reparto)) => void;
  baseProteina: BaseProteina;
  onBaseProteina?: (base: BaseProteina) => void;
}

export function TablaDistribucionMacros({
  comp,
  energia,
  reparto,
  onReparto,
  baseProteina,
  onBaseProteina,
}: TablaDistribucionMacrosProps) {
  const { t } = useIdioma();

  // Inputs locales para edición fluida (solo los porcentajes son capturados)
  const [inputCarboPct, setInputCarboPct] = useState(String(reparto.carbohidrato));
  const [inputProtPct, setInputProtPct] = useState(String(reparto.proteina));
  const [inputGrasaPct, setInputGrasaPct] = useState(String(reparto.grasa));

  const enfocadoCarboPct = useRef(false);
  const enfocadoProtPct = useRef(false);
  const enfocadoGrasaPct = useRef(false);

  const kcalAjustadas = energia.ajustadasKcal;
  const peso = comp.pesoKg;
  const mlg = comp.masaLibreDeGrasaKg;
  const refProteina = baseProteina === "masa_libre_de_grasa" ? mlg : peso;

  // Cálculos de gramos y g/kg exactos de Excel
  const carboG = kcalAjustadas > 0 ? (kcalAjustadas * (reparto.carbohidrato / 100)) / 4 : 0;
  const protG = kcalAjustadas > 0 ? (kcalAjustadas * (reparto.proteina / 100)) / 4 : 0;
  const grasaG = kcalAjustadas > 0 ? (kcalAjustadas * (reparto.grasa / 100)) / 9 : 0;

  const carboGkg = peso > 0 ? carboG / peso : 0;
  const protGkg = refProteina > 0 ? protG / refProteina : 0;
  const grasaGkg = peso > 0 ? grasaG / peso : 0;

  const sumaReparto = Math.round(reparto.carbohidrato + reparto.proteina + reparto.grasa);
  const repartoCuadra = sumaReparto === 100;

  // Sincronizar inputs locales con estado (saltando mientras el campo está enfocado)
  useEffect(() => {
    if (!enfocadoCarboPct.current) setInputCarboPct(String(reparto.carbohidrato));
  }, [reparto.carbohidrato]);

  useEffect(() => {
    if (!enfocadoProtPct.current) setInputProtPct(String(reparto.proteina));
  }, [reparto.proteina]);

  useEffect(() => {
    if (!enfocadoGrasaPct.current) setInputGrasaPct(String(reparto.grasa));
  }, [reparto.grasa]);

  // Manejadores de cambios en Porcentajes
  const aplicarPct = (macro: Macro, valStr: string) => {
    const val = Math.max(0, Math.min(100, Math.round(Number(valStr.replace(",", ".")) || 0)));
    onReparto((prev) => ({ ...prev, [macro]: val }));
  };
  const terminarCarboPct = () => {
    enfocadoCarboPct.current = false;
    aplicarPct("carbohidrato", inputCarboPct);
  };
  const terminarProtPct = () => {
    enfocadoProtPct.current = false;
    aplicarPct("proteina", inputProtPct);
  };
  const terminarGrasaPct = () => {
    enfocadoGrasaPct.current = false;
    aplicarPct("grasa", inputGrasaPct);
  };

  // Restablecer a 50 / 28 / 22 (por defecto en Excel)
  const restablecerPorDefecto = () => {
    onReparto({ carbohidrato: 50, proteina: 28, grasa: 22 });
  };

  // Verificación de rangos saludables
  const fueraCarbo = carboGkg < RANGO_GKG.carbohidrato[0] || carboGkg > RANGO_GKG.carbohidrato[1];
  const fueraProt = protGkg < RANGO_GKG.proteina[0] || protGkg > RANGO_GKG.proteina[1];
  const fueraGrasa = grasaGkg < RANGO_GKG.grasa[0] || grasaGkg > RANGO_GKG.grasa[1];

  return (
    <section className="flex flex-col gap-3">
      {/* Contenedor principal de la tabla */}
      <div className="overflow-hidden rounded-marco border border-linea bg-fondo shadow-xs">
        {/* Cabecera de la tabla */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-linea bg-tinta px-4 py-3 text-fondo dark:bg-tinta-suave/20 dark:text-tinta">
          <h3 className="cifra text-menor font-bold tracking-wider uppercase">
            {t("PORCENTAJE DE DISTRIBUCIÓN DE MACROS")}
          </h3>
          <div className="flex items-center gap-3">
            {onBaseProteina ? (
              <div className="flex items-center gap-1.5 text-micro">
                <span className="opacity-80">{t("Proteína vs:")}</span>
                <select
                  value={baseProteina}
                  onChange={(e) => onBaseProteina(e.target.value as BaseProteina)}
                  className="rounded-marco border border-fondo/30 bg-fondo/10 px-2 py-0.5 text-micro font-medium text-fondo focus:border-acento focus:bg-fondo focus:text-tinta focus:outline-none dark:border-tinta/30 dark:bg-tinta/10 dark:text-tinta"
                >
                  <option value="masa_libre_de_grasa" className="text-tinta">
                    {t("MLG ({n} kg)", { n: num(mlg, 1) })}
                  </option>
                  <option value="peso_total" className="text-tinta">
                    {t("Peso total ({n} kg)", { n: num(peso, 1) })}
                  </option>
                </select>
              </div>
            ) : null}
            <button
              type="button"
              onClick={restablecerPorDefecto}
              className="flex items-center gap-1 rounded-marco px-2 py-1 text-micro text-fondo/80 transition-colors hover:bg-fondo/10 hover:text-fondo dark:text-tinta/80 dark:hover:bg-tinta/10"
              title={t("Restablecer a 50/28/22")}
            >
              <RotateCcw className="size-3" /> 50/28/22
            </button>
          </div>
        </div>

        {/* Tabla responsive */}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-center text-menor">
            {/* BLOQUE SUPERIOR: Encabezados de Macros y % */}
            <thead>
              <tr className="border-b border-linea bg-fondo-sutil/70 text-tinta font-semibold">
                <th scope="col" className="w-1/3 border-r border-linea p-2.5">
                  {t("Carbohidratos")}
                </th>
                <th scope="col" className="w-1/3 border-r border-linea p-2.5">
                  {t("Proteínas")}
                </th>
                <th scope="col" className="w-1/3 p-2.5">
                  {t("Grasas")}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-linea">
              {/* FILA DE PORCENTAJES */}
              <tr>
                {/* Carbohidratos % */}
                <td className="border-r border-linea bg-fondo p-1.5">
                  <div className="flex items-center justify-center">
                    <input
                      type="text"
                      value={inputCarboPct}
                      onChange={(e) => {
                        const s = e.target.value;
                        setInputCarboPct(s);
                        if (String(s).trim() !== "") aplicarPct("carbohidrato", s);
                      }}
                      onFocus={() => {
                        enfocadoCarboPct.current = true;
                      }}
                      onBlur={terminarCarboPct}
                      onKeyDown={(e) => e.key === "Enter" && terminarCarboPct()}
                      className="cifra h-9 w-20 rounded-marco bg-fondo px-2 text-center text-guia font-bold text-tinta transition-all hover:bg-fondo-sutil focus:border focus:border-acento focus:bg-fondo focus:outline-none"
                      title={t("Porcentaje de carbohidratos (editable)")}
                    />
                    <span className="cifra -ml-2 font-bold text-tinta">%</span>
                  </div>
                </td>
                {/* Proteínas % */}
                <td className="border-r border-linea bg-acento-sutil/30 p-1.5">
                  <div className="flex items-center justify-center">
                    <input
                      type="text"
                      value={inputProtPct}
                      onChange={(e) => {
                        const s = e.target.value;
                        setInputProtPct(s);
                        if (String(s).trim() !== "") aplicarPct("proteina", s);
                      }}
                      onFocus={() => {
                        enfocadoProtPct.current = true;
                      }}
                      onBlur={terminarProtPct}
                      onKeyDown={(e) => e.key === "Enter" && terminarProtPct()}
                      className="cifra h-9 w-20 rounded-marco bg-acento-sutil/40 px-2 text-center text-guia font-bold text-acento-texto transition-all hover:bg-acento-sutil focus:border focus:border-acento focus:bg-fondo focus:text-tinta focus:outline-none"
                      title={t("Porcentaje de proteínas (editable)")}
                    />
                    <span className="cifra -ml-2 font-bold text-acento-texto">%</span>
                  </div>
                </td>
                {/* Grasas % */}
                <td className="bg-fondo p-1.5">
                  <div className="flex items-center justify-center">
                    <input
                      type="text"
                      value={inputGrasaPct}
                      onChange={(e) => {
                        const s = e.target.value;
                        setInputGrasaPct(s);
                        if (String(s).trim() !== "") aplicarPct("grasa", s);
                      }}
                      onFocus={() => {
                        enfocadoGrasaPct.current = true;
                      }}
                      onBlur={terminarGrasaPct}
                      onKeyDown={(e) => e.key === "Enter" && terminarGrasaPct()}
                      className="cifra h-9 w-20 rounded-marco bg-fondo px-2 text-center text-guia font-bold text-tinta transition-all hover:bg-fondo-sutil focus:border focus:border-acento focus:bg-fondo focus:outline-none"
                      title={t("Porcentaje de grasas (editable)")}
                    />
                    <span className="cifra -ml-2 font-bold text-tinta">%</span>
                  </div>
                </td>
              </tr>

              {/* FILA DEL TOTAL (100%) */}
              <tr
                className={cn(
                  "border-b border-linea font-bold transition-colors",
                  repartoCuadra
                    ? "bg-fondo-sutil/80 text-tinta"
                    : "bg-peligro-sutil text-peligro",
                )}
              >
                <td colSpan={3} className="p-2 text-center">
                  <div className="flex items-center justify-center gap-2">
                    <span className="cifra text-menor tracking-wider">
                      {sumaReparto}%
                    </span>
                    {repartoCuadra ? (
                      <CheckCircle2 className="size-4 text-exito" />
                    ) : (
                      <span className="flex items-center gap-1 text-micro font-medium text-peligro">
                        <AlertCircle className="size-3.5" /> {t("debe sumar 100%")}
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            </tbody>

            {/* BLOQUE INFERIOR: Gramos, g/kg y Rangos de Referencia */}
            <thead>
              <tr className="border-b border-linea bg-fondo-sutil/60 text-tinta font-semibold">
                <th scope="col" className="w-1/3 border-r border-linea p-2.5">
                  {t("Gramos de macros según %")}
                </th>
                <th scope="col" className="w-1/3 border-r border-linea p-2.5">
                  {t("gr x kg de {base} (proteína)", {
                    base: baseProteina === "masa_libre_de_grasa" ? t("MLG") : t("peso"),
                  })}
                </th>
                <th scope="col" className="w-1/3 p-2.5">
                  {t("Rango de referencia")}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-linea">
              {/* FILA CARBOHIDRATOS */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                {/* Gramos */}
                <td className="border-r border-linea p-1.5 text-center">
                  <div className="flex items-center justify-center gap-1">
                    <span className="cifra h-9 px-2 text-center text-menor font-bold text-tinta">
                      {num(carboG, 0)}
                    </span>
                    <span className="text-micro font-medium text-tinta-suave">g</span>
                  </div>
                </td>
                {/* g / kg */}
                <td className="border-r border-linea p-1.5 text-center">
                  <div className="flex items-center justify-center gap-1.5">
                    <span
                      className={cn(
                        "cifra h-9 px-2 text-center text-menor font-bold",
                        fueraCarbo ? "text-peligro" : "text-tinta",
                      )}
                    >
                      {num(carboGkg, 1)}
                    </span>
                    {fueraCarbo ? (
                      <Chip tono="error" className="text-[10px] py-0 px-1">
                        {t("fuera")}
                      </Chip>
                    ) : null}
                  </div>
                </td>
                {/* Rango */}
                <td className="bg-fondo-sutil/30 p-2.5 text-center font-medium text-tinta-suave cifra text-menor">
                  {t("2.0 a 5.0")}
                </td>
              </tr>

              {/* FILA PROTEÍNAS */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors bg-acento-sutil/15">
                {/* Gramos */}
                <td className="border-r border-linea p-1.5 text-center">
                  <div className="flex items-center justify-center gap-1">
                    <span className="cifra h-9 px-2 text-center text-menor font-bold text-acento-texto">
                      {num(protG, 0)}
                    </span>
                    <span className="text-micro font-medium text-acento-texto">g</span>
                  </div>
                </td>
                {/* g / kg */}
                <td className="border-r border-linea p-1.5 text-center">
                  <div className="flex items-center justify-center gap-1.5">
                    <span
                      className={cn(
                        "cifra h-9 px-2 text-center text-menor font-bold",
                        fueraProt ? "text-peligro" : "text-acento-texto",
                      )}
                    >
                      {num(protGkg, 1)}
                    </span>
                    {fueraProt ? (
                      <Chip tono="error" className="text-[10px] py-0 px-1">
                        {t("fuera")}
                      </Chip>
                    ) : null}
                  </div>
                </td>
                {/* Rango */}
                <td className="bg-fondo-sutil/30 p-2.5 text-center font-medium text-tinta-suave cifra text-menor">
                  {t("1.8 a 3.0")}
                </td>
              </tr>

              {/* FILA GRASAS */}
              <tr className="hover:bg-fondo-sutil/40 transition-colors">
                {/* Gramos */}
                <td className="border-r border-linea p-1.5 text-center">
                  <div className="flex items-center justify-center gap-1">
                    <span className="cifra h-9 px-2 text-center text-menor font-bold text-tinta">
                      {num(grasaG, 0)}
                    </span>
                    <span className="text-micro font-medium text-tinta-suave">g</span>
                  </div>
                </td>
                {/* g / kg */}
                <td className="border-r border-linea p-1.5 text-center">
                  <div className="flex items-center justify-center gap-1.5">
                    <span
                      className={cn(
                        "cifra h-9 px-2 text-center text-menor font-bold",
                        fueraGrasa ? "text-peligro" : "text-tinta",
                      )}
                    >
                      {num(grasaGkg, 1)}
                    </span>
                    {fueraGrasa ? (
                      <Chip tono="error" className="text-[10px] py-0 px-1">
                        {t("fuera")}
                      </Chip>
                    ) : null}
                  </div>
                </td>
                {/* Rango */}
                <td className="bg-fondo-sutil/30 p-2.5 text-center font-medium text-tinta-suave cifra text-menor">
                  {t("0.5 a 1.5")}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
