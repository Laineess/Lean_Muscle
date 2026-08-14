/* Prueba de humo de las maquetas.

   Carga los archivos de un frente en Node con un DOM mínimo y renderiza todas sus vistas,
   incluidas las sub-rutas. No juzga diseño: comprueba que ninguna vista lance al
   construirse y que no se cuele un `undefined` en pantalla.

   Uso:  node pruebas/maquetas/humo.js ui alumna
         node pruebas/maquetas/humo.js ui coach
*/
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const raiz = process.argv[2] || "ui";
const frente = process.argv[3] || "alumna";

const elemento = () => ({
  innerHTML: "", textContent: "", value: "", className: "", style: {}, dataset: {},
  classList: { toggle() {}, add() {}, remove() {}, contains: () => false },
  setAttribute() {}, removeAttribute() {}, getAttribute: () => null,
  addEventListener() {}, appendChild() {}, remove() {},
  querySelectorAll: () => [], parentElement: null,
  disabled: false, checked: false, files: [],
});

const doc = {
  readyState: "complete",
  querySelector: () => elemento(),
  querySelectorAll: () => [],
  getElementById: () => elemento(),
  createElement: () => elemento(),
  addEventListener() {},
  removeEventListener() {},
  body: elemento(),
};

const ctx = {
  window: {}, document: doc, location: { hash: "" }, history: { back() {} },
  setTimeout, clearTimeout, console,
  Date, Math, JSON, Number, String, Object, Array, parseInt, parseFloat, isNaN,
};
ctx.window = ctx;
ctx.globalThis = ctx;
vm.createContext(ctx);

const archivos = [
  "js/nucleo.js",
  "js/datos.js",
  "js/calculadora.js",
  ...fs.readdirSync(path.join(raiz, "js", frente)).map((f) => `js/${frente}/${f}`),
];

for (const rel of archivos) {
  vm.runInContext(fs.readFileSync(path.join(raiz, rel), "utf8"), ctx, { filename: rel });
}

const LM = ctx.LM;

// Object.create(null): sin esto, una vista llamada "constructor" resuelve contra
// Object.prototype y el mapa devuelve una función en lugar de undefined.
const ARGS = Object.assign(Object.create(null), {
  chequeo: [[], ["peso"], ["medidas"], ["fotos"], ["revision"]],
  plan: [[], ["nutricion"], ["entrenamiento"]],
  cuenta: [[], ["pagos"], ["privacidad"]],
  legal: [["privacidad"]],
  alumna: [
    ["01JAL0001"], ["01JAL0001", "chequeo"], ["01JAL0001", "salud"],
    ["01JAL0001", "planes"], ["01JAL0001", "mensajes"],
  ],
  validar: [["01JCHK0004"], ["01JCHK0102"]],
  constructor: [["01JAL0001"], ["01JAL0001", "entrenamiento"]],
  biblioteca: [[], ["ejercicios"], ["alimentos"], ["plantillas"]],
  cumplimiento: [[], ["bitacora"], ["arco"], ["retencion"]],
});

let fallos = 0;
for (const nombre of Object.keys(LM.vistas).filter((k) => !k.startsWith("_"))) {
  for (const args of ARGS[nombre] || [[]]) {
    const etiqueta = `${nombre}(${args.join(",")})`;
    try {
      const salida = LM.vistas[nombre](...args);
      if (typeof salida !== "string" || salida.length < 40) {
        console.log(`VACÍA  ${etiqueta} -> ${typeof salida}`);
        fallos++;
      } else if (/undefined|\[object Object\]|NaN/.test(salida)) {
        const m = salida.match(/.{0,60}(undefined|\[object Object\]|NaN).{0,60}/);
        console.log(`SUCIA  ${etiqueta} -> …${m[0]}…`);
        fallos++;
      } else {
        console.log(`OK     ${etiqueta} ${salida.length} bytes`);
      }
    } catch (e) {
      console.log(`FALLA  ${etiqueta} -> ${e.message}`);
      fallos++;
    }
  }
}

console.log(fallos ? `\n${fallos} problema(s) en ${frente}` : `\nTodas las vistas de ${frente} renderizan`);
process.exit(fallos ? 1 : 0);
