/** Inicio de la alumna: qué le toca hoy.
 *
 *  Editorial y calmado — la pantalla abre con el dato, no con adorno. Todo lo que no es
 *  «qué hago ahora» se va bajando, y lo secundario (cuenta, mensajes, avisos) vive al pie
 *  para no gastar una pestaña en ello.
 */

import { ArrowRight, Loader2, LogOut, MessageSquare, ShieldCheck, Upload, User } from "lucide-react";
import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { cerrarSesion } from "@/lib/sesion";

import { AvisoSinServidor, Cargando } from "@/componentes/Estado";
import { Apoyo, Aviso, Boton, Chip, Dato, Etiqueta, Portada, Regla, Tarjeta, Titulo } from "@/componentes/primitivas";
import {
  ErrorApi,
  api,
  type CitaDeAlumnaApi,
  type ComprobanteApi,
  type InicioAlumnaApi,
} from "@/lib/api";
import { chequeos, ciclo, mensajes, notificaciones, planEntrenamiento, planNutricion, alumna } from "@/lib/datos";
import { delta, diaSemana, fecha, num } from "@/lib/formato";
import { usarApiConRespaldo } from "@/lib/usarApi";
import { ROTULO_ESTADO, type EstadoChequeo } from "@/lib/tipos";

/** Datos de ejemplo para revisar la pantalla sin servidor. Desaparece con la API en pie. */
const RESPALDO: InicioAlumnaApi = {
  perfil: {
    ulid: alumna.ulid,
    nombre: alumna.nombre,
    correo: alumna.email,
    estaturaCm: alumna.estaturaCm,
    plan: null,
    basculaRef: alumna.basculaRef,
    lugarRef: alumna.lugarRef,
    horaRef: alumna.horaRef,
    zonaHoraria: alumna.zonaHoraria,
  },
  ciclo: {
    numero: ciclo.numero,
    iniciaEn: ciclo.iniciaEn,
    terminaEn: ciclo.terminaEn,
    estadoPago: ciclo.estadoPago,
    precio: ciclo.precio,
  },
  chequeos,
  ultimoFeedback: [...chequeos].reverse().find((c) => c.feedback)?.feedback ?? null,
  avisosSinLeer: notificaciones.filter((n) => !n.leida).length,
  coach: "Mariana Cervantes",
  proximasCitas: [],
};

