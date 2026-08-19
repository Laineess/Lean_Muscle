/** El recorrido de quien se registró por la liga de su coach, hasta que la acepten.
 *
 *  Es su pantalla de inicio mientras dura: el panel de alumna no le sirve todavía —no tiene
 *  plan, ni chequeo, ni historial— y enseñárselo vacío sería prometerle algo que aún no
 *  existe. Aquí solo ve lo que le falta, en orden, y cuánto tiempo tiene para terminarlo.
 */

import { ArrowRight, Check, Loader2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Cargando } from "@/componentes/Estado";
import {
  Apoyo,
  Aviso,
  Boton,
  Chip,
  Etiqueta,
  Portada,
  Regla,
  Tarjeta,
  Titulo,
} from "@/componentes/primitivas";
import { BotonSalir } from "@/componentes/Seguridad";
import {
  ErrorApi,
  api,
  type CobroApi2,
  type EstadoDeSolicitudApi,
  type PasoDeSolicitud,
} from "@/lib/api";
import { fecha, horaLocal, num } from "@/lib/formato";
import { usarApi } from "@/lib/usarApi";

interface Escalon {
  paso: PasoDeSolicitud;
  titulo: string;
  detalle: string;
}

const ESCALONES: Escalon[] = [
  {
    paso: "cuestionario",
    titulo: "Conoce a tu coach y contesta",
    detalle: "Lesiones, condiciones y el plan que quieres. De ahí sale tu primer plan.",
  },
  {
    paso: "cita",
    titulo: "Reserva tu primera consulta",
    detalle: "Eliges la hora que te acomode de las que tu coach tiene abiertas.",
  },
  {
    paso: "comprobante",
    titulo: "Sube tu comprobante de inscripción",
    detalle: "Se paga una sola vez, al entrar.",
  },
];

/** Cuántos días le quedan antes de que su registro se borre solo. */
function diasPara(iso: string): number {
  const falta = new Date(iso).getTime() - Date.now();
  return Math.max(0, Math.ceil(falta / 86_400_000));
}

export function Solicitud() {
  const navegar = useNavigate();
  const carga = usarApi<EstadoDeSolicitudApi>((s) => api.alumna.solicitud(s));

  if (carga.cargando) return <Cargando que="tu registro" />;

  if (carga.error) {
    return (
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-5 py-12">
        <Aviso tono="error">{carga.error.message}</Aviso>
      </div>
    );
  }

  const s = carga.datos!;

  // Ya la aceptaron: su sitio es el panel, no esta pantalla.
  if (!s.esSolicitud) {
    void navegar("/inicio", { replace: true });
    return null;
  }

  const hechos = new Set<PasoDeSolicitud>();
  if (s.cuestionarioCompleto) hechos.add("cuestionario");
  if (s.tieneCita) hechos.add("cita");
  if (s.comprobanteSubido) hechos.add("comprobante");

  const quedan = s.venceEn ? diasPara(s.venceEn) : null;
  const termino = s.paso === "espera" || s.paso === "lista";

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 px-5 py-12">
      <header className="flex flex-col gap-3">
        <Etiqueta>{s.coach}</Etiqueta>
        <Portada>{termino ? "Ya está todo de tu lado" : "Te falta poco"}</Portada>
        <Apoyo>
          {termino
            ? "Tu coach revisa tu solicitud y confirma tu consulta. Te avisamos por correo en cuanto lo haga."
            : "Termina estos pasos y tu coach recibe tu solicitud."}
        </Apoyo>
      </header>

      {!termino && quedan !== null ? (
        <Aviso tono={quedan <= 2 ? "atencion" : "info"}>
          Lo que capturaste se guarda {quedan === 1 ? "un día" : `${quedan} días`} más. Si no
          terminas, se borra solo: es tu dato y no lo guardamos de más.
        </Aviso>
      ) : null}

      <ol className="flex flex-col divide-y divide-linea border-y border-linea">
        {ESCALONES.map((escalon, i) => {
          const hecho = hechos.has(escalon.paso);
          const actual = !termino && s.paso === escalon.paso;
          return (
            <li key={escalon.paso} className="flex items-start gap-4 py-4">
              <span
                className={
                  hecho
                    ? "mt-0.5 grid size-6 shrink-0 place-items-center rounded-full bg-exito-sutil text-exito"
                    : actual
                      ? "cifra mt-0.5 grid size-6 shrink-0 place-items-center rounded-full border border-acento text-micro font-semibold"
                      : "cifra mt-0.5 grid size-6 shrink-0 place-items-center rounded-full border border-linea text-micro text-tinta-suave"
                }
              >
                {hecho ? <Check className="size-3.5" /> : i + 1}
              </span>

              <span className="flex min-w-0 flex-1 flex-col gap-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span
                    className={
                      hecho ? "text-menor font-medium text-tinta-suave" : "text-menor font-medium"
                    }
                  >
                    {escalon.titulo}
                  </span>
                  {hecho ? <Chip tono="exito">listo</Chip> : null}
                </span>
                <span className="text-micro text-tinta-suave">{escalon.detalle}</span>

                {escalon.paso === "cita" && s.citaIniciaEn ? (
                  <span className="cifra text-micro">
                    {fecha(s.citaIniciaEn)} · {horaLocal(s.citaIniciaEn)}
                  </span>
                ) : null}

                {actual ? <AccionDelPaso paso={escalon.paso} onHecho={carga.recargar} /> : null}
              </span>
            </li>
          );
        })}
      </ol>

      {termino ? <Espera /> : null}

      <Regla />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Apoyo>Entras con tu correo y la contraseña que elegiste.</Apoyo>
        <BotonSalir />
      </div>
    </div>
  );
}

