/** Tipos del dominio, en la forma en que llegan de la API.
 *
 *  Espejan el modelo de `app/datos/modelos.py`. Cuando exista la API real, estos tipos se
 *  generan del esquema OpenAPI que FastAPI ya publica y este archivo se reduce a un import.
 */

export type EstadoChequeo =
  | "borrador"
  | "pendiente_evaluacion"
  | "validado"
  | "rechazado_calidad"
  | "descartado";

export type Angulo = "frontal" | "perfil" | "espalda";

export type TipoMedida =
  | "cintura"
  | "abdomen"
  | "cadera"
  | "busto"
  | "pecho"
  | "brazo"
  | "muslo"
  | "pantorrilla";

export type NivelActividad =
  | "muy_poco_activo"
  | "poco_activo"
  | "activo"
  | "muy_activo"
  | "intenso"
  | "muy_intenso"
  | "atleta"
  | "atleta_elite";

export interface Coach {
  nombre: string;
  marca: string;
  /** Reemplaza al dorado de MyFittPlan en toda la interfaz de sus alumnas. */
  colorAcento: string;
  plan: string;
  limiteAlumnas: number;
  precioCiclo: number;
}

export interface Alumna {
  ulid: string;
  nombre: string;
  email: string;
  whatsapp: string;
  fechaNacimiento: string;
  sexo: "M" | "F";
  estaturaCm: number;
  objetivo: "perdida_grasa" | "ganancia_masa" | "recomposicion";
  nivelExperiencia: string;
  ocupacion: string;
  basculaRef: string;
  lugarRef: string;
  horaRef: string;
  /** La regla de «mismo día calendario» se evalúa aquí, no en la zona de la coach. */
  zonaHoraria: string;
  porcentajeGrasaObjetivo: number;
  cicloActual: number;
}

export interface Chequeo {
  ulid: string;
  numero: number;
  fecha: string;
  estado: EstadoChequeo;
  pesoKg: number;
  /** Lo estima la coach al validar, comparando las fotos con la lámina de referencia. */
  porcentajeGrasa: number | null;
  medidas: Record<TipoMedida, number>;
  fotos: Record<Angulo, boolean>;
  feedback: string | null;
  alertaOutlier: boolean;
}

export interface Pesaje {
  fecha: string;
  pesoKg: number;
}

/** Chequeo en curso. Vive en el cliente hasta que se envía. */
export interface Borrador {
  numero: number;
  fecha: string;
  ayunoConfirmado: boolean;
  pesoKg: number | null;
  /** Hasta 3 fechas distintas por ciclo; el promedio alimenta la calculadora. */
  pesajes: Pesaje[];
  medidas: Partial<Record<TipoMedida, number>>;
  fotos: Record<Angulo, boolean>;
  notaAlumna: string;
}

export interface RepartoMacros {
  carbohidrato: number;
  proteina: number;
  grasa: number;
}

/** Entradas de la calculadora metabólica, guardadas por ciclo. */
export interface ParametrosCiclo {
  ciclo: number;
  actividad: NivelActividad;
  /** Fracción con signo: −0.20 es un déficit del 20 %. */
  porcentajeAjuste: number;
  reparto: RepartoMacros;
  baseProteina: "peso_total" | "masa_libre_de_grasa";
  diasRefeed: 0 | 1 | 2;
  porcentajeDiaRefeed: number;
  relacionGanancia: "2:1" | "1:1";
  semanasGanancia: number;
}

export interface Ciclo {
  numero: number;
  iniciaEn: string;
  terminaEn: string;
  estadoPago: "pendiente" | "validado" | "rechazado";
  precio: number;
}

export interface Alimento {
  nombre: string;
  porcion: string;
  kcal: number;
  p: number;
  c: number;
  g: number;
}

export interface TiempoDeComida {
  nombre: string;
  hora: string;
  kcal: number;
  alimentos: Alimento[];
}

export interface Ejercicio {
  nombre: string;
  series: number;
  reps: string;
  carga: string;
  nota: string;
}

