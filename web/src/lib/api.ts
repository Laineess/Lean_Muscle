/** Cliente de la API.
 *
 *  El token de sesión vive en una cookie **HttpOnly** que pone el servidor: aquí no se lee
 *  ni se escribe, solo se pide que viaje con `credentials: "include"`. Por eso no hay
 *  ninguna cabecera de autorización que armar.
 *
 *  El servidor responde los errores de negocio con `{ codigo, mensaje }`, y el `mensaje` ya
 *  viene redactado para la usuaria. Este cliente no inventa textos: si el servidor tiene
 *  algo que decir, se muestra tal cual.
 */

const BASE = "/api";

/** Qué hacer cuando el servidor dice que la sesión ya no vale.
 *
 *  Lo pone `main.tsx`. Sin esto, la copia del actor en `sessionStorage` mantiene la interfaz
 *  en pie mientras cada petición devuelve 401: se ve el panel entero y no funciona nada.
 */
let alCaducarLaSesion: (() => void) | null = null;

/** Qué hacer cuando el servidor cierra todo por tener la contraseña inicial sin cambiar. */
let alFaltarLaContrasena: (() => void) | null = null;

export function cuandoCaduqueLaSesion(accion: () => void): void {
  alCaducarLaSesion = accion;
}

export function cuandoFalteCambiarLaContrasena(accion: () => void): void {
  alFaltarLaContrasena = accion;
}

/** Código que devuelve el servidor mientras la contraseña inicial siga puesta. */
const SIN_CAMBIAR = "CONTRASENA_INICIAL_SIN_CAMBIAR";

/** El código del error. FastAPI lo envuelve en `detail` cuando lo levanta una dependencia,
 *  y lo deja suelto cuando pasa por el manejador de `ErrorDeDominio`. */
function codigoDe(d: { codigo?: string; detail?: unknown }): string | null {
  if (d.codigo) return d.codigo;
  if (d.detail && typeof d.detail === "object" && "codigo" in d.detail) {
    return String((d.detail).codigo);
  }
  return null;
}

function revisarSesion(estado: number, codigo?: string | null): void {
  // 403 a secas es «no te toca», y la sesión sigue siendo válida. Pero uno con este código
  // significa que el servidor tiene cerrada la aplicación entera hasta que ponga la suya:
  // sin atenderlo aquí, cada pantalla dispara sus peticiones y todas fallan igual.
  if (estado === 401) alCaducarLaSesion?.();
  else if (estado === 403 && codigo === SIN_CAMBIAR) alFaltarLaContrasena?.();
}

export class ErrorApi extends Error {
  constructor(
    readonly estado: number,
    readonly codigo: string | null,
    mensaje: string,
    readonly detalle?: Record<string, unknown>,
  ) {
    super(mensaje);
    this.name = "ErrorApi";
  }

  /** La sesión expiró o nunca hubo. El marco redirige al acceso. */
  get esSesionInvalida(): boolean {
    return this.estado === 401;
  }
}

interface Opciones {
  metodo?: "GET" | "POST" | "PUT" | "DELETE";
  cuerpo?: unknown;
  senal?: AbortSignal;
}

async function pedir<T>(ruta: string, opciones: Opciones = {}): Promise<T> {
  const { metodo = "GET", cuerpo, senal } = opciones;

  // `exactOptionalPropertyTypes` no acepta `undefined` en propiedades opcionales, así que
  // las claves se agregan solo cuando hay valor en lugar de asignarles undefined.
  const init: RequestInit = { method: metodo, credentials: "include" };
  if (cuerpo !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(cuerpo);
  }
  if (senal) init.signal = senal;

  let respuesta: Response;
  try {
    respuesta = await fetch(`${BASE}${ruta}`, init);
  } catch (causa) {
    // Un fallo de red no es un error de la API: distinguirlo evita mostrar «error interno»
    // cuando lo único que pasa es que el teléfono perdió señal en el gimnasio.
    if (causa instanceof DOMException && causa.name === "AbortError") throw causa;
    throw new ErrorApi(0, "SIN_CONEXION", "No hay conexión. Revisa tu señal e inténtalo otra vez.");
  }

  if (respuesta.status === 204) return undefined as T;

  const texto = await respuesta.text();
  const datos: unknown = texto ? JSON.parse(texto) : null;

  if (!respuesta.ok) {
    const d = (datos ?? {}) as { codigo?: string; mensaje?: string; detail?: unknown; detalle?: Record<string, unknown> };
    revisarSesion(respuesta.status, codigoDe(d));
    const mensaje =
      d.mensaje ??
      (typeof d.detail === "string" ? d.detail : null) ??
      "Algo salió mal. Vuelve a intentarlo.";
    throw new ErrorApi(respuesta.status, d.codigo ?? null, mensaje, d.detalle);
  }

  return datos as T;
}

/** Sube un archivo como `multipart/form-data`.
 *
 *  No usa `pedir` porque el cuerpo no es JSON: aquí **no se pone `Content-Type`** a mano. El
 *  navegador lo escribe solo con el `boundary` que acaba de generar, y ponerlo nosotros
 *  produce un cuerpo que el servidor no puede separar.
 */
async function subir<T>(
  ruta: string,
  archivo: File,
  metodo: "POST" | "PUT" = "PUT",
): Promise<T> {
  const cuerpo = new FormData();
  cuerpo.append("archivo", archivo, archivo.name);

  let respuesta: Response;
  try {
    respuesta = await fetch(`${BASE}${ruta}`, { method: metodo, credentials: "include", body: cuerpo });
  } catch {
    throw new ErrorApi(0, "SIN_CONEXION", "No hay conexión. Revisa tu señal e inténtalo otra vez.");
  }

  if (respuesta.status === 204) return undefined as T;

  const texto = await respuesta.text();
  const datos: unknown = texto ? JSON.parse(texto) : null;

  if (!respuesta.ok) {
    const d = (datos ?? {}) as { codigo?: string; mensaje?: string; detail?: unknown };
    revisarSesion(respuesta.status, codigoDe(d));
    const mensaje =
      d.mensaje ??
      (typeof d.detail === "string" ? d.detail : null) ??
      "No se pudo subir el archivo.";
    throw new ErrorApi(respuesta.status, d.codigo ?? null, mensaje);
  }

  return datos as T;
}

/** Igual que `subir`, pero con campos de texto junto al archivo.
 *
 *  Va en el mismo `FormData` y no en la URL: una nota puede traer acentos, saltos de línea
 *  y comas, y meterla en la query obliga a escaparla dos veces.
 */
