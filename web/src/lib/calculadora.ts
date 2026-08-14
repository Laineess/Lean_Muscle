/** Calculadora metabólica — espejo de `app/dominio/calculadora.py`.
 *
 *  Existe para que el constructor recalcule al vuelo mientras la coach mueve los campos.
 *  **El cálculo que manda es el del servidor**: al conectar la API, esta pantalla pedirá el
 *  resultado y este archivo queda solo para la vista previa optimista.
 *
 *  Fórmulas y constantes salen de `Calculadora del Fitness.xlsm`, hoja «Calculo bajar de
 *  peso». Cada una lleva su celda. Cambiar un número aquí cambia el plan de todas las
 *  alumnas, así que no se toca sin tocar también el módulo de Python y sus pruebas.
 */

/* ------------------------------------------------------ Constantes de la hoja --- */

// Ecuación de tasa metabólica basal, celdas B87 y B88.
const COEF_MLG = 13.587;
const COEF_MG = 9.613;
const COEF_SEXO_MASCULINO = 198;
const COEF_EDAD = 3.351;
const COEF_BASE = 674;

/** Celda C19: el 1.1 es el efecto térmico de los alimentos, aplicado plano. */
const FACTOR_TERMICO = 1.1;
/** Celda H17: kcal de superávit por kilo de peso ganado. */
const KCAL_POR_KILO_GANADO = 8400;

// Composición del peso que se pierde, celdas H105:H107.
const FRACCION_GRASA_PURA = 0.87;
const FRACCION_MLG_PERDIDA = 0.2;
const FRACCION_PROTEINA_EN_MLG = 0.3;

// Celda H7: reducción semanal recomendada, entre 0.5 % y 1.0 % del peso.
const REDUCCION_MIN = 0.005;
const REDUCCION_MAX = 0.01;

export const MAX_DIAS_REFEED = 2;

export type Sexo = "masculino" | "femenino";
export type BaseProteina = "peso_total" | "masa_libre_de_grasa";
export type RelacionGanancia = "2:1" | "1:1";
export type Macro = "carbohidrato" | "proteina" | "grasa";

/** Lista desplegable de la celda C16. */
export const ACTIVIDAD = [
  { id: "muy_poco_activo", rotulo: "Muy poco activa", factor: 1.2 },
  { id: "poco_activo", rotulo: "Poco activa", factor: 1.3 },
  { id: "activo", rotulo: "Activa", factor: 1.4 },
  { id: "muy_activo", rotulo: "Muy activa", factor: 1.5 },
  { id: "intenso", rotulo: "Intensa", factor: 1.6 },
  { id: "muy_intenso", rotulo: "Muy intensa", factor: 1.7 },
  { id: "atleta", rotulo: "Atleta", factor: 1.8 },
  { id: "atleta_elite", rotulo: "Atleta de élite", factor: 1.9 },
] as const;

export type IdActividad = (typeof ACTIVIDAD)[number]["id"];

/** Rangos de referencia en g/kg, celdas E30:E32. Avisan, no bloquean. */
export const RANGO_GKG: Record<Macro, [number, number]> = {
  carbohidrato: [2.0, 5.0],
  proteina: [1.8, 3.0],
  grasa: [0.5, 1.5],
};

export const ROTULO_MACRO: Record<Macro, string> = {
  carbohidrato: "Carbohidratos",
  proteina: "Proteína",
  grasa: "Grasa",
};

const KCAL_POR_GRAMO: Record<Macro, number> = { carbohidrato: 4, proteina: 4, grasa: 9 };

export function factorDe(id: IdActividad): number {
  return ACTIVIDAD.find((a) => a.id === id)?.factor ?? 1.4;
}

/* ------------------------------------------------------- Composición corporal --- */

/** Tabla E65:F84 de la hoja. */
export function clasificarImc(imc: number): string {
  if (imc < 18) return "Muy delgado";
  if (imc < 21) return "Delgado";
  if (imc < 26) return "Normal";
  if (imc < 30) return "Sobre peso";
  return "Obesidad";
}

export interface Composicion {
  pesoKg: number;
  porcentajeGrasa: number;
  masaGrasaKg: number;
  masaLibreDeGrasaKg: number;
  imc: number;
  clasificacionImc: string;
  pesoIdealBrocaKg: number;
  diferenciaPesoEstaturaKg: number;
}

export function composicion(pesoKg: number, porcentajeGrasa: number, estaturaCm: number): Composicion {
  const masaGrasaKg = pesoKg * porcentajeGrasa; // C14
  const metros = estaturaCm / 100;
  const imc = pesoKg / (metros * metros); // C11
  return {
    pesoKg,
    porcentajeGrasa,
    masaGrasaKg,
    masaLibreDeGrasaKg: pesoKg - masaGrasaKg, // C13
    imc,
    clasificacionImc: clasificarImc(imc),
    pesoIdealBrocaKg: estaturaCm - 100, // B66
    diferenciaPesoEstaturaKg: pesoKg - (estaturaCm - 100), // C12
  };
}

