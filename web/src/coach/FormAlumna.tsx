/** Alta y edición de una alumna.
 *
 *  El alta no pide datos de salud: capturarlos por ella viciaría el consentimiento, que la
 *  ley exige expreso y personal.
 *
 *  Al dar de alta se muestra la contraseña inicial para que la coach la dicte si el correo
 *  no llega. Solo sirve para entrar una vez.
 */

import { Check, Copy } from "lucide-react";
import { useEffect, useState } from "react";

import { Dialogo } from "@/componentes/Dialogo";
import { CargandoPantalla } from "@/componentes/Estado";
import { Apoyo, Aviso, Boton, Campo, Entrada, Etiqueta, Selector } from "@/componentes/primitivas";
import {
  ErrorApi,
  api,
  type EdicionDeAlumnaApi,
  type FilaCarteraApi,
  type PerfilEditableApi,
  type PlanComercialApi,
} from "@/lib/api";
import { num } from "@/lib/formato";
import { usarApi } from "@/lib/usarApi";

const NIVELES = ["principiante", "intermedio", "avanzado"] as const;

interface Borrador {
  nombre: string;
  correo: string;
  whatsapp: string;
  fechaNacimiento: string;
  estaturaCm: string;
  tarifaUlid: string;
  nivelExperiencia: string;
  ocupacion: string;
  basculaRef: string;
  lugarRef: string;
  horaRef: string;
  equipo: string;
  grasaObjetivo: string;
  estado: string;
}

const VACIO: Borrador = {
  nombre: "",
  correo: "",
  whatsapp: "",
  fechaNacimiento: "",
  estaturaCm: "",
  tarifaUlid: "",
  nivelExperiencia: "principiante",
  ocupacion: "",
  basculaRef: "",
  lugarRef: "",
  horaRef: "07:00",
  equipo: "gimnasio_completo",
  grasaObjetivo: "",
  estado: "activa",
};

/** Lo guardado, en la forma que usa el formulario. */
function desdePerfil(p: PerfilEditableApi): Borrador {
  return {
    nombre: p.nombre,
    correo: p.correo,
    whatsapp: p.whatsapp ?? "",
    fechaNacimiento: p.fechaNacimiento,
    estaturaCm: p.estaturaCm === null ? "" : String(p.estaturaCm),
    tarifaUlid: p.tarifaUlid ?? "",
    nivelExperiencia: p.nivelExperiencia ?? "principiante",
    ocupacion: p.ocupacion ?? "",
    basculaRef: p.basculaRef ?? "",
    lugarRef: p.lugarRef ?? "",
    horaRef: p.horaRef ?? "07:00",
    equipo: p.equipo ?? "gimnasio_completo",
    // Se guarda como fracción y se enseña como porcentaje: nadie escribe «0.22» de grasa.
    grasaObjetivo:
      p.porcentajeGrasaObjetivo === null ? "" : String(Math.round(p.porcentajeGrasaObjetivo * 100)),
    estado: p.estado,
  };
}