async function subirConCampos<T>(
  ruta: string,
  archivo: File,
  campos: Record<string, string>,
): Promise<T> {
  const cuerpo = new FormData();
  cuerpo.append("archivo", archivo, archivo.name);
  for (const [clave, valor] of Object.entries(campos)) cuerpo.append(clave, valor);

  let respuesta: Response;
  try {
    respuesta = await fetch(`${BASE}${ruta}`, { method: "POST", credentials: "include", body: cuerpo });
  } catch {
    throw new ErrorApi(0, "SIN_CONEXION", "No hay conexión. Revisa tu señal e inténtalo otra vez.");
  }

  if (respuesta.status === 204) return undefined as T;

  const texto = await respuesta.text();
  const datos: unknown = texto ? JSON.parse(texto) : null;

  if (!respuesta.ok) {
    const d = (datos ?? {}) as { codigo?: string; mensaje?: string; detail?: unknown };
    revisarSesion(respuesta.status, codigoDe(d));
    const mensaje =
      d.mensaje ??
      (typeof d.detail === "string" ? d.detail : null) ??
      "No se pudo subir el archivo.";
    throw new ErrorApi(respuesta.status, d.codigo ?? null, mensaje);
  }

  return datos as T;
}

/* ------------------------------------------------------------------ Tipos --- */

export interface ActorPublico {
  rol: "alumna" | "coach" | "admin_plataforma";
  nombre: string;
  correo: string;
  colorAcento: string;
  marca: string;
  /** Entró con la contraseña inicial. Hasta que la cambie el servidor cierra lo demás. */
  debeCambiarContrasena: boolean;
}

export interface ChequeoApi {
  ulid: string;
  numero: number;
  fecha: string;
  estado: string;
  pesoKg: number | null;
  porcentajeGrasa: number | null;
  medidas: Record<string, number>;
  fotos: Record<string, boolean>;
  feedback: string | null;
  alertaOutlier: boolean;
}

export interface InicioAlumnaApi {
  perfil: {
    ulid: string;
    nombre: string;
    correo: string;
    estaturaCm: number | null;
    plan: string | null;
    basculaRef: string | null;
    lugarRef: string | null;
    horaRef: string | null;
    zonaHoraria: string;
    /** Falso hasta que contesta el cuestionario inicial. */
    cuestionarioCompleto: boolean;
  };
  ciclo: {
    numero: number;
    iniciaEn: string;
    terminaEn: string;
    estadoPago: string;
    precio: number;
  } | null;
  chequeos: ChequeoApi[];
  ultimoFeedback: string | null;
  avisosSinLeer: number;
  /** Título del último aviso sin leer. Nulo si no tiene ninguno. */
  ultimoAviso: string | null;
  coach: string;
  proximasCitas: CitaDeAlumnaApi[];
  /** Nulo mientras su coach no le haya publicado nada. */
  plan: {
    publicado: boolean;
    kcalObjetivo: number | null;
    diasEntrenamiento: number;
    primerDia: string | null;
  } | null;
}

export interface AlimentoApi {
  nombre: string;
  porcion: string;
  kcal: number;
  p: number;
  c: number;
  g: number;
  /** Cantidad y referencia del catálogo, para reescalar sin volver a buscar. Los planes
   *  anteriores no las traen: se deducen de lo capturado al abrir el constructor. */
  cantidad?: number;
  unidad?: string;
  base?: { porcion: number; kcal: number; p: number; c: number; g: number };
}

export interface ParametrosDeCicloApi {
  actividad: string;
  porcentajeAjuste: number;
  reparto: { carbohidrato: number; proteina: number; grasa: number };
  baseProteina: string;
  diasRefeed: number;
  porcentajeDiaRefeed: number;
  relacionGanancia: string;
}

/** Todo lo que abre el constructor de planes, en una llamada. */
export interface ExpedienteDeConstructorApi {
  alumnaUlid: string;
  alumna: string;
  ciclo: number;
  fechaNacimiento: string;
  sexo: string | null;
  estaturaCm: number | null;
  porcentajeGrasaObjetivo: number | null;
  chequeo: {
    fecha: string;
    estado: string;
    pesoKg: number | null;
    porcentajeGrasa: number | null;
  } | null;
  parametros: ParametrosDeCicloApi;
  nutricion: PlanApi | null;
  entrenamiento: PlanApi | null;
  /** El plan comercial que contrató y su precio: es lo que se cobra de mensualidad. */
  planNombre: string | null;
  planPrecio: number | null;
}

/* ------------------------------------------- Presentación y cuestionario --- */

export interface DatoDeFichaApi {
  rotulo: string;
  valor: string;
}

export interface PresentacionApi {
  titulo: string;
  texto: string;
  ficha: DatoDeFichaApi[];
  activa: boolean;
  tieneFoto: boolean;
  marca: string;
  colorAcento: string;
}

export type TipoDePregunta = "texto" | "texto_largo" | "numero" | "opcion" | "si_no";

export interface PreguntaApi {
  ulid: string;
  texto: string;
  ayuda: string | null;
  tipo: TipoDePregunta;
  opciones: string[];
  obligatoria: boolean;
  orden: number;
  activa: boolean;
}

export interface PreguntaNuevaApi {
  texto: string;
  ayuda?: string | null;
  tipo: TipoDePregunta;
  opciones: string[];
  obligatoria: boolean;
  orden: number;
  activa: boolean;
}

export interface NucleoClinicoApi {
  lesiones: string | null;
  condiciones: string | null;
  medicacion: string | null;
  restricciones: string | null;
}

export interface CuestionarioApi {
  completo: boolean;
  nucleo: NucleoClinicoApi;
  preguntas: PreguntaApi[];
  respuestas: { preguntaUlid: string; valor: string }[];
  consentimientosPendientes: string[];
}

export interface EnvioDeCuestionarioApi {
  nucleo: NucleoClinicoApi;
  respuestas: { preguntaUlid: string; valor: string }[];
  consentimientos: string[];
}

export interface RespuestaDeAlumnaApi {
  pregunta: string;
  tipo: string;
  valor: string;
}

export interface CeldaDeHojaApi {
  celda: string;
  rotulo: string;
  valor: string;
  unidad: string;
  formula: string;
  capturado: boolean;
}

export interface BloqueDeHojaApi {
  titulo: string;
  rango: string;
  celdas: CeldaDeHojaApi[];
}

