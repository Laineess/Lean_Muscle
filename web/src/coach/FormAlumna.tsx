/** Alta y edición de una alumna.
 *
 *  **El alta no pide datos de salud a propósito.** El historial clínico y los consentimientos
 *  los llena la propia alumna al entrar: que la coach los capture por ella viciaría el
 *  consentimiento, que la ley exige expreso y personal para datos sensibles.
 *
 *  Al dar de alta, el servidor devuelve la clave temporal **una sola vez**. Se muestra para
 *  que la coach pueda dictarla si el correo no llega, y se advierte que no se podrá consultar
 *  después: solo se guarda su hash.
 */

import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { Dialogo } from "@/componentes/Dialogo";
import { Apoyo, Aviso, Boton, Campo, Entrada, Etiqueta, Selector } from "@/componentes/primitivas";
import { ErrorApi, api, type EdicionDeAlumnaApi, type FilaCarteraApi } from "@/lib/api";

const OBJETIVOS = [
  ["perdida_grasa", "Perder grasa"],
  ["ganancia_masa", "Ganar masa muscular"],
  ["recomposicion", "Recomposición"],
] as const;

const NIVELES = ["principiante", "intermedio", "avanzado"] as const;

interface Borrador {
  nombre: string;
  correo: string;
  whatsapp: string;
  fechaNacimiento: string;
  estaturaCm: string;
  objetivo: string;
  nivelExperiencia: string;
  ocupacion: string;
  basculaRef: string;
  lugarRef: string;
  horaRef: string;
  equipo: string;
  estado: string;
}

const VACIO: Borrador = {
  nombre: "",
  correo: "",
  whatsapp: "",
  fechaNacimiento: "",
  estaturaCm: "",
  objetivo: "recomposicion",
  nivelExperiencia: "principiante",
  ocupacion: "",
  basculaRef: "",
  lugarRef: "",
  horaRef: "07:00",
  equipo: "gimnasio_completo",
  estado: "activa",
};

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
  const editando = alumna !== null;

  const [b, setB] = useState<Borrador>(
    editando
      ? { ...VACIO, nombre: alumna.nombre, objetivo: alumna.objetivo ?? "recomposicion", estado: alumna.estado }
      : VACIO,
  );
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [claveEmitida, setClaveEmitida] = useState<{ clave: string; correo: string } | null>(null);
  const [copiada, setCopiada] = useState(false);

  const cambiar = <K extends keyof Borrador>(campo: K, valor: Borrador[K]) =>
    setB((v) => ({ ...v, [campo]: valor }));

  const numero = (v: string) => (v.trim() ? Number(v) : null);
  const texto = (v: string) => (v.trim() ? v.trim() : null);

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
          objetivo: b.objetivo,
          nivelExperiencia: b.nivelExperiencia,
          equipo: texto(b.equipo),
          ocupacion: texto(b.ocupacion),
          basculaRef: texto(b.basculaRef),
          lugarRef: texto(b.lugarRef),
          horaRef: texto(b.horaRef),
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
          objetivo: b.objetivo,
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
          Le mandamos la invitación a <strong>{claveEmitida.correo}</strong> con esta clave
          temporal. Si no le llega, díctasela tú.
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

        <Aviso tono="atencion" titulo="Apúntala ahora">
          No se puede volver a consultar: solo se guarda su hash. Si se pierde, tendrás que
          generar una nueva desde su ficha.
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
          <Boton medida="chica" disabled={enviando} onClick={() => void guardar()}>
            {enviando ? "Guardando…" : editando ? "Guardar" : "Dar de alta"}
          </Boton>
        </>
      }
    >
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
        <Campo id="a-objetivo" etiqueta="Objetivo">
          <Selector id="a-objetivo" value={b.objetivo} onChange={(e) => cambiar("objetivo", e.target.value)}>
            {OBJETIVOS.map(([id, rotulo]) => (
              <option key={id} value={id}>
                {rotulo}
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
          <Campo id="a-estado" etiqueta="Estado">
            <Selector id="a-estado" value={b.estado} onChange={(e) => cambiar("estado", e.target.value)}>
              <option value="activa">Activa</option>
              <option value="pausa">En pausa</option>
              <option value="baja">Dada de baja</option>
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
