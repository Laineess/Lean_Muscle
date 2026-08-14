/** Datos de ejemplo mientras no existe la API.
 *
 *  Cuando FastAPI exponga los endpoints, este archivo se sustituye por llamadas y los
 *  tipos se generan del esquema OpenAPI. La forma ya es la definitiva, así que el cambio
 *  es mecánico.
 */

import type {
  Alumna,
  Borrador,
  Chequeo,
  Ciclo,
  Coach,
  FilaCartera,
  Mensaje,
  ParametrosCiclo,
  PlanEntrenamiento,
  PlanNutricion,
} from "./tipos";

export const HOY = "2026-08-13";

export const coach: Coach = {
  nombre: "Mariana Cervantes",
  marca: "LeanMuscle",
  colorAcento: "#c9a227",
  plan: "Profesional",
  limiteAlumnas: 60,
  precioCiclo: 1200,
};

export const alumna: Alumna = {
  ulid: "01J9ZK3M4N5P6Q7R8S9T0V1W2X",
  nombre: "Andrea Sáenz",
  email: "andrea.saenz@ejemplo.mx",
  whatsapp: "55 1234 5678",
  fechaNacimiento: "1994-03-22",
  sexo: "F",
  estaturaCm: 165,
  objetivo: "recomposicion",
  nivelExperiencia: "Intermedio",
  ocupacion: "Diseñadora, trabajo sentada",
  basculaRef: "Báscula de vidrio del baño",
  lugarRef: "Recámara, junto a la ventana",
  horaRef: "07:00",
  zonaHoraria: "America/Mexico_City",
  porcentajeGrasaObjetivo: 0.22,
  cicloActual: 4,
};

export const historialClinico = {
  lesiones:
    "Esguince de tobillo derecho en 2023, ya recuperado. Molestia ocasional en rodilla izquierda al correr.",
  condiciones: "Hipotiroidismo controlado con levotiroxina.",
  medicacion: "Levotiroxina 50 mcg diaria, en ayunas.",
  restricciones: "Intolerancia a la lactosa. No come mariscos.",
  vigenteDesde: "2026-05-02",
};

export const chequeos: Chequeo[] = [
  {
    ulid: "01JCHK0001",
    numero: 1,
    fecha: "2026-05-03",
    estado: "validado",
    pesoKg: 68.4,
    porcentajeGrasa: 0.312,
    medidas: { cintura: 78.5, abdomen: 84, cadera: 98, busto: 92, pecho: 88, brazo: 28.5, muslo: 56, pantorrilla: 35.5 },
    fotos: { frontal: true, perfil: true, espalda: true },
    feedback:
      "Excelente punto de partida. La postura en la toma de perfil está perfecta: brazos relajados y abdomen neutro. Arrancamos con déficit moderado.",
    alertaOutlier: false,
  },
  {
    ulid: "01JCHK0002",
    numero: 2,
    fecha: "2026-06-01",
    estado: "validado",
    pesoKg: 67.1,
    porcentajeGrasa: 0.298,
    medidas: { cintura: 76.8, abdomen: 82.4, cadera: 97.2, busto: 91, pecho: 87.5, brazo: 28.6, muslo: 55.8, pantorrilla: 35.5 },
    fotos: { frontal: true, perfil: true, espalda: true },
    feedback:
      "Buen mes. Bajó cintura sin perder brazo, que es justo lo que buscábamos. Subimos proteína 10 g y agregamos un día de pierna.",
    alertaOutlier: false,
  },
  {
    ulid: "01JCHK0003",
    numero: 3,
    fecha: "2026-07-01",
    estado: "validado",
    pesoKg: 66.3,
    porcentajeGrasa: 0.286,
    medidas: { cintura: 75.4, abdomen: 81, cadera: 96.5, busto: 90.5, pecho: 87, brazo: 28.8, muslo: 55.4, pantorrilla: 35.4 },
    fotos: { frontal: true, perfil: true, espalda: true },
    feedback:
      "Sigue el descenso constante. Ojo con la iluminación de la foto de espalda: se ve más oscura que el mes pasado. Misma ventana, misma hora.",
    alertaOutlier: false,
  },
  {
    ulid: "01JCHK0004",
    numero: 4,
    fecha: "2026-08-01",
    estado: "pendiente_evaluacion",
    pesoKg: 65.2,
    porcentajeGrasa: 0.271,
    medidas: { cintura: 74.1, abdomen: 79.6, cadera: 95.8, busto: 90, pecho: 86.6, brazo: 29, muslo: 55, pantorrilla: 35.4 },
    fotos: { frontal: true, perfil: true, espalda: true },
    feedback: null,
    alertaOutlier: false,
  },
];

export const borradorInicial: Borrador = {
  numero: 5,
  fecha: HOY,
  ayunoConfirmado: false,
  pesoKg: null,
  pesajes: [{ fecha: "2026-08-11", pesoKg: 65.0 }],
  medidas: {},
  fotos: { frontal: false, perfil: false, espalda: false },
  notaAlumna: "",
};