export interface TablaDeHojaApi {
  titulo: string;
  rango: string;
  encabezados: string[];
  filas: string[][];
}

export interface HojaDeCalculoApi {
  alumna: string;
  bloques: BloqueDeHojaApi[];
  tablas: TablaDeHojaApi[];
  /** Por qué no se puede calcular todavía, si es el caso. */
  falta: string | null;
}

export type FrecuenciaFotos = "ninguna" | "diaria" | "semanal" | "quincenal" | "mensual";

export interface FotoDeComidaApi {
  ulid: string;
  subidaEn: string;
  /** Cuándo se borra. Va explícito para que la alumna no lo tenga que calcular. */
  expiraEn: string;
  tiempo: string | null;
  nota: string | null;
  comentario: string | null;
}

export interface FotosDeComidaApi {
  frecuencia: FrecuenciaFotos;
  rotulo: string;
  desde: string | null;
  hasta: string | null;
  cumplido: boolean;
  fotos: FotoDeComidaApi[];
}

/** Un cobro visto desde la agenda. No es una cita: no tiene hora. */
export interface MarcaDeCobroApi {
  ulid: string;
  fecha: string;
  alumnaUlid: string;
  alumna: string;
  concepto: string;
  monto: number;
  estado: string;
  vencido: boolean;
}

export interface AgendaApi {
  citas: CitaApi[];
  cobros: MarcaDeCobroApi[];
}

export interface ServicioApi {
  ulid: string;
  nombre: string;
  descripcion: string | null;
  motivo: MotivoDeCobro;
  precio: number;
  activo: boolean;
}

export interface ServicioNuevoApi {
  nombre: string;
  descripcion?: string | null;
  motivo: MotivoDeCobro;
  precio: number;
  activo: boolean;
}

export interface PlanApi {
  tipo: "nutricion" | "entrenamiento";
  ciclo: number;
  estado: string;
  publicadoEn: string | null;
  /** JSON libre: su forma cambia seguido y no se consulta por dentro, se lee completo. */
  contenido: {
    notas?: string;
    plantilla?: string;
    tiempos?: { nombre: string; hora: string; kcal: number; alimentos: AlimentoApi[] }[];
    dias?: {
      nombre: string;
      ejercicios: { nombre: string; series: number; reps: string; carga: string; nota: string }[];
    }[];
  };
  kcalObjetivo: number | null;
  proteinaG: number | null;
  carbohidratoG: number | null;
  grasaG: number | null;
  /** Cada cuánto se le piden fotos de sus comidas. Solo el plan de nutrición la usa. */
  frecuenciaFotos: FrecuenciaFotos;
}

export interface PlanesDeAlumnaApi {
  nutricion: PlanApi | null;
  entrenamiento: PlanApi | null;
  /** La guarda vive en el servidor: aquí solo se refleja. */
  bloqueadoPorPago: boolean;
  /** Por qué: `pago`, `ciclo_vencido`, `sin_ciclo`. Nulo si no está bloqueado. */
  motivoBloqueo: "pago" | "ciclo_vencido" | "sin_ciclo" | null;
  restricciones: string | null;
  lesiones: string | null;
}

export interface FilaCarteraApi {
  ulid: string;
  nombre: string;
  ciclo: number;
  estado: string;
  chequeoEstado: string | null;
  chequeoFecha: string | null;
  pesoKg: number | null;
  pesoPrevio: number | null;
  plan: string | null;
  pago: string;
  ultimoAcceso: string | null;
  alerta: "outlier" | "pago" | "inactividad" | null;
  adeudo: number;
}

export interface ResumenPanelApi {
  coach: string;
  marca: string;
  plan: string;
  limiteAlumnas: number;
  precioCiclo: number;
  porValidar: FilaCarteraApi[];
  conAlerta: FilaCarteraApi[];
  activas: number;
  porCobrar: number;
}

export interface CitaApi {
  ulid: string;
  titulo: string;
  tipo: "consulta" | "bloqueo";
  estado: "agendada" | "confirmada" | "realizada" | "cancelada";
  modalidad: "presencial" | "video" | "telefono";
  alumnaUlid: string | null;
  alumnaNombre: string | null;
  iniciaEn: string;
  terminaEn: string;
  notas: string | null;
  motivoCancelacion: string | null;
}

export interface CitaNuevaApi {
  titulo: string;
  tipo: string;
  modalidad: string;
  alumnaUlid: string | null;
  iniciaEn: string;
  terminaEn: string;
  notas: string | null;
}

export interface AltaDeAlumnaApi {
  nombre: string;
  correo: string;
  whatsapp: string | null;
  fechaNacimiento: string;
  estaturaCm: number | null;
  tarifaUlid: string | null;
  nivelExperiencia: string | null;
}

export interface AlumnaDadaDeAltaApi {
  alumnaUlid: string;
  correo: string;
  /** Se devuelve una sola vez: después solo queda su hash. */
  claveTemporal: string;
}

export interface EdicionDeAlumnaApi {
  nombre: string;
  whatsapp: string | null;
  estaturaCm: number | null;
  tarifaUlid: string | null;
  nivelExperiencia: string | null;
  equipo: string | null;
  ocupacion: string | null;
  basculaRef: string | null;
  lugarRef: string | null;
  horaRef: string | null;
  estado: string | null;
}

export interface MovimientoApi {
  ulid: string;
  tipo: "ingreso" | "gasto";
  categoria: string;
  monto: number;
  fecha: string;
  concepto: string;
  alumnaUlid: string | null;
  alumnaNombre: string | null;
  /** Nace de un pago validado: no se edita a mano. */
  automatico: boolean;
  nota: string | null;
}

export interface MovimientoNuevoApi {
  tipo: string;
  categoria: string;
  monto: number;
  fecha: string;
  concepto: string;
  alumnaUlid: string | null;
  nota: string | null;
  /** Cobro programado que salda este ingreso. Lo marca como pagado. */
  cobroUlid: string | null;
}

export interface PanelFinancieroApi {
  ingresos: number;
  gastos: number;
  utilidad: number;
  margen: number;
  ingresoPorAlumna: number;
  proyeccionMensual: number;
  alumnasActivas: number;
  porMes: { mes: string; ingresos: number; gastos: number; utilidad: number }[];
  ingresosPorCategoria: { categoria: string; monto: number }[];
  gastosPorCategoria: { categoria: string; monto: number }[];
  movimientos: MovimientoApi[];
}