function AccionDelPaso({ paso, onHecho }: { paso: PasoDeSolicitud; onHecho: () => void }) {
  if (paso === "cuestionario") {
    return (
      <span className="mt-2">
        <Boton asChild medida="chica">
          <Link to="/bienvenida">
            Empezar <ArrowRight className="size-3.5" />
          </Link>
        </Boton>
      </span>
    );
  }

  if (paso === "cita") {
    return (
      <span className="mt-2">
        <Boton asChild medida="chica">
          <Link to="/reservar">
            Ver horarios <ArrowRight className="size-3.5" />
          </Link>
        </Boton>
      </span>
    );
  }

  return <SubirInscripcion onHecho={onHecho} />;
}

/* --------------------------------------------------- Comprobante --- */

function SubirInscripcion({ onHecho }: { onHecho: () => void }) {
  const carga = usarApi<CobroApi2[]>((s) => api.alumna.cobros(s));
  const entrada = useRef<HTMLInputElement>(null);
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inscripcion = (carga.datos ?? []).find((c) => c.motivo === "inscripcion");
  if (!inscripcion) return null;

  async function subir(archivo: File) {
    if (!inscripcion) return;
    setError(null);
    setSubiendo(true);
    try {
      await api.alumna.subirComprobante(inscripcion.ulid, archivo);
      onHecho();
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo subir el comprobante.");
    } finally {
      setSubiendo(false);
      if (entrada.current) entrada.current.value = "";
    }
  }

  return (
    <span className="mt-2 flex flex-col gap-2">
      <span className="flex flex-wrap items-center gap-3">
        <span className="cifra font-semibold">${num(inscripcion.monto)}</span>
        <Boton
          medida="chica"
          disabled={subiendo}
          onClick={() => entrada.current?.click()}
        >
          {subiendo ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <Upload className="size-3.5" />
          )}
          Subir comprobante
        </Boton>
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
      </span>
      {error ? <Aviso tono="error">{error}</Aviso> : null}
    </span>
  );
}

/* --------------------------------------------------------- Espera --- */

function Espera() {
  return (
    <Tarjeta className="flex flex-col gap-3">
      <Titulo>Qué sigue</Titulo>
      <Apoyo>
        Tu coach revisa lo que capturaste, confirma tu consulta y valida tu pago. Cuando te
        acepte se abre tu primer chequeo, y ahí empieza el método: peso, medidas y fotos.
      </Apoyo>
      <Etiqueta>Mientras tanto no hace falta que hagas nada.</Etiqueta>
    </Tarjeta>
  );
}
