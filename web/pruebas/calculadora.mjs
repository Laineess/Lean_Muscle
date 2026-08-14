/* Verifica que el motor de la interfaz dé los mismos números que la hoja de la clienta y
 * que el módulo de Python. Si estos dos se separan, la coach ve un plan en pantalla y otro
 * guardado.
 *
 * Caso de referencia: el capturado en `Calculadora del Fitness.xlsm`.
 *   Edad 31 · Peso 102.4 kg · 30 % de grasa · 1.78 m · Masculino
 *   Actividad 1.4 · Ajuste −28 % · Macros 50/28/22 · Objetivo 15 %
 *
 *   node pruebas/calculadora.mjs
 */

import { build } from "esbuild";
import { readFileSync, unlinkSync } from "node:fs";
import { pathToFileURL } from "node:url";

const SALIDA = new URL("./.calculadora.compilada.mjs", import.meta.url);

await build({
  entryPoints: [new URL("../src/lib/calculadora.ts", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")],
  outfile: SALIDA.pathname.replace(/^\/([A-Za-z]:)/, "$1"),
  format: "esm",
  bundle: false,
  logLevel: "error",
});

const C = await import(pathToFileURL(SALIDA.pathname.replace(/^\/([A-Za-z]:)/, "$1")).href);

const ENTRADA = {
  pesoKg: 102.4,
  porcentajeGrasa: 0.3,
  estaturaCm: 178,
  edad: 31,
  sexo: "masculino",
  actividad: "activo",
  porcentajeAjuste: -0.28,
  reparto: { carbohidrato: 0.5, proteina: 0.28, grasa: 0.22 },
  baseProteina: "masa_libre_de_grasa",
  diasRefeed: 1,
  porcentajeDiaRefeed: 0,
  porcentajeGrasaObjetivo: 0.15,
  relacionGanancia: "2:1",
  semanasGanancia: 20,
};

const r = C.calcular(ENTRADA);

const casos = [
  ["C13 masa libre de grasa", r.composicion.masaLibreDeGrasaKg, 71.68],
  ["C14 masa grasa", r.composicion.masaGrasaKg, 30.72],
  ["C11 IMC", r.composicion.imc, 32.319151622],
  ["E11 clasificación", r.composicion.clasificacionImc, "Obesidad"],
  ["C12 diferencia peso-estatura", r.composicion.diferenciaPesoEstaturaKg, 24.4],
  ["B87 TMB", r.tmbKcal, 2037.34652],
  ["C19 mantenimiento", r.energia.mantenimientoKcal, 3137.5136408],
  ["C20 calorías ajustadas", r.energia.ajustadasKcal, 2259.009821376],
  ["C21 ajuste diario", r.energia.ajusteDiarioKcal, -878.503819424],
  ["C23 ajuste semanal", r.energia.ajusteSemanalKcal, -6149.526735968],
  ["B93 carbohidratos g", r.macros.carbohidrato, 282.376227672],
  ["B94 proteína g", r.macros.proteina, 158.130687496],
  ["B95 grasa g", r.macros.grasa, 55.220240078],
  ["C30 carbos g/kg", r.gramosPorKilo.carbohidrato, 2.7575803484],
  ["C80 proteína g/kg MLG", r.gramosPorKilo.proteina, 2.2060642787],
  ["C32 grasa g/kg", r.gramosPorKilo.grasa, 0.539260157],
  ["H108 grasa por bajar", r.proyeccionPerdida.kgGrasaPorBajar, 15.36],
  ["H106 MLG perdida", r.proyeccionPerdida.kgMlgQueSePierden, 3.072],
  ["H6 total por bajar", r.proyeccionPerdida.kgTotalesPorBajar, 18.432],
  ["H113 calorías totales", r.proyeccionPerdida.kcalTotales, 123955.2],
  ["H8 pérdida semanal", r.proyeccionPerdida.perdidaSemanalKg, 0.9144277674],
  ["H10 días estimados", r.proyeccionPerdida.diasEstimados, 141.0980775033],
  // En la hoja el día bajo (G14=26) es un campo aparte del ajuste (C17=−28); aquí el día
  // bajo ES el ajuste capturado, así que con −28 % y 1 refeed el promedio es 24 %.
  ["déficit promedio, 1 refeed", r.deficitPromedioSemanal, 0.24],
  ["B74 con día bajo al 26 %", C.deficitPromedioSemanal(26, 1), 22.285714285714],
  ["B75 con día bajo al 26 %", C.deficitPromedioSemanal(26, 2), 18.571428571428],
];

let fallos = 0;
for (const [rotulo, obtenido, esperado] of casos) {
  const ok =
    typeof esperado === "string"
      ? obtenido === esperado
      : Math.abs(obtenido - esperado) <= Math.max(Math.abs(esperado) * 1e-9, 1e-6);
  if (!ok) fallos++;
  console.log(`${ok ? "OK    " : "FALLA "} ${rotulo.padEnd(30)} ${obtenido}  (hoja: ${esperado})`);
}

const deMacros = r.macros.carbohidrato * 4 + r.macros.proteina * 4 + r.macros.grasa * 9;
const cuadra = Math.abs(deMacros - r.energia.ajustadasKcal) < 1e-9;
if (!cuadra) fallos++;
console.log(`${cuadra ? "OK    " : "FALLA "} los macros cuadran con las calorías`);

// Los ocho niveles de actividad de la hoja tienen que estar completos.
const factores = C.ACTIVIDAD.map((a) => a.factor).join(",");
const esperados = "1.2,1.3,1.4,1.5,1.6,1.7,1.8,1.9";
if (factores !== esperados) {
  fallos++;
  console.log(`FALLA  niveles de actividad: ${factores}`);
} else {
  console.log("OK     los ocho niveles de actividad de la hoja");
}

unlinkSync(SALIDA.pathname.replace(/^\/([A-Za-z]:)/, "$1"));
console.log(fallos ? `\n${fallos} desviación(es) contra la hoja` : "\nEl motor de la interfaz coincide con la hoja");
process.exit(fallos ? 1 : 0);