export interface DiaDeEntrenamiento {
  nombre: string;
  ejercicios: Ejercicio[];
}

export interface PlanNutricion {
  ciclo: number;
  kcal: number;
  macros: { proteinaG: number; carbohidratoG: number; grasaG: number };
  notas: string;
  tiempos: TiempoDeComida[];
}

export interface PlanEntrenamiento {
  ciclo: number;
  plantilla: string;
  notas: string;
  dias: DiaDeEntrenamiento[];
}

export interface Mensaje {
  autor: "alumna" | "coach";
  cuerpo: string;
  enviadoEn: string;
}

export interface FilaCartera {
  ulid: string;
  nombre: string;
  ciclo: number;
  estado: "activa" | "pausa" | "baja";
  chequeoEstado: EstadoChequeo | null;
  chequeoFecha: string | null;
  pesoKg: number | null;
  pesoPrevio: number | null;
  plan: string | null;
  pago: string;
  ultimoAcceso: string;
  adeudo: number;
  alerta: "outlier" | "pago" | "inactividad" | null;
}

export const ROTULO_MEDIDA: Record<TipoMedida, string> = {
  cintura: "Cintura",
  abdomen: "Abdomen",
  cadera: "Cadera",
  busto: "Busto",
  pecho: "Pecho",
  brazo: "Brazo",
  muslo: "Muslo",
  pantorrilla: "Pantorrilla",
};

export const ROTULO_ESTADO: Record<EstadoChequeo, string> = {
  borrador: "Borrador",
  pendiente_evaluacion: "En revisión",
  validado: "Validado",
  rechazado_calidad: "Rechazado",
  descartado: "Descartado",
};

export const ROTULO_OBJETIVO: Record<Alumna["objetivo"], string> = {
  perdida_grasa: "Pérdida de grasa",
  ganancia_masa: "Ganancia de masa",
  recomposicion: "Recomposición",
};

export const ANGULOS: { id: Angulo; rotulo: string; guia: string }[] = [
  {
    id: "frontal",
    rotulo: "Frontal",
    guia: "De frente a la cámara, brazos relajados a los lados, pies a la anchura de los hombros.",
  },
  {
    id: "perfil",
    rotulo: "Perfil",
    guia: "De lado, mirando a la pared. Brazos colgando, abdomen relajado — sin meterlo.",
  },
  {
    id: "espalda",
    rotulo: "Espalda",
    guia: "De espaldas, misma postura que la frontal. Hombros abajo, sin tensar.",
  },
];

export const MEDIDAS: {
  tipo: TipoMedida;
  rotulo: string;
  min: number;
  max: number;
  ayuda: string;
}[] = [
  { tipo: "cintura", rotulo: "Cintura", min: 40, max: 200, ayuda: "Punto más estrecho del torso, a la altura del ombligo. Cinta paralela al piso." },
  { tipo: "abdomen", rotulo: "Abdomen", min: 40, max: 200, ayuda: "Zona media abdominal, relajada. Sin meter aire ni apretar." },
  { tipo: "cadera", rotulo: "Cadera", min: 50, max: 250, ayuda: "Punto máximo de glúteos, de pie con los pies juntos." },
  { tipo: "busto", rotulo: "Busto", min: 50, max: 200, ayuda: "Contorno a la altura del pezón, brazos relajados a los lados." },
  { tipo: "pecho", rotulo: "Pecho", min: 50, max: 200, ayuda: "Contorno axilar, por debajo de las axilas. Respiración normal." },
  { tipo: "brazo", rotulo: "Brazo", min: 15, max: 70, ayuda: "Punto medio del bíceps, brazo extendido y relajado. Sin flexionar." },
  { tipo: "muslo", rotulo: "Muslo", min: 30, max: 100, ayuda: "Punto medio entre la ingle y la rodilla, peso repartido en ambas piernas." },
  { tipo: "pantorrilla", rotulo: "Pantorrilla", min: 15, max: 70, ayuda: "Punto máximo, planta del pie completa en el piso." },
];