export interface TarifaApi {
  ulid: string;
  codigo: string;
  nombre: string;
  descripcion: string | null;
  precio: number;
  dias: number;
  activa: boolean;
}

export interface AlimentoCatalogoApi {
  ulid: string;
  nombre: string;
  marca: string | null;
  porcion: number;
  unidad: string;
  kcal: number;
  proteina: number;
  carbo: number;
  grasa: number;
  grupo: string | null;
  propio: boolean;
}

export interface EjercicioCatalogoApi {
  ulid: string;
  nombre: string;
  grupo: string | null;
  equipo: string | null;
  patron: string | null;
  tieneVideo: boolean;
  contraindicaciones: string | null;
  propio: boolean;
}

export interface FotoApi {
  angulo: "frontal" | "perfil" | "espalda";
  /** `false` = ya se purgó: la fila sobrevive con su fecha, la imagen no. */
  disponible: boolean;
  nitidez: number | null;
  luminancia: number | null;
  estadoAuto: string;
  esLineaBase: boolean;
  tomadaEn: string | null;
  purgadaEn: string | null;
  diasParaPurga: number | null;
}

export interface HistorialApi {
  lesiones: string | null;
  condiciones: string | null;
  medicacion: string | null;
  restricciones: string | null;
  vigenteDesde: string;
  versiones: number;
}

export type Angulo = "frontal" | "perfil" | "espalda";

export interface FotoDeBorradorApi {
  angulo: string;
  estadoAuto: string;
  motivoRechazo: string | null;
  nitidez: number | null;
  luminancia: number | null;
  tomadaEn: string | null;
}

export interface PesajeApi {
  fecha: string;
  pesoKg: number;
}

export interface BorradorApi {
  ulid: string;
  numero: number;
  fecha: string;
  estado: string;
  ayunoConfirmado: boolean;
  varianzaConfirmada: boolean;
  notaAlumna: string | null;
  pesoKg: number | null;
  medidas: Record<string, number>;
  fotos: FotoDeBorradorApi[];
  pesajes: PesajeApi[];
  maxPesajes: number;
  pesoAnteriorKg: number | null;
  medidasAnteriores: Record<string, number>;
  basculaRef: string | null;
  lugarRef: string | null;
  horaRef: string | null;
  basculaUsada: string | null;
  lugarUsado: string | null;
  horaUsada: string | null;
}

export interface GuardadoDeChequeoApi {
  ayunoConfirmado?: boolean;
  pesoKg?: number;
  varianzaConfirmada?: boolean;
  medidas?: Record<string, number>;
  notaAlumna?: string;
  basculaUsada?: string;
  lugarUsado?: string;
  horaUsada?: string;
}

/** Lo que el servidor devolvió al recortar y medir la foto. */
export interface FotoSubidaApi {
  angulo: string;
  estadoAuto: string;
  motivoRechazo: string | null;
  nitidez: number;
  luminancia: number;
}

/** Lo que el OCR entendió del comprobante. Es una sugerencia: la coach confirma. */
export interface ComprobanteApi {
  pagoUlid: string;
  monto: number | null;
  fecha: string | null;
  referencia: string | null;
  banco: string | null;
  confianza: number;
  requiereRevision: boolean;
}

export interface MensajeApi {
  ulid: string;
  autor: "alumna" | "coach";
  cuerpo: string;
  enviadoEn: string;
  leidoEn: string | null;
}

/** Un aviso de la coach, visto desde su panel: a cuántas fue y cuántas lo abrieron. */
export interface AnuncioApi {
  ulid: string;
  titulo: string;
  cuerpo: string;
  enviadoEn: string;
  enviadas: number;
  leidas: number;
}

/** El mismo aviso, visto por la alumna. */
export interface AvisoDeAlumnaApi {
  ulid: string;
  titulo: string;
  cuerpo: string;
  recibidoEn: string;
  leidoEn: string | null;
}

/* ------------------------------------------------------- Panel de plataforma --- */

export interface SuscripcionApi {
  plan: string;
  precio: number;
  periodicidad: "mensual" | "anual";
  estado: "cortesia" | "al_corriente" | "por_vencer" | "vencida" | "cancelada";
  iniciaEn: string;
  vigenteHasta: string | null;
  nota: string | null;
}

/** Una coach vista desde la plataforma. **Solo agregados: ninguna cifra llega a una alumna.** */
export interface FilaDeCoachApi {
  ulid: string;
  nombre: string;
  marca: string;
  slug: string;
  email: string;
  plan: string;
  limiteAlumnas: number;
  estado: string;
  precioCiclo: number;
  creadoEn: string;
  alumnas: number;
  alumnasActivas: number;
  chequeosPorValidar: number;
  chequeosDelMes: number;
  fotos: number;
  mbFotos: number;
  ultimoAcceso: string | null;
  diasInactiva: number | null;
  suscripcion: SuscripcionApi | null;
}

export interface AltaDeCoachApi {
  nombre: string;
  marca: string;
  email: string;
  slug: string | null;
  plan: string;
  limiteAlumnas: number;
  precioCiclo: number;
  colorAcento: string;
  zonaHoraria: string;
}

export interface EdicionDeCoachApi {
  nombre: string;
  marca: string;
  plan: string;
  limiteAlumnas: number;
  estado: string;
  precioCiclo: number;
  colorAcento: string;
}

export interface EdicionDeSuscripcionApi {
  plan: string;
  precio: number;
  periodicidad: string;
  estado: string;
  vigenteHasta: string | null;
  nota: string | null;
}

export interface CobroApi {
  ulid: string;
  coachUlid: string;
  monto: number;
  fecha: string;
  metodo: string;
  periodoInicia: string | null;
  periodoTermina: string | null;
  nota: string | null;
}

export interface CobroNuevoApi {
  monto: number;
  fecha: string;
  metodo: string;
  periodoInicia: string | null;
  periodoTermina: string | null;
  nota: string | null;
}

export interface FacturacionApi {
  cobradoEnElAno: number;
  facturacionMensualEsperada: number;
  coachesAlCorriente: number;
  coachesVencidas: number;
  coachesEnCortesia: number;
  porMes: { mes: string; ingresos: number; gastos: number; utilidad: number }[];
}

export interface SaludApi {
  avisosPendientes: number;
  avisosAgotados: number;
  ultimoAvisoEnviado: string | null;
  fotosPorPurgar: number;
  mbTotales: number;
  suscripcionesPush: number;
  sesionesVivas: number;
  coachesActivas: number;
  coachesInactivas: number;
}

