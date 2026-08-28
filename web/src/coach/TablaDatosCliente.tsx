/** Tabla «DATOS DE LA CLIENTA»
 *
 *  Formato y cálculos fieles a «Calculadora del Fitness.xlsm» (hoja «Calculo bajar de peso »,
 *  rango B5:E23, celdas C6:C23, E11, B66, B101).
 *
 *  Todos los campos capturados son editables interactivamente y recalculan toda la
 *  cadena metabólica en tiempo real (TMB, mantenimiento, calorías ajustadas, IMC, etc.).
 *
 *  La paleta de estilos y colores respeta 100 % el sistema de diseño del resto de la aplicación.
 */

import { useEffect, useState } from "react";

import {
  ACTIVIDAD,
  type Composicion,
  type IdActividad,
  type Prescripcion,
  type Sexo,
} from "@/lib/calculadora";
import { num } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
import { cn } from "@/lib/utils";

interface TablaDatosClienteProps {
  comp: Composicion;
  onPeso?: (peso: number) => void;
  onPorcentajeGrasa?: (grasa: number) => void;
  estaturaCm: number;
  onEstaturaCm?: (estatura: number) => void;
  edad: number;
  onEdad?: (edad: number) => void;
  sexo: Sexo;
  onSexo?: (sexo: Sexo) => void;
  actividad: IdActividad;
  onActividad?: (act: IdActividad) => void;
  ajustePct: number;
  onAjustePct?: (ajuste: number) => void;
  prescripcion: Prescripcion;
}

