/* Verifica que el motor JS de la maqueta dé los mismos números que la hoja y que el
   módulo de Python. Si estos dos se separan, la coach ve un plan en pantalla y otro
   guardado. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const raiz = process.argv[2];
const ctx = { window: {}, console, Math, Object, Number, String, Array, Date, parseInt, parseFloat };
ctx.window = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(raiz, "js/calculadora.js"), "utf8"), ctx, {
  filename: "calculadora.js",
});

const C = ctx.LM.calc;

// Caso de referencia capturado en Calculadora del Fitness.xlsm.
const ENTRADA = {
  peso_kg: 102.4,
  porcentaje_grasa: 0.3,
  estatura_cm: 178,
  edad: 31,
  sexo: "masculino",
  actividad: "activo",
  porcentaje_ajuste: -0.28,
  reparto: { carbohidrato: 0.5, proteina: 0.28, grasa: 0.22 },
  base_proteina: "masa_libre_de_grasa",
  dias_refeed: 1,
  porcentaje_dia_refeed: 0,
  porcentaje_grasa_objetivo: 0.15,
};

const r = C.calcular(ENTRADA);

const casos = [
  ["C13 masa libre de grasa", r.composicion.masa_libre_de_grasa_kg, 71.68],
  ["C14 masa grasa", r.composicion.masa_grasa_kg, 30.72],
  ["C11 IMC", r.composicion.imc, 32.319151622],
  ["C12 diferencia peso-estatura", r.composicion.diferencia_peso_estatura_kg, 24.4],
  ["B87 TMB", r.tmb_kcal, 2037.34652],
  ["C19 mantenimiento", r.energia.mantenimiento_kcal, 3137.5136408],
  ["C20 calorías ajustadas", r.energia.ajustadas_kcal, 2259.009821376],
  ["C21 ajuste diario", r.energia.ajuste_diario_kcal, -878.503819424],
  ["C22 calorías semanales", r.energia.semanales_kcal, 15813.068749632],
  ["C23 ajuste semanal", r.energia.ajuste_semanal_kcal, -6149.526735968],
  ["B93 carbohidratos g", r.macros.carbohidrato_g, 282.376227672],
  ["B94 proteína g", r.macros.proteina_g, 158.130687496],
  ["B95 grasa g", r.macros.grasa_g, 55.220240078],
  ["C30 carbos g/kg", r.gramos_por_kilo.carbohidrato, 2.7575803484],
  ["C80 proteína g/kg MLG", r.gramos_por_kilo.proteina, 2.2060642787],
  ["C32 grasa g/kg", r.gramos_por_kilo.grasa, 0.539260157],
  // En la hoja el déficit del día bajo (G14=26) es un campo aparte del ajuste calórico
  // (C17=−28), y nada obliga a que cuadren. Aquí el día bajo ES el ajuste capturado, así
  // que con −28 % y 1 refeed a mantenimiento el promedio semanal es 24 %.
  ["déficit promedio, 1 refeed", r.deficit_promedio_semanal, 0.24],
  // Reproducción literal del escenario de la hoja, con su 26 % de día bajo.
  ["B74 con día bajo al 26 %", C.deficitPromedioSemanal(26, 1), 22.285714285714],
  ["B75 con día bajo al 26 %", C.deficitPromedioSemanal(26, 2), 18.571428571428],
  ["H108 grasa por bajar", r.proyeccion_perdida.kg_grasa_por_bajar, 15.36],
  ["H106 MLG perdida", r.proyeccion_perdida.kg_mlg_que_se_pierden, 3.072],
  ["H6 total por bajar", r.proyeccion_perdida.kg_totales_por_bajar, 18.432],
  ["H113 calorías totales", r.proyeccion_perdida.kcal_totales, 123955.2],
  ["H8 pérdida semanal", r.proyeccion_perdida.perdida_semanal_kg, 0.9144277674],
  ["H9 % semanal", r.proyeccion_perdida.porcentaje_semanal, 0.0089299587],
  ["H10 días estimados", r.proyeccion_perdida.dias_estimados, 141.0980775033],
];

let fallos = 0;
for (const [rotulo, obtenido, esperado] of casos) {
  const tolerancia = Math.max(Math.abs(esperado) * 1e-9, 1e-6);
  const ok = Math.abs(obtenido - esperado) <= tolerancia;
  if (!ok) fallos++;
  console.log(`${ok ? "OK    " : "FALLA "} ${rotulo.padEnd(32)} ${obtenido}  (hoja: ${esperado})`);
}

// Los gramos tienen que reconstruir exactamente las calorías del objetivo.
const deMacros = r.macros.carbohidrato_g * 4 + r.macros.proteina_g * 4 + r.macros.grasa_g * 9;
const cuadra = Math.abs(deMacros - r.energia.ajustadas_kcal) < 1e-9;
if (!cuadra) fallos++;
console.log(`${cuadra ? "OK    " : "FALLA "} los macros cuadran con las calorías`);

console.log(fallos ? `\n${fallos} desviación(es) contra la hoja` : "\nEl motor JS coincide con la hoja");
process.exit(fallos ? 1 : 0);