export function Inicio() {
  const navegar = useNavigate();
  const { datos, cargando, sinServidor, mensaje } = usarApiConRespaldo<InicioAlumnaApi>(
    (senal) => api.alumna.inicio(senal),
    RESPALDO,
  );

  if (cargando) return <Cargando que="tu inicio" />;

  const historico = datos.chequeos;
  const ultimo = historico.at(-1)!;
  const previo = historico.at(-2) ?? ultimo;
  const base = historico[0]!;
  const primerNombre = datos.perfil.nombre.split(" ")[0];
  const nombreCoach = datos.coach.split(" ")[0];

  const dPeso = delta(ultimo.pesoKg ?? 0, previo.pesoKg, "kg");
  const dCintura = delta(ultimo.medidas.cintura ?? 0, previo.medidas.cintura, "cm");
  const dTotal = delta(ultimo.pesoKg ?? 0, base.pesoKg, "kg");

  return (
    <div className="flex flex-col gap-12">
      {/* ---- Encabezado ---- */}
      <header className="flex flex-col gap-3">
        <Etiqueta>{diaSemana("2026-08-13")}</Etiqueta>
        <Portada>Hola, {primerNombre}</Portada>
        {datos.ciclo ? (
          <Apoyo>
            Ciclo {datos.ciclo.numero} · termina el {fecha(datos.ciclo.terminaEn)}
          </Apoyo>
        ) : null}
      </header>

      {sinServidor ? <AvisoSinServidor mensaje={mensaje} /> : null}

      {datos.avisosSinLeer > 0 ? (
        <Aviso
          tono="atencion"
          titulo={datos.avisosSinLeer === 1 ? "Tienes un aviso" : `Tienes ${datos.avisosSinLeer} avisos`}
        >
          {notificaciones.find((n) => !n.leida)?.texto ?? "Revisa tus avisos."}
        </Aviso>
      ) : null}

      <ProximasFechas ciclo={datos.ciclo} citas={datos.proximasCitas} />

      {datos.ciclo ? (
        <SubirComprobante precio={datos.ciclo.precio} estado={datos.ciclo.estadoPago} />
      ) : null}

      {/* ---- Lo que toca hoy ---- */}
      <section className="filete flex flex-col gap-4">
        <Etiqueta>Hoy te toca</Etiqueta>
        <div className="flex flex-col gap-1">
          <Titulo>{planEntrenamiento.dias[0]!.nombre}</Titulo>
          <Apoyo>
            {planEntrenamiento.dias[0]!.ejercicios.length} ejercicios · {planNutricion.kcal} kcal
          </Apoyo>
        </div>
        <div>
          <Boton asChild medida="grande">
            <Link to="/plan">
              Abrir mi plan <ArrowRight className="size-4" />
            </Link>
          </Boton>
        </div>
      </section>

      <Regla />

      {/* ---- Cifras ---- */}
      <section className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-3">
        <Dato
          rotulo="Peso"
          valor={num(ultimo.pesoKg)}
          unidad="kg"
          nota={dPeso ? `${dPeso.texto} desde julio` : undefined}
          direccion={dPeso?.direccion}
        />
        <Dato
          rotulo="Cintura"
          valor={num(ultimo.medidas.cintura)}
          unidad="cm"
          nota={dCintura ? `${dCintura.texto} desde julio` : undefined}
          direccion={dCintura?.direccion}
        />
        <Dato
          rotulo="Desde que empezaste"
          valor={num(Math.abs(dTotal?.valor ?? 0))}
          unidad="kg"
          nota={`${(dTotal?.valor ?? 0) < 0 ? "menos" : "más"} en ${historico.length} chequeos`}
        />
      </section>

      <Regla />

      {/* ---- Chequeo del mes ---- */}
      <Tarjeta acentuada className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <Etiqueta>
              Chequeo #{ultimo.numero} · {fecha(ultimo.fecha)}
            </Etiqueta>
            <Titulo>{nombreCoach} lo está revisando</Titulo>
          </div>
          <Chip tono="espera">{ROTULO_ESTADO[ultimo.estado as EstadoChequeo]}</Chip>
        </div>
        <Apoyo className="medida">
          Enviaste tus ocho medidas, tu peso y las tres fotos el {fecha(ultimo.fecha)}. En cuanto lo
          valide te avisamos y se libera tu plan del ciclo siguiente.
        </Apoyo>
        <div className="flex flex-wrap gap-2">
          <Boton asChild tono="contorno">
            <Link to="/evolucion">Ver lo que enviaste</Link>
          </Boton>
          <Boton asChild tono="discreto">
            <Link to="/chequeo">Empezar el del mes que entra</Link>
          </Boton>
        </div>
      </Tarjeta>

      {/* ---- Último feedback ---- */}
      {datos.ultimoFeedback ? (
        <section className="flex flex-col gap-3">
          <Etiqueta>Lo último que te dijo {nombreCoach}</Etiqueta>
          <blockquote className="medida text-guia leading-relaxed text-balance">
            «{datos.ultimoFeedback}»
          </blockquote>
          <Apoyo>{mensajes.length} mensajes en tu hilo</Apoyo>
        </section>
      ) : null}

      <Regla />

      {/* ---- Lo secundario, al pie: no gasta una pestaña ---- */}
      <nav aria-label="Más opciones" className="flex flex-wrap gap-2">
        <Boton asChild tono="discreto" medida="chica">
          <Link to="/mensajes">
            <MessageSquare className="size-4" /> Mensajes
          </Link>
        </Boton>
        <Boton asChild tono="discreto" medida="chica">
          <Link to="/cuenta">
            <User className="size-4" /> Mi cuenta
          </Link>
        </Boton>
        <Boton asChild tono="discreto" medida="chica">
          <Link to="/cuenta">
            <ShieldCheck className="size-4" /> Privacidad
          </Link>
        </Boton>
        <Boton
          tono="discreto"
          medida="chica"
          className="ml-auto"
          onClick={() => {
            cerrarSesion();
            navegar("/acceso", { replace: true });
          }}
        >
          <LogOut className="size-4" /> Salir
        </Boton>
      </nav>
    </div>
  );
}