export function FormAlumna({
  alumna,
  onCerrar,
  onGuardada,
}: {
  /** Nula = alta. Con valor = edición. */
  alumna: FilaCarteraApi | null;
  onCerrar: () => void;
  onGuardada: () => void;
}) {
  const planes = usarApi<PlanComercialApi[]>((senal) => api.coach.planes(senal)).datos ?? [];
  const editando = alumna !== null;

  const [b, setB] = useState<Borrador>(
    editando ? { ...VACIO, nombre: alumna.nombre, estado: alumna.estado } : VACIO,
  );
  // El PUT escribe todos los campos: guardar a medio cargar borraría lo que falte.
  const [cargando, setCargando] = useState(editando);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [claveEmitida, setClaveEmitida] = useState<{ clave: string; correo: string } | null>(null);
  const [copiada, setCopiada] = useState(false);

  const ulid = alumna?.ulid;
  useEffect(() => {
    if (!ulid) return;
    const control = new AbortController();
    api.coach
      .perfilDeAlumna(ulid, control.signal)
      .then((p) => {
        setB(desdePerfil(p));
        setCargando(false);
      })
      .catch((causa: unknown) => {
        if (control.signal.aborted) return;
        setError(causa instanceof ErrorApi ? causa.message : "No se pudieron cargar sus datos.");
        setCargando(false);
      });
    return () => control.abort();
  }, [ulid]);

  const cambiar = <K extends keyof Borrador>(campo: K, valor: Borrador[K]) =>
    setB((v) => ({ ...v, [campo]: valor }));

  const numero = (v: string) => (v.trim() ? Number(v) : null);
  const texto = (v: string) => (v.trim() ? v.trim() : null);
  /** El porcentaje que teclea la coach, de vuelta a la fracción que guarda la base. */
  const fraccion = (v: string) => (v.trim() ? Number(v) / 100 : null);

  // Las mismas guardas que el servidor, para avisar antes de enviar.
  const problema = !b.nombre.trim()
    ? "Falta el nombre."
    : !editando && !/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(b.correo.trim())
      ? "Ese correo no parece válido."
      : !editando && !b.fechaNacimiento
        ? "Falta la fecha de nacimiento. El servicio es solo para mayores de 18 años."
        : null;

  async function guardar() {
    if (problema) {
      setError(problema);
      return;
    }
    setError(null);
    setEnviando(true);
    try {
      if (editando) {
        const cambios: EdicionDeAlumnaApi = {
          nombre: b.nombre.trim(),
          whatsapp: texto(b.whatsapp),
          estaturaCm: numero(b.estaturaCm),
          tarifaUlid: b.tarifaUlid || null,
          nivelExperiencia: b.nivelExperiencia,
          equipo: texto(b.equipo),
          ocupacion: texto(b.ocupacion),
          basculaRef: texto(b.basculaRef),
          lugarRef: texto(b.lugarRef),
          horaRef: texto(b.horaRef),
          porcentajeGrasaObjetivo: fraccion(b.grasaObjetivo),
          estado: b.estado,
        };
        await api.coach.editarAlumna(alumna.ulid, cambios);
        onGuardada();
        onCerrar();
      } else {
        const alta = await api.coach.darDeAlta({
          nombre: b.nombre.trim(),
          correo: b.correo.trim(),
          whatsapp: texto(b.whatsapp),
          fechaNacimiento: b.fechaNacimiento,
          estaturaCm: numero(b.estaturaCm),
          tarifaUlid: b.tarifaUlid || null,
          nivelExperiencia: b.nivelExperiencia,
        });
        setClaveEmitida({ clave: alta.claveTemporal, correo: alta.correo });
        onGuardada();
      }
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo guardar.");
    } finally {
      setEnviando(false);
    }
  }

  // ---- Pantalla de clave emitida: aparece una sola vez tras el alta ----
  if (claveEmitida) {
    return (
      <Dialogo
        abierto
        onCambio={(v) => !v && onCerrar()}
        etiqueta="Alumna dada de alta"
        titulo={b.nombre}
        pie={
          <Boton medida="chica" onClick={onCerrar}>
            Listo
          </Boton>
        }
      >
        <Apoyo>
          Le mandamos la invitación a <strong>{claveEmitida.correo}</strong> con esta
          contraseña. Es la misma para todas: díctasela sin problema.
        </Apoyo>

        <div className="flex items-center gap-3 rounded-marco border border-linea-fuerte px-4 py-3">
          <span className="cifra flex-1 text-titulo font-semibold tracking-[0.1em]">
            {claveEmitida.clave}
          </span>
          <Boton
            tono="contorno"
            medida="chica"
            onClick={() => {
              void navigator.clipboard?.writeText(claveEmitida.clave);
              setCopiada(true);
            }}
          >
            {copiada ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
            {copiada ? "Copiada" : "Copiar"}
          </Boton>
        </div>

        <Aviso tono="atencion" titulo="Solo le sirve para entrar una vez">
          Al entrar, lo primero que ve es la pantalla para ponerse la suya. Hasta que lo
          haga, el sistema no le abre nada más.
        </Aviso>

        <Apoyo>
          Vence en 24 horas. Al entrar se le pedirá cambiarla, y después completará su
          cuestionario y sus consentimientos ella misma.
        </Apoyo>
      </Dialogo>
    );
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={editando ? "Editar alumna" : "Alta de alumna"}
      titulo={editando ? alumna.nombre : "Nueva alumna"}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton medida="chica" disabled={enviando || cargando} onClick={() => void guardar()}>
            {enviando ? "Guardando…" : editando ? "Guardar" : "Dar de alta"}
          </Boton>
        </>
      }
    >
      {cargando ? (
        <CargandoPantalla que="sus datos" texto={2} filas={3} portada={false} />
      ) : (
        <>
      <Campo id="a-nombre" etiqueta="Nombre completo">
        <Entrada
          id="a-nombre"
          value={b.nombre}
          onChange={(e) => cambiar("nombre", e.target.value)}
          placeholder="Andrea Sáenz"
        />
      </Campo>

      {!editando ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="a-correo" etiqueta="Correo" ayuda="Ahí le llega su invitación.">
            <Entrada
              id="a-correo"
              type="email"
              value={b.correo}
              onChange={(e) => cambiar("correo", e.target.value)}
            />
          </Campo>
          <Campo
            id="a-nac"
            etiqueta="Fecha de nacimiento"
            ayuda="Solo mayores de 18 años."
          >
            <Entrada
              id="a-nac"
              type="date"
              value={b.fechaNacimiento}
              onChange={(e) => cambiar("fechaNacimiento", e.target.value)}
            />
          </Campo>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="a-wa" etiqueta="WhatsApp">
          <Entrada id="a-wa" type="tel" value={b.whatsapp} onChange={(e) => cambiar("whatsapp", e.target.value)} />
        </Campo>
        <Campo id="a-estatura" etiqueta="Estatura" sufijo="cm" ayuda="Se registra una sola vez.">
          <Entrada
            id="a-estatura"
            type="number"
            min={100}
            max={250}
            value={b.estaturaCm}
            onChange={(e) => cambiar("estaturaCm", e.target.value)}
            className="rounded-r-none"
          />
        </Campo>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo
          id="a-plan"
          etiqueta="Plan"
          ayuda="De aquí sale cuánto se le cobra. Los planes se crean en tus ajustes."
        >
          <Selector id="a-plan" value={b.tarifaUlid} onChange={(e) => cambiar("tarifaUlid", e.target.value)}>
            <option value="">Sin plan asignado</option>
            {planes
              .filter((p) => p.activa)
              .map((p) => (
                <option key={p.ulid} value={p.ulid}>
                  {p.nombre} · ${num(p.precio)} · {p.intensidad}
                </option>
              ))}
          </Selector>
        </Campo>
        <Campo id="a-nivel" etiqueta="Nivel de experiencia">
          <Selector
            id="a-nivel"
            value={b.nivelExperiencia}
            onChange={(e) => cambiar("nivelExperiencia", e.target.value)}
          >
            {NIVELES.map((n) => (
              <option key={n} value={n}>
                {n[0]!.toUpperCase() + n.slice(1)}
              </option>
            ))}
          </Selector>
        </Campo>
      </div>

      {editando ? (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Campo id="a-bascula" etiqueta="Báscula">
              <Entrada id="a-bascula" value={b.basculaRef} onChange={(e) => cambiar("basculaRef", e.target.value)} />
            </Campo>
            <Campo id="a-lugar" etiqueta="Lugar de fotos">
              <Entrada id="a-lugar" value={b.lugarRef} onChange={(e) => cambiar("lugarRef", e.target.value)} />
            </Campo>
            <Campo id="a-hora" etiqueta="Hora">
              <Entrada id="a-hora" value={b.horaRef} onChange={(e) => cambiar("horaRef", e.target.value)} />
            </Campo>
          </div>
          <Campo
            id="a-grasa"
            etiqueta="Grasa objetivo"
            sufijo="%"
            ayuda="Con esto la calculadora proyecta cuánto le falta. Solo lo ves tú."
          >
            <Entrada
              id="a-grasa"
              type="number"
              min={3}
              max={60}
              value={b.grasaObjetivo}
              onChange={(e) => cambiar("grasaObjetivo", e.target.value)}
              className="rounded-r-none"
            />
          </Campo>
          <Campo id="a-estado" etiqueta="Estado">
            <Selector id="a-estado" value={b.estado} onChange={(e) => cambiar("estado", e.target.value)}>
              <option value="activa">Activa</option>
              <option value="pausa">En pausa</option>
            </Selector>
          </Campo>
        </>
      ) : (
        <Aviso tono="info" titulo="No captures datos de salud aquí">
          Su historial clínico y sus consentimientos los llena ella al entrar. La ley exige que
          el consentimiento para datos sensibles sea personal, así que capturarlo tú lo
          invalidaría.
        </Aviso>
      )}
        </>
      )}

      {error ? <Aviso tono="error">{error}</Aviso> : null}
    </Dialogo>
  );
}

/** Emisión de clave temporal: la recuperación de acceso del MVP. */
export function FormClaveTemporal({
  alumna,
  onCerrar,
}: {
  alumna: FilaCarteraApi;
  onCerrar: () => void;
}) {
  const [motivo, setMotivo] = useState("");
  const [clave, setClave] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function emitir() {
    setError(null);
    try {
      const r = await api.coach.claveTemporal(alumna.ulid, motivo.trim());
      setClave(r.clave);
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo generar.");
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta="Recuperación de acceso"
      titulo={alumna.nombre}
      pie={
        clave ? (
          <Boton medida="chica" onClick={onCerrar}>
            Listo
          </Boton>
        ) : (
          <>
            <Boton tono="contorno" medida="chica" onClick={onCerrar}>
              Cancelar
            </Boton>
            <Boton medida="chica" disabled={!motivo.trim()} onClick={() => void emitir()}>
              Generar clave
            </Boton>
          </>
        )
      }
    >
      {clave ? (
        <>
          <div className="rounded-marco border border-linea-fuerte px-4 py-3 text-center">
            <span className="cifra text-titulo font-semibold tracking-[0.1em]">{clave}</span>
          </div>
          <Apoyo>Vence en 24 horas. Al entrar se le pedirá cambiarla.</Apoyo>
        </>
      ) : (
        <>
          <Apoyo>
            En esta versión no hay recuperación automática por correo. Verifica que es ella
            antes de generar la clave.
          </Apoyo>

          <Campo
            id="ct-motivo"
            etiqueta="¿Cómo verificaste su identidad?"
            ayuda="Queda registrado. Sin esto, entregar una clave por WhatsApp es indistinguible de dársela a quien se hizo pasar por ella."
          >
            <Entrada
              id="ct-motivo"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Videollamada · audio de WhatsApp · la conozco en persona"
            />
          </Campo>

          <Etiqueta>Se le enviará también por correo</Etiqueta>
        </>
      )}

      {error ? <Aviso tono="error">{error}</Aviso> : null}
    </Dialogo>
  );
}