export interface MovimientoDeAuditoriaApi {
  cuando: string;
  coach: string;
  actorTipo: string;
  accion: string;
  entidad: string;
}

export interface PlanComercialApi {
  ulid: string;
  codigo: string;
  nombre: string;
  descripcion: string | null;
  precio: number;
  dias: number;
  intensidad: "baja" | "media" | "alta";
  activa: boolean;
  alumnas: number;
}

export type PlanComercialNuevoApi = Omit<PlanComercialApi, "ulid" | "alumnas">;

export type MotivoDeCobro = "inscripcion" | "mensualidad" | "cita" | "material" | "otro";

export interface CobroApi2 {
  ulid: string;
  fecha: string;
  motivo: MotivoDeCobro;
  concepto: string;
  monto: number;
  estado: "pendiente" | "en_revision" | "pagado" | "cancelado";
  pagadoEn: string | null;
  nota: string | null;
  /** La fecha pasó y sigue sin pagarse. Es lo que pausa el plan de la alumna. */
  vencido: boolean;
  tieneComprobante: boolean;
  /** Por qué se rechazó el comprobante anterior. La alumna lo lee tal cual. */
  motivoRechazo: string | null;
}

export interface ComprobantePorRevisarApi {
  cobroUlid: string;
  alumnaUlid: string;
  alumna: string;
  plan: string | null;
  fechaCobro: string;
  concepto: string;
  montoEsperado: number;
  subidoEn: string | null;
  /** Lo que el OCR entendió. Es una sugerencia, no una validación. */
  montoLeido: number | null;
  fechaLeida: string | null;
  referencia: string | null;
  banco: string | null;
  confianza: number;
  /** El importe leído no coincide con el esperado. Mirar la imagen deja de ser opcional. */
  montoNoCuadra: boolean;
}

export interface CobroNuevoProgramadoApi {
  fecha: string;
  motivo: MotivoDeCobro;
  concepto: string | null;
  monto: number;
  nota: string | null;
}

export interface AlumnaConCobrosApi {
  ulid: string;
  nombre: string;
  plan: string | null;
  pendientes: CobroApi2[];
  adeudo: number;
}

export interface DocumentoLegalApi {
  clave: string;
  titulo: string;
  version: string;
  actualizado: string;
  /** Markdown tal cual está en `docs/`. */
  contenido: string;
  /** Huecos sin rellenar. Vacío = el documento está completo. */
  marcadores: string[];
}

export interface CitaDeAlumnaApi {
  ulid: string;
  titulo: string;
  modalidad: "presencial" | "video" | "telefono";
  estado: string;
  iniciaEn: string;
  terminaEn: string;
}

export interface MarcaApi {
  nombre: string;
  marca: string;
  colorAcento: string;
  tieneLogo: boolean;
}

export interface ChequeoDeValidacionApi {
  ulid: string;
  numero: number;
  fecha: string;
  estado: string;
  pesoKg: number | null;
  porcentajeGrasa: number | null;
  medidas: Record<string, number>;
  notaAlumna: string | null;
  alertaOutlier: boolean;
  varianzaConfirmada: boolean;
  basculaUsada: string | null;
  lugarUsado: string | null;
  horaUsada: string | null;
}

export interface ExpedienteDeValidacionApi {
  alumnaUlid: string;
  alumna: string;
  estaturaCm: number | null;
  plan: string | null;
  actual: ChequeoDeValidacionApi | null;
  anteriores: ChequeoDeValidacionApi[];
  lesiones: string | null;
  restricciones: string | null;
}

export interface PlanGuardadoApi {
  tipo: "nutricion" | "entrenamiento";
  contenido: Record<string, unknown>;
  kcalObjetivo?: number | null;
  proteinaG?: number | null;
  carbohidratoG?: number | null;
  grasaG?: number | null;
  publicar: boolean;
  /** Solo con el plan de nutrición: es donde vive la calculadora. */
  parametros?: ParametrosDeCicloApi;
  frecuenciaFotos?: FrecuenciaFotos;
}

/* --------------------------------------------------------------- Endpoints --- */