/* ---------------------------------------------------- Próximas fechas --- */

const ROTULO_MODALIDAD: Record<string, string> = {
  video: "Videollamada",
  presencial: "Presencial",
  telefono: "Llamada",
};

/** Días que faltan, contando por día calendario y no por horas.
 *
 *  Una cita de mañana a las 9 está a 14 horas, pero decir «en 0 días» sería absurdo: lo que
 *  la alumna piensa es «mañana».
 */
function diasHasta(iso: string): number {
  const objetivo = new Date(iso);
  const hoy = new Date();
  objetivo.setHours(0, 0, 0, 0);
  hoy.setHours(0, 0, 0, 0);
  return Math.round((objetivo.getTime() - hoy.getTime()) / 86_400_000);
}

function cuando(dias: number): string {
  if (dias <= 0) return "hoy";
  if (dias === 1) return "mañana";
  return `en ${dias} días`;
}

/** Lo que viene: el pago del ciclo y las consultas agendadas.
 *
 *  Van juntos porque son las dos únicas fechas que la alumna tiene que recordar, y estaban
 *  repartidas entre dos pantallas distintas.
 */
function ProximasFechas({
  ciclo,
  citas,
}: {
  ciclo: InicioAlumnaApi["ciclo"];
  citas: CitaDeAlumnaApi[];
}) {
  if (!ciclo && citas.length === 0) return null;

  const diasParaPago = ciclo ? diasHasta(ciclo.terminaEn) : null;
  const vencido = diasParaPago !== null && diasParaPago < 0;
  const urgePago = diasParaPago !== null && diasParaPago >= 0 && diasParaPago <= 5;

  return (
    <section className="flex flex-col gap-4">
      <Etiqueta>Próximas fechas</Etiqueta>

      <ul className="flex flex-col divide-y divide-linea border-y border-linea">
        {ciclo ? (
          <li className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3">
            <span className="flex min-w-0 flex-col gap-0.5">
              <span className="text-menor font-medium">
                {ciclo.estadoPago === "validado" ? "Renovación de tu ciclo" : "Pago de tu ciclo"}
              </span>
              <span className="text-micro text-tinta-suave">
                Ciclo {ciclo.numero} · ${num(ciclo.precio)}
              </span>
            </span>
            <span className="flex items-baseline gap-3">
              <span className="cifra text-menor">{fecha(ciclo.terminaEn)}</span>
              <Chip tono={vencido ? "error" : urgePago ? "espera" : "neutro"}>
                {vencido ? "vencido" : cuando(diasParaPago ?? 0)}
              </Chip>
            </span>
          </li>
        ) : null}

        {citas.map((c) => {
          const dias = diasHasta(c.iniciaEn);
          return (
            <li
              key={c.ulid}
              className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3"
            >
              <span className="flex min-w-0 flex-col gap-0.5">
                <span className="text-menor font-medium">{c.titulo}</span>
                <span className="text-micro text-tinta-suave">
                  {ROTULO_MODALIDAD[c.modalidad] ?? c.modalidad}
                  {c.estado === "confirmada" ? " · confirmada" : ""}
                </span>
              </span>
              <span className="flex items-baseline gap-3">
                <span className="cifra text-menor">
                  {fecha(c.iniciaEn)} · {c.iniciaEn.slice(11, 16)}
                </span>
                <Chip tono={dias <= 1 ? "espera" : "neutro"}>{cuando(dias)}</Chip>
              </span>
            </li>
          );
        })}
      </ul>

      {citas.length === 0 ? (
        <Apoyo>No tienes consultas agendadas. Tu coach te avisa cuando agende una.</Apoyo>
      ) : null}
    </section>
  );
}

