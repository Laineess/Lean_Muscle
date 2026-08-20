/** Calculadora metabólica — espejo de `app/dominio/calculadora.py`.
 *
 *  Existe para que el constructor recalcule al vuelo mientras la coach mueve los campos.
 *  **El cálculo que manda es el del servidor**: al conectar la API, esta pantalla pedirá el
 *  resultado y este archivo queda solo para la vista previa optimista.
 *
 *  Fórmulas y constantes salen de `Calculadora del Fitness.xlsm`, hoja «Calculo bajar de
 *  peso». Cambiar un número aquí cambia el plan de todas las
 *  alumnas, así que no se toca sin tocar también el módulo de Python y sus pruebas.
 */

/* ------------------------------------------------------ Constantes de la hoja --- */

// Ecuación de tasa metabólica basal.
const COEF_MLG = 13.587;
const COEF_MG = 9.613;
const COEF_SEXO_MASCULINO = 198;
const COEF_EDAD = 3.351;
const COEF_BASE = 674;

/** Efecto térmico de los alimentos, aplicado plano sobre el mantenimiento. */
const FACTOR_TERMICO = 1.1;
/** Kcal de superávit por kilo de peso ganado. */
const KCAL_POR_KILO_GANADO = 8400;

// Composición del peso que se pierde.
const FRACCION_GRASA_PURA = 0.87;
const FRACCION_MLG_PERDIDA = 0.2;
const FRACCION_PROTEINA_EN_MLG = 0.3;

// Reducción semanal recomendada, entre 0.5 % y 1.0 % del peso.
const REDUCCION_MIN = 0.005;
const REDUCCION_MAX = 0.01;

export const MAX_DIAS_REFEED = 2;

export type Sexo = "masculino" | "femenino";
export type BaseProteina = "peso_total" | "masa_libre_de_grasa";
export type RelacionGanancia = "2:1" | "1:1";
export type Macro = "carbohidrato" | "proteina" | "grasa";

/** Multiplicador con el que se pasa de tasa basal a mantenimiento. */
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

/** Rangos de referencia en g/kg. Avisan, no bloquean. */
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

// Reparto del peso que se baja, en la «regla del cuarto»: tres cuartas partes de grasa.
const FRACCION_GRASA_EN_LO_PERDIDO = 0.75;
const FRACCION_MLG_EN_LO_PERDIDO = 0.25;

export function factorDe(id: IdActividad): number {
  return ACTIVIDAD.find((a) => a.id === id)?.factor ?? 1.4;
}

/* ------------------------------------------------------- Composición corporal --- */

/** Clasificación de IMC. La hoja la tabula de 16 a 35. */
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
  const masaGrasaKg = pesoKg * porcentajeGrasa;
  const metros = estaturaCm / 100;
  const imc = pesoKg / (metros * metros);
  return {
    pesoKg,
    porcentajeGrasa,
    masaGrasaKg,
    masaLibreDeGrasaKg: pesoKg - masaGrasaKg,
    imc,
    clasificacionImc: clasificarImc(imc),
    pesoIdealBrocaKg: estaturaCm - 100, // Broca
    diferenciaPesoEstaturaKg: pesoKg - (estaturaCm - 100),
  };
}

/* --------------------------------------------------------------------- Energía --- */

/** La única diferencia entre sexos es el término de 198 kcal. */
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

/** De mantenimiento a calorías ajustadas. `porcentajeAjuste` con signo: −0.28 es déficit del 28 %. */
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

/** Calorías ajustadas por el porcentaje de cada macro, entre sus kcal por gramo. */
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

/** La proteína se expresa contra peso total o contra masa libre de grasa. */
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

/** Con 1 día a mantenimiento y 26 % los otros seis, el promedio cae a 22.29 %.
 *  La hoja suma el día de refeed una sola vez aunque sean dos; aquí se suma por cada día. */