export const api = {
  acceso: {
    entrar: (correo: string, contrasena: string, recordarme: boolean) =>
      pedir<ActorPublico>("/auth/login", {
        metodo: "POST",
        cuerpo: { correo, contrasena, recordarme },
      }),
    salir: () => pedir<void>("/auth/logout", { metodo: "POST" }),
    yo: (senal?: AbortSignal) => pedir<ActorPublico>("/auth/yo", senal ? { senal } : {}),
    cambiarContrasena: (actual: string, nueva: string) =>
      pedir<void>("/auth/contrasena", { metodo: "POST", cuerpo: { actual, nueva } }),
  },

  alumna: {
    inicio: (senal?: AbortSignal) => pedir<InicioAlumnaApi>("/mi/inicio", senal ? { senal } : {}),

    presentacion: (senal?: AbortSignal) =>
      pedir<PresentacionApi>("/mi/presentacion", senal ? { senal } : {}),

    fotosDeComida: (senal?: AbortSignal) =>
      pedir<FotosDeComidaApi>("/mi/fotos-comida", senal ? { senal } : {}),
    subirFotoDeComida: (archivo: File, tiempo: string, nota: string) =>
      subirConCampos<FotoDeComidaApi>("/mi/fotos-comida", archivo, { tiempo, nota }),
    borrarFotoDeComida: (ulid: string) =>
      pedir<void>(`/mi/fotos-comida/${ulid}`, { metodo: "DELETE" }),
    cuestionario: (senal?: AbortSignal) =>
      pedir<CuestionarioApi>("/mi/cuestionario", senal ? { senal } : {}),
    enviarCuestionario: (envio: EnvioDeCuestionarioApi) =>
      pedir<void>("/mi/cuestionario", { metodo: "POST", cuerpo: envio }),
    plan: (senal?: AbortSignal) => pedir<PlanesDeAlumnaApi>("/mi/plan", senal ? { senal } : {}),

    /** Abre el chequeo del ciclo, o devuelve el que ya estaba abierto. Es idempotente. */
    abrirChequeo: () => pedir<BorradorApi>("/mi/chequeo", { metodo: "POST" }),
    guardarChequeo: (ulid: string, cambios: GuardadoDeChequeoApi) =>
      pedir<BorradorApi>(`/mi/chequeo/${ulid}`, { metodo: "PUT", cuerpo: cambios }),
    enviarChequeo: (ulid: string) =>
      pedir<BorradorApi>(`/mi/chequeo/${ulid}/enviar`, { metodo: "POST" }),

    /** El original no se guarda: el servidor recorta cabeza y cuello antes de tocar disco. */
    subirFoto: (chequeoUlid: string, angulo: Angulo, archivo: File) =>
      subir<FotoSubidaApi>(`/mi/chequeos/${chequeoUlid}/fotos/${angulo}`, archivo, "PUT"),
    borrarFoto: (chequeoUlid: string, angulo: Angulo) =>
      pedir<void>(`/mi/chequeos/${chequeoUlid}/fotos/${angulo}`, { metodo: "DELETE" }),

    /** Sus cobros: de aquí elige cuál está pagando. */
    cobros: (senal?: AbortSignal) => pedir<CobroApi2[]>("/mi/cobros", senal ? { senal } : {}),
    subirComprobante: (cobroUlid: string, archivo: File) =>
      subir<CobroApi2>(`/mi/cobros/${cobroUlid}/comprobante`, archivo, "POST"),

    mensajes: (senal?: AbortSignal) =>
      pedir<MensajeApi[]>("/mi/mensajes", senal ? { senal } : {}),
    escribir: (cuerpo: string) =>
      pedir<MensajeApi>("/mi/mensajes", { metodo: "POST", cuerpo: { cuerpo } }),

    /** Los avisos de su coach. Pedirlos los marca como leídos. */
    avisos: (senal?: AbortSignal) =>
      pedir<AvisoDeAlumnaApi[]>("/mi/avisos", senal ? { senal } : {}),
  },

  /** Panel del superadmin. Requiere rol `admin_plataforma`; una coach recibe 403. */
  plataforma: {
    coaches: (senal?: AbortSignal) =>
      pedir<FilaDeCoachApi[]>("/plataforma/coaches", senal ? { senal } : {}),
    darDeAltaCoach: (c: AltaDeCoachApi) =>
      pedir<{ coachUlid: string; email: string; claveTemporal: string }>("/plataforma/coaches", {
        metodo: "POST",
        cuerpo: c,
      }),
    editarCoach: (ulid: string, c: EdicionDeCoachApi) =>
      pedir<FilaDeCoachApi>(`/plataforma/coaches/${ulid}`, { metodo: "PUT", cuerpo: c }),

    editarSuscripcion: (ulid: string, s: EdicionDeSuscripcionApi) =>
      pedir<SuscripcionApi>(`/plataforma/coaches/${ulid}/suscripcion`, {
        metodo: "PUT",
        cuerpo: s,
      }),
    cobros: (ulid: string, senal?: AbortSignal) =>
      pedir<CobroApi[]>(`/plataforma/coaches/${ulid}/cobros`, senal ? { senal } : {}),
    registrarCobro: (ulid: string, c: CobroNuevoApi) =>
      pedir<CobroApi>(`/plataforma/coaches/${ulid}/cobros`, { metodo: "POST", cuerpo: c }),

    facturacion: (meses = 12, senal?: AbortSignal) =>
      pedir<FacturacionApi>(`/plataforma/facturacion?meses=${meses}`, senal ? { senal } : {}),
    salud: (senal?: AbortSignal) => pedir<SaludApi>("/plataforma/salud", senal ? { senal } : {}),
    auditoria: (limite = 100, senal?: AbortSignal) =>
      pedir<MovimientoDeAuditoriaApi[]>(
        `/plataforma/auditoria?limite=${limite}`,
        senal ? { senal } : {},
      ),
  },

  /** Sin sesión: el aviso de privacidad se lee antes de entregar ningún dato. */
  legales: {
    documento: (clave: string, coach: string | null, senal?: AbortSignal) =>
      pedir<DocumentoLegalApi>(
        `/legales/${clave}${coach ? `?coach=${encodeURIComponent(coach)}` : ""}`,
        senal ? { senal } : {},
      ),
  },

  push: {
    llave: (senal?: AbortSignal) =>
      pedir<{ publica: string }>("/push/llave", senal ? { senal } : {}),
    suscribir: (s: { endpoint: string; p256dh: string; auth: string }) =>
      pedir<void>("/mi/push", { metodo: "POST", cuerpo: s }),
    desuscribir: () => pedir<void>("/mi/push", { metodo: "DELETE" }),
  },

  coach: {
    panel: (senal?: AbortSignal) => pedir<ResumenPanelApi>("/coach/panel", senal ? { senal } : {}),
    alumnas: (senal?: AbortSignal) =>
      pedir<FilaCarteraApi[]>("/coach/alumnas", senal ? { senal } : {}),

    agenda: (desde: string, dias = 7, senal?: AbortSignal) =>
      pedir<AgendaApi>(
        `/coach/agenda?desde=${encodeURIComponent(desde)}&dias=${dias}`,
        senal ? { senal } : {},
      ),
    citasDeAlumna: (alumnaUlid: string, senal?: AbortSignal) =>
      pedir<CitaDeAlumnaApi[]>(`/coach/alumnas/${alumnaUlid}/citas`, senal ? { senal } : {}),
    agendar: (cita: CitaNuevaApi) => pedir<CitaApi>("/coach/agenda", { metodo: "POST", cuerpo: cita }),
    editarCita: (ulid: string, cita: CitaNuevaApi) =>
      pedir<CitaApi>(`/coach/agenda/${ulid}`, { metodo: "PUT", cuerpo: cita }),
    cancelarCita: (ulid: string, motivo: string) =>
      pedir<CitaApi>(`/coach/agenda/${ulid}/cancelar`, { metodo: "POST", cuerpo: { motivo } }),
    eliminarCita: (ulid: string) => pedir<void>(`/coach/agenda/${ulid}`, { metodo: "DELETE" }),

    estimarGrasa: (chequeoUlid: string, porcentajeGrasa: number) =>
      pedir<void>(`/coach/chequeos/${chequeoUlid}/grasa`, {
        metodo: "PUT",
        cuerpo: { porcentajeGrasa },
      }),
    validarChequeo: (chequeoUlid: string, feedback: string, justificacionOutlier?: string) =>
      pedir<void>(`/coach/chequeos/${chequeoUlid}/validar`, {
        metodo: "POST",
        cuerpo: { feedback, justificacionOutlier: justificacionOutlier ?? null },
      }),
    rechazarChequeo: (chequeoUlid: string, motivo: string) =>
      pedir<void>(`/coach/chequeos/${chequeoUlid}/rechazar`, {
        metodo: "POST",
        cuerpo: { motivo },
      }),

    darDeAlta: (alumna: AltaDeAlumnaApi) =>
      pedir<AlumnaDadaDeAltaApi>("/coach/alumnas", { metodo: "POST", cuerpo: alumna }),
    editarAlumna: (ulid: string, alumna: EdicionDeAlumnaApi) =>
      pedir<FilaCarteraApi>(`/coach/alumnas/${ulid}`, { metodo: "PUT", cuerpo: alumna }),
    darDeBaja: (ulid: string) => pedir<void>(`/coach/alumnas/${ulid}`, { metodo: "DELETE" }),
    claveTemporal: (ulid: string, motivoVerificacion: string) =>
      pedir<{ clave: string; venceEn: string }>(`/coach/alumnas/${ulid}/clave-temporal`, {
        metodo: "POST",
        cuerpo: { motivoVerificacion },
      }),

    servicios: (senal?: AbortSignal) =>
      pedir<ServicioApi[]>("/coach/servicios", senal ? { senal } : {}),
    crearServicio: (x: ServicioNuevoApi) =>
      pedir<ServicioApi>("/coach/servicios", { metodo: "POST", cuerpo: x }),
    editarServicio: (ulid: string, x: ServicioNuevoApi) =>
      pedir<ServicioApi>(`/coach/servicios/${ulid}`, { metodo: "PUT", cuerpo: x }),
    borrarServicio: (ulid: string) =>
      pedir<void>(`/coach/servicios/${ulid}`, { metodo: "DELETE" }),

    planes: (senal?: AbortSignal) =>
      pedir<PlanComercialApi[]>("/coach/tarifas", senal ? { senal } : {}),
    crearPlan: (p: PlanComercialNuevoApi) =>
      pedir<PlanComercialApi>("/coach/tarifas", { metodo: "POST", cuerpo: p }),
    editarPlan: (ulid: string, p: PlanComercialNuevoApi) =>
      pedir<PlanComercialApi>(`/coach/tarifas/${ulid}`, { metodo: "PUT", cuerpo: p }),
    desactivarPlan: (ulid: string) =>
      pedir<void>(`/coach/tarifas/${ulid}`, { metodo: "DELETE" }),

    cobros: (alumnaUlid: string, senal?: AbortSignal) =>
      pedir<CobroApi2[]>(`/coach/alumnas/${alumnaUlid}/cobros`, senal ? { senal } : {}),
    programarCobro: (alumnaUlid: string, c: CobroNuevoProgramadoApi) =>
      pedir<CobroApi2>(`/coach/alumnas/${alumnaUlid}/cobros`, { metodo: "POST", cuerpo: c }),
    cancelarCobro: (ulid: string) => pedir<void>(`/coach/cobros/${ulid}`, { metodo: "DELETE" }),
    comprobantes: (senal?: AbortSignal) =>
      pedir<ComprobantePorRevisarApi[]>("/coach/comprobantes", senal ? { senal } : {}),
    validarComprobante: (cobroUlid: string) =>
      pedir<void>(`/coach/cobros/${cobroUlid}/validar`, { metodo: "POST" }),
    rechazarComprobante: (cobroUlid: string, motivo: string) =>
      pedir<void>(`/coach/cobros/${cobroUlid}/rechazar`, { metodo: "POST", cuerpo: { motivo } }),

    aQuienCobrar: (texto: string, senal?: AbortSignal) =>
      pedir<AlumnaConCobrosApi[]>(
        `/coach/cobrar?q=${encodeURIComponent(texto)}`,
        senal ? { senal } : {},
      ),

    anuncios: (senal?: AbortSignal) =>
      pedir<AnuncioApi[]>("/coach/anuncios", senal ? { senal } : {}),
    enviarAnuncio: (a: { titulo: string; cuerpo: string; alumnas: string[] }) =>
      pedir<AnuncioApi>("/coach/anuncios", { metodo: "POST", cuerpo: a }),

    marca: (senal?: AbortSignal) => pedir<MarcaApi>("/coach/marca", senal ? { senal } : {}),
    guardarMarca: (m: { nombre: string; marca: string; colorAcento: string }) =>
      pedir<MarcaApi>("/coach/marca", { metodo: "PUT", cuerpo: m }),
    subirLogo: (archivo: File) => subir<MarcaApi>("/coach/logo", archivo, "PUT"),

    validacion: (alumnaUlid: string, senal?: AbortSignal) =>
      pedir<ExpedienteDeValidacionApi>(
        `/coach/alumnas/${alumnaUlid}/validacion`,
        senal ? { senal } : {},
      ),

    /** Abrir las fotos de un chequeo queda registrado en la bitácora de accesos. */
    fotosDeChequeo: (chequeoUlid: string, senal?: AbortSignal) =>
      pedir<FotoApi[]>(`/coach/chequeos/${chequeoUlid}/fotos`, senal ? { senal } : {}),
    /** Igual que las fotos: cada lectura del historial clínico se anota. */
    historial: (alumnaUlid: string, senal?: AbortSignal) =>
      pedir<HistorialApi>(`/coach/alumnas/${alumnaUlid}/historial`, senal ? { senal } : {}),

    alimentos: (q: string, senal?: AbortSignal) =>
      pedir<AlimentoCatalogoApi[]>(
        `/coach/alimentos?q=${encodeURIComponent(q)}`,
        senal ? { senal } : {},
      ),
    ejercicios: (q: string, senal?: AbortSignal) =>
      pedir<EjercicioCatalogoApi[]>(
        `/coach/ejercicios?q=${encodeURIComponent(q)}`,
        senal ? { senal } : {},
      ),
    presentacion: (senal?: AbortSignal) =>
      pedir<PresentacionApi>("/coach/presentacion", senal ? { senal } : {}),
    guardarPresentacion: (p: {
      titulo: string;
      texto: string;
      ficha: DatoDeFichaApi[];
      activa: boolean;
    }) => pedir<PresentacionApi>("/coach/presentacion", { metodo: "PUT", cuerpo: p }),
    subirFotoDePresentacion: (archivo: File) =>
      subir<PresentacionApi>("/coach/presentacion/foto", archivo, "PUT"),

    preguntas: (senal?: AbortSignal) =>
      pedir<PreguntaApi[]>("/coach/preguntas", senal ? { senal } : {}),
    crearPregunta: (p: PreguntaNuevaApi) =>
      pedir<PreguntaApi>("/coach/preguntas", { metodo: "POST", cuerpo: p }),
    editarPregunta: (ulid: string, p: PreguntaNuevaApi) =>
      pedir<PreguntaApi>(`/coach/preguntas/${ulid}`, { metodo: "PUT", cuerpo: p }),
    quitarPregunta: (ulid: string) =>
      pedir<void>(`/coach/preguntas/${ulid}`, { metodo: "DELETE" }),
    respuestasDeAlumna: (alumnaUlid: string, senal?: AbortSignal) =>
      pedir<RespuestaDeAlumnaApi[]>(
        `/coach/alumnas/${alumnaUlid}/cuestionario`,
        senal ? { senal } : {},
      ),

    fotosDeComida: (alumnaUlid: string, senal?: AbortSignal) =>
      pedir<FotoDeComidaApi[]>(
        `/coach/alumnas/${alumnaUlid}/fotos-comida`,
        senal ? { senal } : {},
      ),
    comentarFotoDeComida: (ulid: string, comentario: string) =>
      pedir<FotoDeComidaApi>(`/coach/fotos-comida/${ulid}/comentario`, {
        metodo: "POST",
        cuerpo: { comentario },
      }),

    hoja: (alumnaUlid: string, senal?: AbortSignal) =>
      pedir<HojaDeCalculoApi>(`/coach/hoja/${alumnaUlid}`, senal ? { senal } : {}),

    expedienteDePlan: (alumnaUlid: string, senal?: AbortSignal) =>
      pedir<ExpedienteDeConstructorApi>(
        `/coach/planes/${alumnaUlid}`,
        senal ? { senal } : {},
      ),
    guardarPlan: (alumnaUlid: string, plan: PlanGuardadoApi) =>
      pedir<void>(`/coach/planes/${alumnaUlid}`, { metodo: "PUT", cuerpo: plan }),

    finanzas: (meses = 12, senal?: AbortSignal) =>
      pedir<PanelFinancieroApi>(`/coach/finanzas?meses=${meses}`, senal ? { senal } : {}),
    crearMovimiento: (m: MovimientoNuevoApi) =>
      pedir<MovimientoApi>("/coach/finanzas/movimientos", { metodo: "POST", cuerpo: m }),
    editarMovimiento: (ulid: string, m: MovimientoNuevoApi) =>
      pedir<MovimientoApi>(`/coach/finanzas/movimientos/${ulid}`, { metodo: "PUT", cuerpo: m }),
    eliminarMovimiento: (ulid: string) =>
      pedir<void>(`/coach/finanzas/movimientos/${ulid}`, { metodo: "DELETE" }),

    mensajes: (alumnaUlid: string, senal?: AbortSignal) =>
      pedir<MensajeApi[]>(`/coach/mensajes/${alumnaUlid}`, senal ? { senal } : {}),
    responder: (alumnaUlid: string, cuerpo: string) =>
      pedir<MensajeApi>(`/coach/mensajes/${alumnaUlid}`, { metodo: "POST", cuerpo: { cuerpo } }),

    tarifas: (senal?: AbortSignal) =>
      pedir<TarifaApi[]>("/coach/finanzas/tarifas", senal ? { senal } : {}),
    crearTarifa: (t: Omit<TarifaApi, "ulid">) =>
      pedir<TarifaApi>("/coach/finanzas/tarifas", { metodo: "POST", cuerpo: t }),
    editarTarifa: (ulid: string, t: Omit<TarifaApi, "ulid">) =>
      pedir<TarifaApi>(`/coach/finanzas/tarifas/${ulid}`, { metodo: "PUT", cuerpo: t }),
    desactivarTarifa: (ulid: string) =>
      pedir<void>(`/coach/finanzas/tarifas/${ulid}`, { metodo: "DELETE" }),
  },
};