/* -------------------------------------------------- Comprobante de pago --- */

/** Subida del comprobante del ciclo.
 *
 *  El servidor lo lee con OCR y devuelve lo que entendió. **Eso no valida el pago**: la coach
 *  lo confirma contra su estado de cuenta. Un comprobante es una imagen que cualquiera puede
 *  editar, y ningún grado de confianza automática sustituye a que alguien mire el banco. Por
 *  eso la pantalla dice «recibido», nunca «pagado».
 */
function SubirComprobante({ precio, estado }: { precio: number; estado: string }) {
  const entrada = useRef<HTMLInputElement>(null);
  const [subiendo, setSubiendo] = useState(false);
  const [lectura, setLectura] = useState<ComprobanteApi | null>(null);
  const [error, setError] = useState<string | null>(null);
  const validado = estado === "validado";

  async function subir(archivo: File) {
    setError(null);
    setSubiendo(true);
    try {
      setLectura(await api.alumna.subirComprobante(archivo));
    } catch (causa: unknown) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo subir el comprobante.");
    } finally {
      setSubiendo(false);
      if (entrada.current) entrada.current.value = "";
    }
  }

  return (
    <Tarjeta className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <Etiqueta>Pago del ciclo</Etiqueta>
          <Titulo>
            {validado
              ? "Tu ciclo está pagado"
              : lectura
                ? "Comprobante recibido"
                : "Falta tu comprobante"}
          </Titulo>
        </div>
        <Chip tono={validado ? "exito" : estado === "rechazado" ? "error" : "espera"}>
          {validado ? "Validado" : estado === "rechazado" ? "Rechazado" : "Pendiente"}
        </Chip>
      </div>

      <Apoyo className="medida">
        {validado
          ? `Tu coach ya validó los $${num(precio)} de este ciclo. Si necesitas subir otro comprobante —una corrección, un pago adelantado— puedes hacerlo desde aquí.`
          : `Sube la captura de tu transferencia de $${num(precio)}. Tu coach la confirma contra su estado de cuenta; en cuanto lo haga se libera tu plan y te llega el recibo por correo.`}
      </Apoyo>

      {lectura ? (
        <Aviso tono={lectura.requiereRevision ? "atencion" : "exito"} titulo="Lo que leímos">
          <ul className="flex flex-col gap-0.5">
            <li>Monto: {lectura.monto !== null ? `$${num(lectura.monto)}` : "no se pudo leer"}</li>
            <li>Fecha: {lectura.fecha ? fecha(lectura.fecha) : "no se pudo leer"}</li>
            <li>Referencia: {lectura.referencia ?? "no se pudo leer"}</li>
            <li>Banco: {lectura.banco ?? "no se pudo leer"}</li>
          </ul>
          <p className="mt-2">
            {lectura.requiereRevision
              ? "Algunos datos no se leyeron bien. No pasa nada: tu coach lo revisa a ojo."
              : "Tu coach lo revisa y te confirma."}
          </p>
        </Aviso>
      ) : null}

      {error ? <Aviso tono="error">{error}</Aviso> : null}

      <input
        ref={entrada}
        type="file"
        accept="image/*,application/pdf"
        className="hidden"
        onChange={(e) => {
          const archivo = e.target.files?.[0];
          if (archivo) void subir(archivo);
        }}
      />

      <div>
        <Boton
          tono={validado ? "contorno" : "solido"}
          disabled={subiendo}
          onClick={() => entrada.current?.click()}
        >
          {subiendo ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
          {lectura || validado ? "Subir otro comprobante" : "Subir comprobante"}
        </Boton>
      </div>
    </Tarjeta>
  );
}