export function TablaDatosCliente({
  comp,
  onPeso,
  onPorcentajeGrasa,
  estaturaCm,
  onEstaturaCm,
  edad,
  onEdad,
  sexo,
  onSexo,
  actividad,
  onActividad,
  ajustePct,
  onAjustePct,
  prescripcion,
}: TablaDatosClienteProps) {
  const { t } = useIdioma();

  // Inputs locales
  const [inputEdad, setInputEdad] = useState(String(edad));
  const [inputPeso, setInputPeso] = useState(num(comp.pesoKg, 2));
  const [inputGrasa, setInputGrasa] = useState(num(comp.porcentajeGrasa * 100, 1));
  const [inputEstatura, setInputEstatura] = useState(num(estaturaCm / 100, 2));
  const [inputAjuste, setInputAjuste] = useState(String(ajustePct));

  useEffect(() => {
    setInputEdad(String(edad));
  }, [edad]);

  useEffect(() => {
    setInputPeso(num(comp.pesoKg, 2));
  }, [comp.pesoKg]);

  useEffect(() => {
    setInputGrasa(num(comp.porcentajeGrasa * 100, 1));
  }, [comp.porcentajeGrasa]);

  useEffect(() => {
    setInputEstatura(num(estaturaCm / 100, 2));
  }, [estaturaCm]);

  useEffect(() => {
    setInputAjuste(String(ajustePct));
  }, [ajustePct]);

  // Manejadores
  const aplicarEdad = (valStr: string) => {
    const val = Math.max(10, Math.min(100, Math.round(Number(valStr) || 0)));
    if (onEdad) onEdad(val);
  };

  const aplicarPeso = (valStr: string) => {
    const val = Math.max(20, Math.min(300, Number(valStr.replace(",", ".")) || 0));
    if (onPeso && val > 0) onPeso(val);
  };

  const aplicarGrasa = (valStr: string) => {
    const val = Math.max(3, Math.min(60, Number(valStr.replace("%", "").replace(",", ".")) || 0));
    if (onPorcentajeGrasa && val > 0) onPorcentajeGrasa(val / 100);
  };

  const aplicarEstatura = (valStr: string) => {
    let val = Number(valStr.replace(",", ".")) || 0;
    if (val > 0 && val < 3) val = Math.round(val * 100);
    val = Math.max(100, Math.min(230, Math.round(val)));
    if (onEstaturaCm && val > 0) onEstaturaCm(val);
  };

  const aplicarAjuste = (valStr: string) => {
    const val = Math.max(-50, Math.min(50, Math.round(Number(valStr.replace("%", "").replace(",", ".")) || 0)));
    if (onAjustePct) onAjustePct(val);
  };

  const r = prescripcion;
  const factorActividad = ACTIVIDAD.find((a) => a.id === actividad)?.factor ?? 1.4;

  const filas = [
    {
      celda: "C6",
      rotulo: t("Edad"),
      capturado: true,
      render: () => (
        <input
          type="text"
          value={inputEdad}
          onChange={(e) => setInputEdad(e.target.value)}
          onBlur={() => aplicarEdad(inputEdad)}
          onKeyDown={(e) => e.key === "Enter" && aplicarEdad(inputEdad)}
          className="cifra h-8 w-24 rounded-marco bg-fondo px-2 text-center text-menor font-bold text-tinta transition-all hover:bg-fondo-sutil focus:border focus:border-acento focus:bg-fondo focus:outline-none"
          title={t("Edad en años (editable)")}
        />
      ),
      unidad: t("años"),
    },
    {
      celda: "C7",
      rotulo: t("Peso"),
      capturado: true,
      render: () => (
        <input
          type="text"
          value={inputPeso}
          onChange={(e) => setInputPeso(e.target.value)}
          onBlur={() => aplicarPeso(inputPeso)}
          onKeyDown={(e) => e.key === "Enter" && aplicarPeso(inputPeso)}
          className="cifra h-8 w-24 rounded-marco bg-fondo px-2 text-center text-menor font-bold text-tinta transition-all hover:bg-fondo-sutil focus:border focus:border-acento focus:bg-fondo focus:outline-none"
          title={t("Peso en kg (editable)")}
        />
      ),
      unidad: "kg",
    },
    {
      celda: "C8",
      rotulo: t("% grasa estimado"),
      capturado: true,
      render: () => (
        <div className="flex items-center justify-center gap-0.5">
          <input
            type="text"
            value={inputGrasa}
            onChange={(e) => setInputGrasa(e.target.value)}
            onBlur={() => aplicarGrasa(inputGrasa)}
            onKeyDown={(e) => e.key === "Enter" && aplicarGrasa(inputGrasa)}
            className="cifra h-8 w-20 rounded-marco bg-fondo px-2 text-center text-menor font-bold text-tinta transition-all hover:bg-fondo-sutil focus:border focus:border-acento focus:bg-fondo focus:outline-none"
            title={t("Porcentaje de grasa estimado (editable)")}
          />
          <span className="text-micro font-medium text-tinta-suave">%</span>
        </div>
      ),
      unidad: "",
    },
    {
      celda: "C9",
      rotulo: t("Estatura"),
      capturado: true,
      render: () => (
        <input
          type="text"
          value={inputEstatura}
          onChange={(e) => setInputEstatura(e.target.value)}
          onBlur={() => aplicarEstatura(inputEstatura)}
          onKeyDown={(e) => e.key === "Enter" && aplicarEstatura(inputEstatura)}
          className="cifra h-8 w-24 rounded-marco bg-fondo px-2 text-center text-menor font-bold text-tinta transition-all hover:bg-fondo-sutil focus:border focus:border-acento focus:bg-fondo focus:outline-none"
          title={t("Estatura en metros (ej. 1.65, editable)")}
        />
      ),
      unidad: "mts",
    },
    {
      celda: "C10",
      rotulo: t("Género"),
      capturado: true,
      render: () => (
        <select
          value={sexo}
          onChange={(e) => onSexo && onSexo(e.target.value as Sexo)}
          className="h-8 rounded-marco border border-linea bg-fondo px-2 text-center text-menor font-bold text-tinta hover:bg-fondo-sutil focus:border-acento focus:outline-none cursor-pointer"
        >
          <option value="femenino">{t("Femenino")}</option>
          <option value="masculino">{t("Masculino")}</option>
        </select>
      ),
      unidad: "",
    },
    {
      celda: "C11",
      rotulo: t("IMC"),
      capturado: false,
      render: () => <span className="cifra font-bold">{num(comp.imc, 2)}</span>,
      unidad: "",
    },
    {
      celda: "E11",
      rotulo: t("Clasificación"),
      capturado: false,
      render: () => (
        <span className="font-bold text-acento-texto">{comp.clasificacionImc}</span>
      ),
      unidad: "",
    },
    {
      celda: "C12",
      rotulo: t("Diferencia peso-estatura"),
      capturado: false,
      render: () => (
        <span className="cifra font-bold">{num(comp.diferenciaPesoEstaturaKg, 2)}</span>
      ),
      unidad: "kg",
    },
    {
      celda: "C13",
      rotulo: t("Masa libre de grasa (MLG)"),
      capturado: false,
      render: () => (
        <span className="cifra font-bold">{num(comp.masaLibreDeGrasaKg, 2)}</span>
      ),
      unidad: "kg",
    },
    {
      celda: "C14",
      rotulo: t("Masa grasa (MG)"),
      capturado: false,
      render: () => (
        <span className="cifra font-bold">{num(comp.masaGrasaKg, 2)}</span>
      ),
      unidad: "kg",
    },
    {
      celda: "C16",
      rotulo: t("Multiplicador de actividad"),
      capturado: true,
      render: () => (
        <select
          value={actividad}
          onChange={(e) => onActividad && onActividad(e.target.value as IdActividad)}
          className="h-8 rounded-marco border border-linea bg-fondo px-2 text-center text-menor font-bold text-tinta hover:bg-fondo-sutil focus:border-acento focus:outline-none cursor-pointer"
        >
          {ACTIVIDAD.map((a) => (
            <option key={a.id} value={a.id}>
              {a.factor} ({t(a.rotulo)})
            </option>
          ))}
        </select>
      ),
      unidad: "",
    },
    {
      celda: "C17",
      rotulo: t("% de ajuste calórico"),
      capturado: true,
      render: () => (
        <div className="flex items-center justify-center gap-0.5">
          <input
            type="text"
            value={inputAjuste}
            onChange={(e) => setInputAjuste(e.target.value)}
            onBlur={() => aplicarAjuste(inputAjuste)}
            onKeyDown={(e) => e.key === "Enter" && aplicarAjuste(inputAjuste)}
            className="cifra h-8 w-20 rounded-marco bg-fondo px-2 text-center text-menor font-bold text-tinta transition-all hover:bg-fondo-sutil focus:border focus:border-acento focus:bg-fondo focus:outline-none"
            title={t("% de ajuste calórico (negativo déficit, positivo superávit)")}
          />
          <span className="text-micro font-medium text-tinta-suave">%</span>
        </div>
      ),
      unidad: "",
    },
    {
      celda: "C18",
      rotulo: t("Tasa metabólica basal"),
      capturado: false,
      render: () => <span className="cifra font-bold">{num(r.tmbKcal, 2)}</span>,
      unidad: "kcal",
    },
    {
      celda: "C19",
      rotulo: t("Calorías de mantenimiento"),
      capturado: false,
      render: () => (
        <span className="cifra font-bold">{num(r.energia.mantenimientoKcal, 2)}</span>
      ),
      unidad: "kcal",
    },
    {
      celda: "C20",
      rotulo: t("Calorías ajustadas"),
      capturado: false,
      render: () => (
        <span className="cifra font-bold text-acento-texto">{num(r.energia.ajustadasKcal, 2)}</span>
      ),
      unidad: "kcal",
    },
    {
      celda: "C21",
      rotulo: t("Calorías de ajuste diario"),
      capturado: false,
      render: () => (
        <span
          className={cn(
            "cifra font-bold",
            r.energia.ajusteDiarioKcal < 0 ? "text-exito" : "text-tinta",
          )}
        >
          {num(r.energia.ajusteDiarioKcal, 2)}
        </span>
      ),
      unidad: "kcal",
    },
    {
      celda: "C22",
      rotulo: t("Calorías semanales según ajuste"),
      capturado: false,
      render: () => (
        <span className="cifra font-bold">{num(r.energia.semanalesKcal, 2)}</span>
      ),
      unidad: "kcal",
    },
    {
      celda: "C23",
      rotulo: t("Calorías de ajuste semanal"),
      capturado: false,
      render: () => (
        <span
          className={cn(
            "cifra font-bold",
            r.energia.ajusteSemanalKcal < 0 ? "text-exito" : "text-tinta",
          )}
        >
          {num(r.energia.ajusteSemanalKcal, 2)}
        </span>
      ),
      unidad: "kcal",
    },
  ];

  return (
    <section className="flex flex-col gap-3">
      {/* Contenedor principal de la tabla */}
      <div className="overflow-hidden rounded-marco border border-linea bg-fondo shadow-xs">
        {/* Cabecera */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-linea bg-tinta px-4 py-3 text-fondo dark:bg-tinta-suave/20 dark:text-tinta">
          <div className="flex items-center gap-2">
            <h3 className="cifra text-menor font-bold tracking-wider uppercase">
              {t("DATOS DE LA CLIENTA")}
            </h3>
            <span className="cifra text-micro opacity-60">B5:E23</span>
          </div>
          <span className="text-micro opacity-80">
            {t("TMB: {tmb} kcal · Mant: {mant} kcal · Factor: ×{factor}", {
              tmb: num(r.tmbKcal, 0),
              mant: num(r.energia.mantenimientoKcal, 0),
              factor: factorActividad,
            })}
          </span>
        </div>

        {/* Tabla de datos */}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-menor">
            <tbody className="divide-y divide-linea">
              {filas.map((f) => (
                <tr
                  key={f.celda}
                  className={cn(
                    "hover:bg-fondo-sutil/40 transition-colors",
                    f.capturado ? "bg-fondo" : "bg-fondo-sutil/20",
                  )}
                >
                  {/* Código de celda */}
                  <td className="w-12 border-r border-linea bg-fondo-sutil/60 p-2.5 text-center cifra text-micro font-semibold text-tinta-suave">
                    {f.celda}
                  </td>
                  {/* Rótulo */}
                  <th
                    scope="row"
                    className="w-1/2 border-r border-linea p-2.5 font-medium text-tinta"
                  >
                    {f.rotulo}
                  </th>
                  {/* Valor / Input */}
                  <td className="p-1.5 text-center">{f.render()}</td>
                  {/* Unidad */}
                  <td className="w-14 border-l border-linea bg-fondo-sutil/30 p-2.5 text-center font-medium text-tinta-suave text-micro">
                    {f.unidad}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