/* --------------------------------------------------------------------- Energía --- */

/** Celdas B87/B88. La única diferencia entre sexos es el término de 198 kcal. */
export function tmb(comp: Composicion, sexo: Sexo, edad: number): number {
  const terminoSexo = sexo === "masculino" ? COEF_SEXO_MASCULINO : 0;
  return (
    COEF_MLG * comp.masaLibreDeGrasaKg +
    COEF_MG * comp.masaGrasaKg +
    terminoSexo -
    COEF_EDAD * edad +
    COEF_BASE
  );
}

export interface Energia {
  mantenimientoKcal: number;
  ajustadasKcal: number;
  ajusteDiarioKcal: number;
  ajusteSemanalKcal: number;
  semanalesKcal: number;
  esDeficit: boolean;
}

/** Celdas C19 a C23. `porcentajeAjuste` con signo: −0.28 es déficit del 28 %. */
export function energia(tasaBasal: number, actividad: IdActividad, porcentajeAjuste: number): Energia {
  const mantenimiento = tasaBasal * factorDe(actividad) * FACTOR_TERMICO;
  const ajustadas = mantenimiento + mantenimiento * porcentajeAjuste;
  const diario = ajustadas - mantenimiento;
  return {
    mantenimientoKcal: mantenimiento,
    ajustadasKcal: ajustadas,
    ajusteDiarioKcal: diario,
    ajusteSemanalKcal: diario * 7,
    semanalesKcal: ajustadas * 7,
    esDeficit: diario < 0,
  };
}

/* ---------------------------------------------------------------------- Macros --- */

export type Reparto = Record<Macro, number>;
export type Macros = Record<Macro, number>;

/** Celdas B93:B95. */
export function macros(kcalAjustadas: number, reparto: Reparto): Macros {
  return {
    carbohidrato: (kcalAjustadas * reparto.carbohidrato) / KCAL_POR_GRAMO.carbohidrato,
    proteina: (kcalAjustadas * reparto.proteina) / KCAL_POR_GRAMO.proteina,
    grasa: (kcalAjustadas * reparto.grasa) / KCAL_POR_GRAMO.grasa,
  };
}

export function kcalDe(macro: Macro, gramos: number): number {
  return gramos * KCAL_POR_GRAMO[macro];
}

/** Celdas C30:C32. La proteína se expresa contra peso total o contra masa libre de grasa. */
export function gramosPorKilo(m: Macros, comp: Composicion, base: BaseProteina): Macros {
  const referencia = base === "peso_total" ? comp.pesoKg : comp.masaLibreDeGrasaKg;
  return {
    carbohidrato: m.carbohidrato / comp.pesoKg,
    proteina: m.proteina / referencia,
    grasa: m.grasa / comp.pesoKg,
  };
}

export function fueraDeRango(gkg: Macros): Macro[] {
  return (Object.keys(RANGO_GKG) as Macro[]).filter((m) => {
    const [min, max] = RANGO_GKG[m];
    return gkg[m] < min || gkg[m] > max;
  });
}

/* --------------------------------------------------------------------- Refeeds --- */

/** Celdas B72:B75. Con 1 día a mantenimiento y 26 % los otros seis, el promedio cae a 22.29 %. */
export function deficitPromedioSemanal(
  porcentajeDiaBajo: number,
  diasRefeed: number,
  porcentajeDiaRefeed = 0,
): number {
  const diasBajos = 7 - diasRefeed;
  return (porcentajeDiaBajo * diasBajos + porcentajeDiaRefeed * diasRefeed) / 7;
}

/* ----------------------------------------------------------------- Proyecciones --- */

export interface ProyeccionPerdida {
  kgGrasaPorBajar: number;
  kgMlgQueSePierden: number;
  kgTotalesPorBajar: number;
  kcalTotales: number;
  perdidaSemanalKg: number;
  porcentajeSemanal: number;
  diasEstimados: number;
  recomendadoMinKg: number;
  recomendadoMaxKg: number;
  dentroDeLoRecomendado: boolean;
}