export function deficitPromedioSemanal(
  porcentajeDiaBajo: number,
  diasRefeed: number,
  porcentajeDiaRefeed = 0,
): number {
  const diasBajos = 7 - diasRefeed;
  return (porcentajeDiaBajo * diasBajos + porcentajeDiaRefeed * diasRefeed) / 7;
}

/* ---------------------------------------------------------- Déficit recomendado --- */

/** Kcal en un kilo de peso bajado, unas 6 172: 750 g de grasa al 87 % de lípido y 250 g de
 *  masa magra al 30 % de proteína. */
export function energiaPorKiloPerdido(): number {
  const grasa = FRACCION_GRASA_EN_LO_PERDIDO * FRACCION_GRASA_PURA * KCAL_POR_GRAMO.grasa;
  const proteina = FRACCION_MLG_EN_LO_PERDIDO * FRACCION_PROTEINA_EN_MLG * KCAL_POR_GRAMO.proteina;
  return (grasa + proteina) * 1000;
}

export interface DeficitRecomendado {
  minimoKcal: number;
  maximoKcal: number;
  kcalPorKilo: number;
}

/** El inverso del ritmo recomendado: de 0.5 % a 1 % del peso por semana, en kcal al día. */
export function deficitRecomendado(comp: Composicion): DeficitRecomendado {
  const porDia = (comp.pesoKg * energiaPorKiloPerdido()) / 7;
  return {
    minimoKcal: porDia * REDUCCION_MIN,
    maximoKcal: porDia * REDUCCION_MAX,
    kcalPorKilo: energiaPorKiloPerdido(),
  };
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

/** **Solo la ve la coach**: asume adherencia perfecta. */
export function proyectarPerdida(
  comp: Composicion,
  porcentajeObjetivo: number,
  e: Energia,
): ProyeccionPerdida | null {
  if (!e.esDeficit || porcentajeObjetivo >= comp.porcentajeGrasa) return null;

  const grasaEnObjetivo = (porcentajeObjetivo * comp.masaGrasaKg) / comp.porcentajeGrasa;
  const grasaPorBajar = comp.masaGrasaKg - grasaEnObjetivo;

  // El modelo no supone que todo lo perdido sea grasa: por cada kilo se pierden 0.2 de MLG.
  const grasaPura = grasaPorBajar * FRACCION_GRASA_PURA;
  const mlgPerdida = grasaPorBajar * FRACCION_MLG_PERDIDA;
  const proteinaPura = mlgPerdida * FRACCION_PROTEINA_EN_MLG;

  const totales = grasaPorBajar + mlgPerdida;
  const kcalTotales = (grasaPura * 9 + proteinaPura * 4) * 1000;

  const perdidaSemanal = (-e.ajusteSemanalKcal * totales) / kcalTotales;
  const minimo = comp.pesoKg * REDUCCION_MIN;
  const maximo = comp.pesoKg * REDUCCION_MAX;

  return {
    kgGrasaPorBajar: grasaPorBajar,
    kgMlgQueSePierden: mlgPerdida,
    kgTotalesPorBajar: totales,
    kcalTotales,
    perdidaSemanalKg: perdidaSemanal,
    porcentajeSemanal: perdidaSemanal / comp.pesoKg,
    diasEstimados: kcalTotales / -e.ajusteDiarioKcal,
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

/** Etapa de volumen. */
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
  deficitRecomendado: DeficitRecomendado;
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
    deficitRecomendado: deficitRecomendado(comp),
    deficitPromedioSemanal: e.diasRefeed
      ? deficitPromedioSemanal(Math.abs(e.porcentajeAjuste), e.diasRefeed, e.porcentajeDiaRefeed)
      : null,
    proyeccionPerdida: proyectarPerdida(comp, e.porcentajeGrasaObjetivo, energ),
    proyeccionGanancia: proyectarGanancia(comp, energ, e.semanasGanancia, e.relacionGanancia),
  };
}
