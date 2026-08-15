/** Lo que la coach escribe para presentarse, y las preguntas que agrega al cuestionario.
 *
 *  El texto y la ficha son suyos por completo: la plataforma no impone ni un rótulo. El
 *  cuestionario sí tiene un núcleo que no se puede quitar —lesiones, condiciones, medicación
 *  y restricciones— porque el constructor los lee al elegir ejercicios y la ley exige
 *  consentimiento expreso para ellos.
 */

import { GripVertical, Plus, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Casilla,
  Chip,
  Entrada,
  Etiqueta,
  Selector,
  Titulo,
  Vacio,
} from "@/componentes/primitivas";
import {
  ErrorApi,
  api,
  urlDeFotoDeCoach,
  type DatoDeFichaApi,
  type PreguntaApi,
  type PresentacionApi,
  type TipoDePregunta,
} from "@/lib/api";
import { marcaCambiada } from "@/lib/marca";
import { usarApi } from "@/lib/usarApi";

const TIPOS: [TipoDePregunta, string][] = [
  ["texto", "Texto corto"],
  ["texto_largo", "Texto largo"],
  ["numero", "Número"],
  ["opcion", "Opción de una lista"],
  ["si_no", "Sí o no"],
];

const NUCLEO = [
  "Lesiones o cirugías",
  "Condiciones médicas",
  "Medicación",
  "Alergias y restricciones",
  "Consentimientos de datos y fotografías",
];