export const parametrosCiclo: ParametrosCiclo = {
  ciclo: 5,
  actividad: "activo",
  porcentajeAjuste: -0.2,
  reparto: { carbohidrato: 0.4, proteina: 0.32, grasa: 0.28 },
  baseProteina: "masa_libre_de_grasa",
  diasRefeed: 1,
  porcentajeDiaRefeed: 0,
  relacionGanancia: "2:1",
  semanasGanancia: 20,
};

export const ciclo: Ciclo = {
  numero: 4,
  iniciaEn: "2026-07-15",
  terminaEn: "2026-08-14",
  estadoPago: "validado",
  precio: 1200,
};

export const planNutricion: PlanNutricion = {
  ciclo: 4,
  kcal: 1850,
  macros: { proteinaG: 140, carbohidratoG: 175, grasaG: 58 },
  notas: "Come la mayor parte de los carbohidratos alrededor del entrenamiento. Dos litros de agua mínimo.",
  tiempos: [
    {
      nombre: "Desayuno",
      hora: "07:30",
      kcal: 480,
      alimentos: [
        { nombre: "Claras de huevo", porcion: "200 g", kcal: 104, p: 22, c: 2, g: 0 },
        { nombre: "Avena", porcion: "60 g", kcal: 228, p: 8, c: 40, g: 4 },
        { nombre: "Arándanos", porcion: "80 g", kcal: 46, p: 1, c: 11, g: 0 },
        { nombre: "Almendras", porcion: "15 g", kcal: 102, p: 4, c: 3, g: 9 },
      ],
    },
    {
      nombre: "Comida",
      hora: "14:00",
      kcal: 620,
      alimentos: [
        { nombre: "Pechuga de pollo", porcion: "180 g", kcal: 297, p: 56, c: 0, g: 7 },
        { nombre: "Arroz integral cocido", porcion: "180 g", kcal: 200, p: 4, c: 42, g: 2 },
        { nombre: "Ensalada verde", porcion: "150 g", kcal: 38, p: 2, c: 6, g: 0 },
        { nombre: "Aceite de oliva", porcion: "10 ml", kcal: 88, p: 0, c: 0, g: 10 },
      ],
    },
    {
      nombre: "Colación",
      hora: "17:30",
      kcal: 260,
      alimentos: [
        { nombre: "Yogur griego sin lactosa", porcion: "170 g", kcal: 145, p: 17, c: 8, g: 4 },
        { nombre: "Plátano", porcion: "1 pieza", kcal: 105, p: 1, c: 27, g: 0 },
      ],
    },
    {
      nombre: "Cena",
      hora: "20:30",
      kcal: 490,
      alimentos: [
        { nombre: "Salmón", porcion: "150 g", kcal: 312, p: 34, c: 0, g: 19 },
        { nombre: "Camote horneado", porcion: "150 g", kcal: 129, p: 2, c: 30, g: 0 },
        { nombre: "Espárragos", porcion: "120 g", kcal: 24, p: 3, c: 4, g: 0 },
      ],
    },
  ],
};

export const planEntrenamiento: PlanEntrenamiento = {
  ciclo: 4,
  plantilla: "Fuerza superior/inferior — 4 días",
  notas: "Descansa 90 s entre series compuestas y 60 s en accesorios. Deja siempre 2 repeticiones en reserva.",
  dias: [
    {
      nombre: "Día 1 · Tren inferior",
      ejercicios: [
        { nombre: "Sentadilla trasera", series: 4, reps: "6-8", carga: "45 kg", nota: "Profundidad hasta paralelo. Rodilla izquierda: nada de valgo." },
        { nombre: "Peso muerto rumano", series: 3, reps: "8-10", carga: "40 kg", nota: "Barra pegada a la pierna." },
        { nombre: "Prensa de pierna", series: 3, reps: "10-12", carga: "90 kg", nota: "" },
        { nombre: "Elevación de talones sentada", series: 4, reps: "12-15", carga: "25 kg", nota: "" },
      ],
    },
    {
      nombre: "Día 2 · Tren superior (empuje)",
      ejercicios: [
        { nombre: "Press de banca con mancuernas", series: 4, reps: "8-10", carga: "14 kg", nota: "" },
        { nombre: "Press militar sentada", series: 3, reps: "8-10", carga: "10 kg", nota: "Sin arquear la espalda baja." },
        { nombre: "Fondos en máquina asistida", series: 3, reps: "10-12", carga: "-20 kg", nota: "" },
        { nombre: "Extensión de tríceps en polea", series: 3, reps: "12-15", carga: "15 kg", nota: "" },
      ],
    },
    {
      nombre: "Día 3 · Tren inferior (cadena posterior)",
      ejercicios: [
        { nombre: "Hip thrust", series: 4, reps: "8-10", carga: "60 kg", nota: "Pausa de 1 s arriba." },
        { nombre: "Zancada búlgara", series: 3, reps: "10 por pierna", carga: "12 kg", nota: "" },
        { nombre: "Curl femoral acostada", series: 3, reps: "12-15", carga: "25 kg", nota: "" },
      ],
    },
    {
      nombre: "Día 4 · Tren superior (jalón)",
      ejercicios: [
        { nombre: "Jalón al pecho", series: 4, reps: "8-10", carga: "35 kg", nota: "" },
        { nombre: "Remo con barra", series: 3, reps: "8-10", carga: "30 kg", nota: "Torso a 45°." },
        { nombre: "Face pull", series: 3, reps: "15", carga: "12 kg", nota: "" },
        { nombre: "Curl de bíceps con mancuerna", series: 3, reps: "10-12", carga: "8 kg", nota: "" },
      ],
    },
  ],
};

