/** Validación de un chequeo: el «validation gate» del método.
 *
 *  Hasta que la coach valida, el plan del ciclo siguiente no se publica.
 *
 *  Reparto de trabajo decidido en el documento de requerimientos (8.4): el sistema mide
 *  nitidez y luz; la postura y la vestimenta las revisa la coach. La pantalla está armada
 *  alrededor de esa división y no promete detección automática de poses.
 *
 *  Aquí también se captura el **porcentaje de grasa**, que es la entrada que manda toda la
 *  cadena de la calculadora. Sin ese dato no se puede armar el plan del ciclo siguiente.
 */

import { ArrowLeft } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Dialogo } from "@/componentes/Dialogo";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Casilla,
  Chip,
  Entrada,
  Etiqueta,
  Portada,
  Regla,
  Selector,
  Titulo,
} from "@/componentes/primitivas";
import { ErrorApi, api, type FotoApi } from "@/lib/api";
import { usarApiConRespaldo } from "@/lib/usarApi";
import { composicion } from "@/lib/calculadora";
import { alumna, cartera, chequeos } from "@/lib/datos";
import { delta, fecha, num, porcentaje } from "@/lib/formato";
import { ANGULOS, MEDIDAS, type Angulo } from "@/lib/tipos";

export function Validacion() {
  const { alumnaUlid } = useParams();
  const navegar = useNavigate();

  const ficha = cartera.find((a) => a.ulid === alumnaUlid) ?? cartera[0]!;
  const actual = chequeos.at(-1)!;

  const [comparaCon, setComparaCon] = useState(chequeos.length - 2);
  const [angulo, setAngulo] = useState<Angulo>("frontal");
  const [grasa, setGrasa] = useState(String(num((actual.porcentajeGrasa ?? 0.27) * 100)));
  const [revisado, setRevisado] = useState({ postura: false, vestimenta: false, entorno: false });
  const [accion, setAccion] = useState<"validar" | "rechazar" | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);

  // Se piden por su propia ruta a propósito: es lo que deja constancia de que esta coach
  // abrió estas fotos, y cuándo. La obligación es del Anexo Legal §6.
  const { datos: fotos, sinServidor: sinFotos } = usarApiConRespaldo<FotoApi[]>(
    (senal) => api.coach.fotosDeChequeo(actual.ulid, senal),
    [],
    [actual.ulid],
  );

  const previo = chequeos[comparaCon]!;
  const grasaNum = Number.parseFloat(grasa) / 100;

  const derivados = useMemo(() => {
    if (!grasaNum || grasaNum < 0.03 || grasaNum > 0.7) return null;
    const hoy = composicion(actual.pesoKg, grasaNum, alumna.estaturaCm);
    const antes = composicion(previo.pesoKg, previo.porcentajeGrasa ?? grasaNum, alumna.estaturaCm);
    return {
      hoy,
      dGrasa: delta(hoy.masaGrasaKg, antes.masaGrasaKg, "kg"),
      dMagra: delta(hoy.masaLibreDeGrasaKg, antes.masaLibreDeGrasaKg, "kg"),
    };
  }, [grasaNum, actual.pesoKg, previo]);

  const revisionCompleta = revisado.postura && revisado.vestimenta && revisado.entorno;
  const alertaOutlier = ficha.alerta === "outlier";
  const varianza =
    ficha.pesoKg !== null && ficha.pesoPrevio !== null
      ? (ficha.pesoKg - ficha.pesoPrevio) / ficha.pesoPrevio
      : 0;

  return (
    <div className="flex flex-col gap-10">
      <div className="flex flex-col gap-4">
        <Link to="/coach" className="flex w-fit items-center gap-2 text-menor text-tinta-media hover:text-tinta">
          <ArrowLeft className="size-4" /> Panel
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-3">
            <Etiqueta>Chequeo del {fecha(actual.fecha)}</Etiqueta>
            <Portada>{ficha.nombre}</Portada>
          </div>
          <div className="flex flex-wrap gap-2">
            <Boton tono="peligro" onClick={() => setAccion("rechazar")}>
              Rechazar con causa
            </Boton>
            <Boton disabled={!derivados} onClick={() => setAccion("validar")}>
              Validar
            </Boton>
          </div>
        </div>
      </div>

      {fallo ? (
        <Aviso tono="error" titulo="No se pudo guardar">
          {fallo}
        </Aviso>
      ) : null}

      {alertaOutlier ? (
        <Aviso tono="error" titulo={`Alerta de outlier: ${num(varianza * 100)} % de cambio`}>
          De {num(ficha.pesoPrevio)} kg a {num(ficha.pesoKg)} kg en un ciclo. Para validar tendrás
          que escribir por qué lo consideras real.
        </Aviso>
      ) : null}

      <div className="grid gap-10 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-10">
          {/* ---- Comparativa visual ---- */}
          <section className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <Titulo>Comparativa visual</Titulo>
              <Apoyo>Encuadre sin rostro. Cada apertura queda en la bitácora de accesos.</Apoyo>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Campo id="v-contra" etiqueta="Comparar contra">
                <Selector id="v-contra" value={comparaCon} onChange={(e) => setComparaCon(Number(e.target.value))}>
                  {chequeos.slice(0, -1).map((c, i) => (
                    <option key={c.ulid} value={i}>
                      #{c.numero} · {fecha(c.fecha)}
                    </option>
                  ))}
                </Selector>
              </Campo>
              <Campo id="v-angulo" etiqueta="Ángulo">
                <Selector id="v-angulo" value={angulo} onChange={(e) => setAngulo(e.target.value as Angulo)}>
                  {ANGULOS.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.rotulo}
                    </option>
                  ))}
                </Selector>
              </Campo>
            </div>

            {!sinFotos && fotos.some((f) => f.diasParaPurga !== null && f.diasParaPurga <= 15) ? (
              <Aviso tono="atencion" titulo="Estas fotos se purgan pronto">
                La retención es de 4 meses. A la alumna ya se le avisó con enlace de descarga.
              </Aviso>
            ) : null}

            <div className="grid grid-cols-2 gap-3">
              {[
                { c: previo, rotulo: "Anterior" },
                { c: actual, rotulo: "Este chequeo" },
              ].map(({ c, rotulo }) => (
                <figure key={rotulo} className="overflow-hidden rounded-marco border border-linea">
                  <div className="grid aspect-3/4 place-items-center bg-fondo-sutil text-micro text-tinta-suave">
                    {angulo} · {fecha(c.fecha, { day: "numeric", month: "short" })}
                  </div>
                  <figcaption className="flex items-center justify-between gap-2 border-t border-linea px-3 py-2 text-micro font-medium">
                    <span>{rotulo}</span>
                    <span className="cifra text-tinta-media">{num(c.pesoKg)} kg</span>
                  </figcaption>
                </figure>
              ))}
            </div>
          </section>

          <Regla />

          {/* ---- Números ---- */}
          <section className="flex flex-col gap-4">
            <Titulo>Medidas y peso</Titulo>
            <ul className="flex flex-col divide-y divide-linea border-y border-linea">
              <li className="flex items-baseline justify-between gap-3 py-3">
                <span className="text-menor font-semibold">Peso</span>
                <span className="flex items-baseline gap-4">
                  <span className="cifra text-menor text-tinta-suave">{num(previo.pesoKg)}</span>
                  <span className="cifra font-semibold">{num(actual.pesoKg)} kg</span>
                  <span className="cifra w-16 text-right text-menor text-tinta-media">
                    {delta(actual.pesoKg, previo.pesoKg, "kg")?.texto}
                  </span>
                </span>
              </li>
              {MEDIDAS.map((m) => (
                <li key={m.tipo} className="flex items-baseline justify-between gap-3 py-3">
                  <span className="text-menor">{m.rotulo}</span>
                  <span className="flex items-baseline gap-4">
                    <span className="cifra text-menor text-tinta-suave">{num(previo.medidas[m.tipo])}</span>
                    <span className="cifra font-semibold">{num(actual.medidas[m.tipo])} cm</span>
                    <span className="cifra w-16 text-right text-menor text-tinta-media">
                      {delta(actual.medidas[m.tipo], previo.medidas[m.tipo], "cm")?.texto}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </div>

        {/* ---- Columna derecha ---- */}
        <aside className="flex flex-col gap-8">
          {/* Sin este dato no se puede calcular el plan del ciclo siguiente. */}
          <section className="filete flex flex-col gap-4">
            <div className="flex items-center justify-between gap-3">
              <Etiqueta>Estimación de grasa</Etiqueta>
              <Chip tono="espera">Obligatorio</Chip>
            </div>

            <Campo
              id="v-grasa"
              etiqueta="% de grasa corporal"
              sufijo="%"
              ayuda={`Mes pasado: ${previo.porcentajeGrasa ? porcentaje(previo.porcentajeGrasa) : "—"}`}
              {...(grasa && !derivados ? { error: "Entre 3 % y 70 %." } : {})}
            >
              <Entrada
                id="v-grasa"
                type="number"
                step="0.1"
                min={3}
                max={70}
                value={grasa}
                onChange={(e) => setGrasa(e.target.value)}
                className="rounded-r-none"
              />
            </Campo>

            {derivados ? (
              <>
                <dl className="flex flex-col gap-2 text-menor">
                  {[
                    ["Masa grasa", `${num(derivados.hoy.masaGrasaKg)} kg`, derivados.dGrasa?.texto],
                    ["Masa magra", `${num(derivados.hoy.masaLibreDeGrasaKg)} kg`, derivados.dMagra?.texto],
                    ["IMC", `${num(derivados.hoy.imc)} · ${derivados.hoy.clasificacionImc}`, null],
                  ].map(([rotulo, valor, cambio]) => (
                    <div key={rotulo} className="flex items-baseline justify-between gap-3">
                      <dt className="text-tinta-suave">{rotulo}</dt>
                      <dd className="flex items-baseline gap-2">
                        <span className="cifra font-semibold">{valor}</span>
                        {cambio ? <span className="cifra text-micro text-tinta-media">{cambio}</span> : null}
                      </dd>
                    </div>
                  ))}
                </dl>

                {derivados.dMagra && derivados.dMagra.valor < -1 ? (
                  <Aviso tono="error" titulo="Perdió más de 1 kg de masa magra">
                    Con este déficit no debería. Revisa proteína y adherencia antes de bajar más
                    las calorías.
                  </Aviso>
                ) : null}
              </>
            ) : null}

            <Apoyo>
              Sin este dato el constructor no puede calcular calorías ni macros del ciclo siguiente.
            </Apoyo>
          </section>

          {/* ---- Lo automático ---- */}
          <section className="flex flex-col gap-3">
            <Etiqueta>Revisión automática</Etiqueta>
            <dl className="flex flex-col gap-2 text-menor">
              {[
                [
                  "Nitidez",
                  fotos.length
                    ? fotos.every((f) => f.estadoAuto !== "rechazada")
                      ? "Dentro de umbral"
                      : "Bajo umbral"
                    : "Sin datos",
                ],
                ["Ángulos", `${fotos.filter((f) => f.disponible).length} de 3`],
                ["Medidas", "8 de 8"],
                ["Mismo día", "Sí"],
              ].map(([k, v]) => (
                <div key={k} className="flex items-baseline justify-between gap-3">
                  <dt className="text-tinta-suave">{k}</dt>
                  <dd className="font-medium">{v}</dd>
                </div>
              ))}
            </dl>
          </section>

          {/* ---- Lo que revisa la coach ---- */}
          <section className="flex flex-col gap-3">
            <Etiqueta>Lo que revisas tú</Etiqueta>
            <Apoyo>El sistema no juzga postura ni vestimenta. Eso lo ves tú.</Apoyo>
            <div className="flex flex-col gap-2">
              <Casilla
                id="r-postura"
                titulo="Postura"
                checked={revisado.postura}
                onChange={(e) => setRevisado((r) => ({ ...r, postura: e.target.checked }))}
              >
                Brazos relajados, abdomen neutro, sin poses
              </Casilla>
              <Casilla
                id="r-vestimenta"
                titulo="Vestimenta"
                checked={revisado.vestimenta}
                onChange={(e) => setRevisado((r) => ({ ...r, vestimenta: e.target.checked }))}
              >
                Short y top de color liso, según protocolo
              </Casilla>
              <Casilla
                id="r-entorno"
                titulo="Entorno"
                checked={revisado.entorno}
                onChange={(e) => setRevisado((r) => ({ ...r, entorno: e.target.checked }))}
              >
                Mismo lugar y misma luz que el chequeo anterior
              </Casilla>
            </div>
          </section>

          <section className="flex flex-col gap-2">
            <Etiqueta>Nota de la alumna</Etiqueta>
            <Apoyo>Dormí mal la última semana por trabajo. Entrené los 4 días igual.</Apoyo>
          </section>
        </aside>
      </div>

      <DialogoAccion
        accion={accion}
        nombre={ficha.nombre}
        conOutlier={alertaOutlier}
        revisionCompleta={revisionCompleta}
        onCerrar={() => setAccion(null)}
        onListo={async (feedback, justificacion, motivo) => {
          setFallo(null);
          try {
            // El porcentaje de grasa se guarda antes de validar: sin él, el servidor
            // rechaza la validación porque el plan del ciclo siguiente no se podría calcular.
            if (accion === "validar") {
              await api.coach.estimarGrasa(actual.ulid, grasaNum);
              await api.coach.validarChequeo(actual.ulid, feedback, justificacion || undefined);
            } else {
              await api.coach.rechazarChequeo(actual.ulid, motivo);
            }
            setAccion(null);
            navegar("/coach");
          } catch (causa) {
            setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo guardar.");
          }
        }}
      />
    </div>
  );
}

function DialogoAccion({
  accion,
  nombre,
  conOutlier,
  revisionCompleta,
  onCerrar,
  onListo,
}: {
  accion: "validar" | "rechazar" | null;
  nombre: string;
  conOutlier: boolean;
  revisionCompleta: boolean;
  onCerrar: () => void;
  onListo: (feedback: string, justificacion: string, motivo: string) => void | Promise<void>;
}) {
  const [feedback, setFeedback] = useState("");
  const [justificacion, setJustificacion] = useState("");
  const [motivo, setMotivo] = useState("");

  if (accion === null) return null;

  const validando = accion === "validar";
  const faltaJustificacion = validando && conOutlier && !justificacion.trim();
  const bloqueado = validando ? faltaJustificacion : !motivo.trim();

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={validando ? "Validar chequeo" : "Rechazar con causa"}
      titulo={nombre}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton
            tono={validando ? "solido" : "peligro"}
            medida="chica"
            disabled={bloqueado}
            onClick={() => void onListo(feedback, justificacion, motivo)}
          >
            {validando ? "Validar y enviar feedback" : "Rechazar y avisar"}
          </Boton>
        </>
      }
    >
      {validando ? (
        <>
          {!revisionCompleta ? (
            <Aviso tono="atencion" titulo="No marcaste toda la revisión manual">
              Postura, vestimenta y entorno son lo que el sistema no puede juzgar. Puedes validar
              igual, pero conviene revisarlas.
            </Aviso>
          ) : null}

          {conOutlier ? (
            <>
              <Aviso tono="error" titulo="Sobrescribes una alerta de outlier">
                La justificación es obligatoria y queda en el expediente.
              </Aviso>
              <Campo id="v-justif" etiqueta="Justificación técnica">
                <textarea
                  id="v-justif"
                  rows={3}
                  value={justificacion}
                  onChange={(e) => setJustificacion(e.target.value)}
                  className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
                  placeholder="Por qué consideras que el cambio es real"
                />
              </Campo>
            </>
          ) : null}

          <Campo
            id="v-feedback"
            etiqueta="Feedback para la alumna"
            ayuda="Es lo primero que va a leer. Concreto y sin juicio."
          >
            <textarea
              id="v-feedback"
              rows={4}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
              placeholder="Qué ves, qué cambia y por qué"
            />
          </Campo>
        </>
      ) : (
        <>
          <Apoyo>
            Regresa a borrador para que vuelva a capturar. El motivo es obligatorio y ella lo ve
            tal cual: escríbelo como se lo dirías de frente.
          </Apoyo>
          <Campo id="r-detalle" etiqueta="Qué debe corregir">
            <textarea
              id="r-detalle"
              rows={4}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
              placeholder="En la foto de perfil metiste el abdomen. Repítela relajada."
            />
          </Campo>
        </>
      )}
    </Dialogo>
  );
}