/** Celdas H105:H117. **Solo la ve la coach**: asume adherencia perfecta. */
export function proyectarPerdida(
  comp: Composicion,
  porcentajeObjetivo: number,
  e: Energia,
): ProyeccionPerdida | null {
  if (!e.esDeficit || porcentajeObjetivo >= comp.porcentajeGrasa) return null;

  const grasaEnObjetivo = (porcentajeObjetivo * comp.masaGrasaKg) / comp.porcentajeGrasa; // H109
  const grasaPorBajar = comp.masaGrasaKg - grasaEnObjetivo; // H108

  // El modelo no supone que todo lo perdido sea grasa: por cada kilo se pierden 0.2 de MLG.
  const grasaPura = grasaPorBajar * FRACCION_GRASA_PURA;
  const mlgPerdida = grasaPorBajar * FRACCION_MLG_PERDIDA;
  const proteinaPura = mlgPerdida * FRACCION_PROTEINA_EN_MLG;

  const totales = grasaPorBajar + mlgPerdida; // H6
  const kcalTotales = (grasaPura * 9 + proteinaPura * 4) * 1000; // H113

  const perdidaSemanal = (-e.ajusteSemanalKcal * totales) / kcalTotales; // H117
  const minimo = comp.pesoKg * REDUCCION_MIN;
  const maximo = comp.pesoKg * REDUCCION_MAX;

  return {
    kgGrasaPorBajar: grasaPorBajar,
    kgMlgQueSePierden: mlgPerdida,
    kgTotalesPorBajar: totales,
    kcalTotales,
    perdidaSemanalKg: perdidaSemanal,
    porcentajeSemanal: perdidaSemanal / comp.pesoKg,
    diasEstimados: kcalTotales / -e.ajusteDiarioKcal, // H10
    recomendadoMinKg: minimo,
    recomendadoMaxKg: maximo,
    dentroDeLoRecomendado: perdidaSemanal >= minimo && perdidaSemanal <= maximo,
  };
}

export interface ProyeccionGanancia {
  aumentoSemanalKg: number;
  musculoSemanalKg: number;
  porcentajeMensual: number;
  semanas: number;
  aumentoTotalKg: number;
  musculoTotalKg: number;
  grasaTotalKg: number;
}

/** Celdas G16:J23. */
export function proyectarGanancia(
  comp: Composicion,
  e: Energia,
  semanas: number,
  relacion: RelacionGanancia = "2:1",
): ProyeccionGanancia | null {
  if (e.esDeficit) return null;
  const proporcion = relacion === "1:1" ? 0.5 : 0.33;
  const semanal = e.ajusteSemanalKcal / KCAL_POR_KILO_GANADO;
  const musculoSemanal = semanal * proporcion;
  const total = semanal * semanas;
  const musculoTotal = musculoSemanal * semanas;
  return {
    aumentoSemanalKg: semanal,
    musculoSemanalKg: musculoSemanal,
    porcentajeMensual: (semanal / comp.pesoKg) * 4,
    semanas,
    aumentoTotalKg: total,
    musculoTotalKg: musculoTotal,
    grasaTotalKg: total - musculoTotal,
  };
}

/* -------------------------------------------------------------------- Fachada --- */

export interface EntradasCalculadora {
  pesoKg: number;
  porcentajeGrasa: number;
  estaturaCm: number;
  edad: number;
  sexo: Sexo;
  actividad: IdActividad;
  porcentajeAjuste: number;
  reparto: Reparto;
  baseProteina: BaseProteina;
  diasRefeed: number;
  porcentajeDiaRefeed: number;
  porcentajeGrasaObjetivo: number;
  relacionGanancia: RelacionGanancia;
  semanasGanancia: number;
}

export interface Prescripcion {
  composicion: Composicion;
  tmbKcal: number;
  energia: Energia;
  macros: Macros;
  gramosPorKilo: Macros;
  avisosDeRango: Macro[];
  deficitPromedioSemanal: number | null;
  proyeccionPerdida: ProyeccionPerdida | null;
  proyeccionGanancia: ProyeccionGanancia | null;
}

export function calcular(e: EntradasCalculadora): Prescripcion {
  const comp = composicion(e.pesoKg, e.porcentajeGrasa, e.estaturaCm);
  const tasaBasal = tmb(comp, e.sexo, e.edad);
  const energ = energia(tasaBasal, e.actividad, e.porcentajeAjuste);
  const m = macros(energ.ajustadasKcal, e.reparto);
  const gkg = gramosPorKilo(m, comp, e.baseProteina);

  return {
    composicion: comp,
    tmbKcal: tasaBasal,
    energia: energ,
    macros: m,
    gramosPorKilo: gkg,
    avisosDeRango: fueraDeRango(gkg),
    deficitPromedioSemanal: e.diasRefeed
      ? deficitPromedioSemanal(Math.abs(e.porcentajeAjuste), e.diasRefeed, e.porcentajeDiaRefeed)
      : null,
    proyeccionPerdida: proyectarPerdida(comp, e.porcentajeGrasaObjetivo, energ),
    proyeccionGanancia: proyectarGanancia(comp, energ, e.semanasGanancia, e.relacionGanancia),
  };
}