export function Presentacion() {
  const carga = usarApi<PresentacionApi>((s) => api.coach.presentacion(s));

  const [titulo, setTitulo] = useState("");
  const [texto, setTexto] = useState("");
  const [ficha, setFicha] = useState<DatoDeFichaApi[]>([]);
  const [activa, setActiva] = useState(true);
  const [tieneFoto, setTieneFoto] = useState(false);
  const [version, setVersion] = useState(0);
  const [ocupado, setOcupado] = useState(false);
  const [guardado, setGuardado] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);
  const entradaFoto = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!carga.datos) return;
    setTitulo(carga.datos.titulo);
    setTexto(carga.datos.texto);
    setFicha(carga.datos.ficha);
    setActiva(carga.datos.activa);
    setTieneFoto(carga.datos.tieneFoto);
  }, [carga.datos]);

  async function guardar() {
    setFallo(null);
    setOcupado(true);
    try {
      await api.coach.guardarPresentacion({ titulo, texto, ficha, activa });
      setGuardado(true);
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo guardar.");
    } finally {
      setOcupado(false);
    }
  }

  async function subirFoto(archivo: File) {
    setFallo(null);
    setOcupado(true);
    try {
      await api.coach.subirFotoDePresentacion(archivo);
      setTieneFoto(true);
      setVersion((v) => v + 1);
      // El avatar de la barra es esta misma foto: sin avisar, seguiría con las iniciales.
      marcaCambiada();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo subir la foto.");
    } finally {
      setOcupado(false);
      if (entradaFoto.current) entradaFoto.current.value = "";
    }
  }

  return (
    <section className="flex flex-col gap-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <Titulo>Tu presentación</Titulo>
            <Apoyo>
              Es lo primero que ve una alumna nueva, antes del cuestionario. Escríbela como
              se la contarías en persona.
            </Apoyo>
          </div>
          {activa ? <Chip tono="exito">Se muestra</Chip> : <Chip>Apagada</Chip>}
        </div>

        <div className="flex flex-wrap items-center gap-4">
          {tieneFoto ? (
            <img
              src={urlDeFotoDeCoach(version)}
              alt="Tu foto"
              className="size-20 rounded-full border border-linea object-cover"
            />
          ) : (
            <span className="grid size-20 place-items-center rounded-full border border-dashed border-linea text-micro text-tinta-suave">
              Sin foto
            </span>
          )}
          <input
            ref={entradaFoto}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const archivo = e.target.files?.[0];
              if (archivo) void subirFoto(archivo);
            }}
          />
          <Boton
            tono="contorno"
            medida="chica"
            disabled={ocupado}
            onClick={() => entradaFoto.current?.click()}
          >
            {tieneFoto ? "Cambiar foto" : "Subir foto"}
          </Boton>
          <Apoyo>Tu cara, no tu logo. Se recorta al centro en un cuadrado.</Apoyo>
        </div>

        <Campo id="pr-titulo" etiqueta="Encabezado" ayuda="Lo primero que lee.">
          <Entrada
            id="pr-titulo"
            value={titulo}
            onChange={(e) => setTitulo(e.target.value)}
            placeholder="Hola, soy Mariana"
          />
        </Campo>

        <Campo
          id="pr-texto"
          etiqueta="Tu presentación"
          ayuda="Deja una línea en blanco para separar párrafos."
        >
          <textarea
            id="pr-texto"
            rows={8}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Llevo doce años acompañando a mujeres…"
            className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
          />
        </Campo>

        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Etiqueta>Tu ficha</Etiqueta>
            <Boton
              tono="contorno"
              medida="chica"
              disabled={ficha.length >= 8}
              onClick={() => setFicha((v) => [...v, { rotulo: "", valor: "" }])}
            >
              <Plus className="size-3.5" /> Dato
            </Boton>
          </div>
          <Apoyo>Tú nombras los campos: certificaciones, años de experiencia, enfoque…</Apoyo>
          {ficha.length === 0 ? (
            <Vacio>Sin datos todavía.</Vacio>
          ) : (
            <ul className="flex flex-col gap-2">
              {ficha.map((d, i) => (
                <li key={i} className="flex flex-wrap items-center gap-2">
                  <Entrada
                    aria-label="Rótulo"
                    value={d.rotulo}
                    onChange={(e) =>
                      setFicha((v) =>
                        v.map((x, j) => (j === i ? { ...x, rotulo: e.target.value } : x)),
                      )
                    }
                    placeholder="Certificaciones"
                    className="max-w-48"
                  />
                  <Entrada
                    aria-label="Valor"
                    value={d.valor}
                    onChange={(e) =>
                      setFicha((v) =>
                        v.map((x, j) => (j === i ? { ...x, valor: e.target.value } : x)),
                      )
                    }
                    placeholder="ISAK nivel 1, NSCA-CPT"
                    className="min-w-48 flex-1"
                  />
                  <Boton
                    tono="discreto"
                    medida="icono"
                    aria-label="Quitar dato"
                    onClick={() => setFicha((v) => v.filter((_, j) => j !== i))}
                  >
                    <X className="size-4" />
                  </Boton>
                </li>
              ))}
            </ul>
          )}
        </div>

        <Casilla
          id="pr-activa"
          titulo="Mostrarla a las alumnas nuevas"
          checked={activa}
          onChange={(e) => setActiva(e.target.checked)}
        >
          Apagada, tus alumnas nuevas van directo al cuestionario.
        </Casilla>

        <div>
          <Boton disabled={ocupado} onClick={() => void guardar()}>
            Guardar presentación
          </Boton>
          {guardado ? <Apoyo className="mt-2">Presentación actualizada.</Apoyo> : null}
          {fallo ? (
            <Aviso tono="error" className="mt-3">
              {fallo}
            </Aviso>
          ) : null}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------ Cuestionario --- */