export const mensajes: Mensaje[] = [
  {
    autor: "alumna",
    cuerpo: "Hola Mariana, en el hip thrust siento que se me carga la espalda baja en vez del glúteo. ¿Qué ajusto?",
    enviadoEn: "2026-08-11T18:02:00Z",
  },
  {
    autor: "coach",
    cuerpo: "Casi siempre es el rango: estás subiendo de más y la pelvis se va a anteversión. Termina el movimiento cuando el tronco quede paralelo al piso y mete un poco la costilla. Prueba mañana con 50 kg y me cuentas.",
    enviadoEn: "2026-08-11T19:40:00Z",
  },
  { autor: "alumna", cuerpo: "Probé con 50 y sí, se sintió muchísimo mejor. Gracias.", enviadoEn: "2026-08-12T20:15:00Z" },
];

export const cartera: FilaCartera[] = [
  { ulid: "01JAL0001", nombre: "Andrea Sáenz", ciclo: 4, estado: "activa", chequeoEstado: "pendiente_evaluacion", chequeoFecha: "2026-08-01", pesoKg: 65.2, pesoPrevio: 66.3, plan: "Completo", pago: "validado", ultimoAcceso: "2026-08-12", alerta: null, adeudo: 0 },
  { ulid: "01JAL0002", nombre: "Paola Rentería", ciclo: 6, estado: "activa", chequeoEstado: "pendiente_evaluacion", chequeoFecha: "2026-08-02", pesoKg: 58.9, pesoPrevio: 65.8, plan: "Esencial", pago: "validado", ultimoAcceso: "2026-08-13", alerta: "outlier", adeudo: 0 },
  { ulid: "01JAL0003", nombre: "Renata Ibáñez", ciclo: 2, estado: "activa", chequeoEstado: "borrador", chequeoFecha: "2026-08-13", pesoKg: null, pesoPrevio: 71.2, plan: "Alto rendimiento", pago: "validado", ultimoAcceso: "2026-08-13", alerta: null, adeudo: 0 },
  { ulid: "01JAL0004", nombre: "Ximena Ordaz", ciclo: 9, estado: "activa", chequeoEstado: "validado", chequeoFecha: "2026-08-01", pesoKg: 62, pesoPrevio: 62.4, plan: "Completo", pago: "pendiente", ultimoAcceso: "2026-08-09", alerta: "pago", adeudo: 0 },
  { ulid: "01JAL0005", nombre: "Daniela Fuentes", ciclo: 3, estado: "activa", chequeoEstado: "rechazado_calidad", chequeoFecha: "2026-08-03", pesoKg: 74.5, pesoPrevio: 75.1, plan: "Esencial", pago: "validado", ultimoAcceso: "2026-08-10", alerta: null, adeudo: 0 },
  { ulid: "01JAL0006", nombre: "Sofía Bustamante", ciclo: 1, estado: "activa", chequeoEstado: "borrador", chequeoFecha: null, pesoKg: null, pesoPrevio: null, plan: "Alto rendimiento", pago: "validado", ultimoAcceso: "2026-08-09", alerta: "inactividad", adeudo: 0 },
  { ulid: "01JAL0007", nombre: "Lucía Márquez", ciclo: 5, estado: "pausa", chequeoEstado: null, chequeoFecha: null, pesoKg: 69.8, pesoPrevio: 70, plan: "Completo", pago: "pendiente", ultimoAcceso: "2026-07-28", alerta: "inactividad", adeudo: 0 },
];

export const notificaciones = [
  { tipo: "recordatorio_chequeo", texto: "Tu chequeo de agosto ya está abierto. Recuerda: en ayunas, recién despierta.", momento: "2026-08-01T06:00:00Z", leida: false },
  { tipo: "pago_validado", texto: "Tu pago del ciclo 4 fue validado. Acceso extendido 30 días.", momento: "2026-07-14T21:05:00Z", leida: true },
  { tipo: "plan_publicado", texto: "Tu plan del ciclo 4 ya está disponible.", momento: "2026-07-02T12:00:00Z", leida: true },
];