/** Dirección de una fotografía de chequeo.
 *
 *  Se pone directamente en el `src` de un `<img>`: la cookie de sesión viaja sola y nginx
 *  entrega el archivo con `X-Accel-Redirect`, sin que Python lo cargue en memoria. Cada
 *  apertura queda anotada en la bitácora de accesos.
 */
export function urlDeFoto(chequeoUlid: string, angulo: string, mini = false): string {
  return `${BASE}/fotos/${chequeoUlid}/${angulo}${mini ? "?mini=true" : ""}`;
}

/** La imagen del comprobante de un cobro. La ven la coach y la propia alumna. */
export function urlDeComprobante(cobroUlid: string): string {
  return `${BASE}/coach/cobros/${cobroUlid}/comprobante`;
}

/** El logo de la marca del inquilino en curso. `v` fuerza recarga tras subir uno nuevo. */
export function urlDeLogo(version = 0): string {
  return `${BASE}/logo${version ? `?v=${version}` : ""}`;
}

/** La imagen de una foto de comida. Devuelve 404 en cuanto expira. */
export function urlDeFotoDeComida(ulid: string): string {
  return `${BASE}/fotos-comida/${ulid}/imagen`;
}

/** Foto de la coach para su presentación. La versión evita servir la anterior en caché. */
export function urlDeFotoDeCoach(version = 0): string {
  return `${BASE}/presentacion/foto${version ? `?v=${version}` : ""}`;
}

/** Descarga un PDF.
 *
 *  No usa `pedir` porque la respuesta es binaria. El navegador lo guarda con el nombre que
 *  manda el servidor en `Content-Disposition`.
 */
export async function descargarPdf(ruta: string, nombreSugerido: string): Promise<void> {
  const respuesta = await fetch(`${BASE}${ruta}`, { credentials: "include" });
  if (!respuesta.ok) {
    const texto = await respuesta.text();
    let mensaje = "No se pudo generar el documento.";
    try {
      const d = JSON.parse(texto) as { codigo?: string; mensaje?: string; detail?: unknown };
      revisarSesion(respuesta.status, codigoDe(d));
      mensaje = d.mensaje ?? mensaje;
    } catch {
      revisarSesion(respuesta.status);
      /* respuesta no JSON: se queda el mensaje genérico */
    }
    throw new ErrorApi(respuesta.status, null, mensaje);
  }

  const blob = await respuesta.blob();
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombreSugerido;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  // Sin revocar, cada descarga deja el archivo en memoria hasta recargar la página.
  URL.revokeObjectURL(url);
}