export function Preguntas() {
  const carga = usarApi<PreguntaApi[]>((s) => api.coach.preguntas(s));
  const [fallo, setFallo] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const preguntas = carga.datos ?? [];

  async function operar(accion: () => Promise<unknown>) {
    setFallo(null);
    setOcupado(true);
    try {
      await accion();
      carga.recargar();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo guardar.");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-col gap-1">
        <Titulo>Cuestionario inicial</Titulo>
        <Apoyo>Lo contesta cada alumna nueva justo después de leer tu presentación.</Apoyo>
      </div>

      <div className="flex flex-col gap-2 border-l-2 border-l-linea-fuerte pl-4">
        <Etiqueta>Siempre se pregunta</Etiqueta>
        <ul className="flex flex-col gap-1">
          {NUCLEO.map((n) => (
            <li key={n} className="text-menor text-tinta-media">
              {n}
            </li>
          ))}
        </ul>
        <Apoyo>
          No se pueden quitar: tu constructor los usa para avisarte de una lesión al elegir
          ejercicios, y el consentimiento de datos de salud lo exige la ley.
        </Apoyo>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <Etiqueta>Tus preguntas</Etiqueta>
        <Boton
          tono="contorno"
          medida="chica"
          disabled={ocupado}
          onClick={() =>
            void operar(() =>
              api.coach.crearPregunta({
                texto: "Pregunta nueva",
                tipo: "texto",
                opciones: [],
                obligatoria: false,
                orden: 0,
                activa: true,
              }),
            )
          }
        >
          <Plus className="size-3.5" /> Pregunta
        </Boton>
      </div>

      {fallo ? <Aviso tono="error">{fallo}</Aviso> : null}

      {preguntas.length === 0 ? (
        <Vacio>Todavía no agregas ninguna. El núcleo se pregunta de todos modos.</Vacio>
      ) : (
        <ul className="flex flex-col gap-3">
          {preguntas.map((q) => (
            <Fila
              key={q.ulid}
              q={q}
              onGuardar={(cambios) => void operar(() => api.coach.editarPregunta(q.ulid, cambios))}
              onQuitar={() => void operar(() => api.coach.quitarPregunta(q.ulid))}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

function Fila({
  q,
  onGuardar,
  onQuitar,
}: {
  q: PreguntaApi;
  onGuardar: (cambios: {
    texto: string;
    ayuda: string | null;
    tipo: TipoDePregunta;
    opciones: string[];
    obligatoria: boolean;
    orden: number;
    activa: boolean;
  }) => void;
  onQuitar: () => void;
}) {
  const [texto, setTexto] = useState(q.texto);
  const [tipo, setTipo] = useState<TipoDePregunta>(q.tipo);
  const [opciones, setOpciones] = useState(q.opciones.join(", "));
  const [obligatoria, setObligatoria] = useState(q.obligatoria);
  const [orden, setOrden] = useState(q.orden);

  const cambios = {
    texto,
    ayuda: q.ayuda,
    tipo,
    opciones: opciones
      .split(",")
      .map((o) => o.trim())
      .filter(Boolean),
    obligatoria,
    orden,
    activa: q.activa,
  };

  return (
    <li className="flex flex-col gap-3 rounded-marco border border-linea p-4">
      <div className="flex flex-wrap items-end gap-3">
        <GripVertical className="mb-3 size-4 shrink-0 text-tinta-suave" />
        <div className="min-w-64 flex-1">
          <Campo id={`q-${q.ulid}-t`} etiqueta="Pregunta">
            <Entrada
              id={`q-${q.ulid}-t`}
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
            />
          </Campo>
        </div>
        <Campo id={`q-${q.ulid}-tipo`} etiqueta="Tipo">
          <Selector
            id={`q-${q.ulid}-tipo`}
            value={tipo}
            onChange={(e) => setTipo(e.target.value as TipoDePregunta)}
            className="max-w-48"
          >
            {TIPOS.map(([v, r]) => (
              <option key={v} value={v}>
                {r}
              </option>
            ))}
          </Selector>
        </Campo>
        <Campo id={`q-${q.ulid}-orden`} etiqueta="Orden">
          <Entrada
            id={`q-${q.ulid}-orden`}
            type="number"
            min={0}
            value={orden}
            onChange={(e) => setOrden(Number(e.target.value))}
            className="max-w-20"
          />
        </Campo>
      </div>

      {tipo === "opcion" ? (
        <Campo
          id={`q-${q.ulid}-op`}
          etiqueta="Opciones"
          ayuda="Sepáralas con comas."
        >
          <Entrada
            id={`q-${q.ulid}-op`}
            value={opciones}
            onChange={(e) => setOpciones(e.target.value)}
            placeholder="Principiante, Intermedia, Avanzada"
          />
        </Campo>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-menor">
          <input
            type="checkbox"
            checked={obligatoria}
            onChange={(e) => setObligatoria(e.target.checked)}
            className="size-4 accent-[var(--acento-texto)]"
          />
          Obligatoria
        </label>
        {!q.activa ? <Chip>Apagada</Chip> : null}
        <div className="ml-auto flex gap-2">
          <Boton tono="discreto" medida="chica" onClick={onQuitar}>
            Quitar
          </Boton>
          <Boton tono="contorno" medida="chica" onClick={() => onGuardar(cambios)}>
            Guardar
          </Boton>
        </div>
      </div>
    </li>
  );
}
