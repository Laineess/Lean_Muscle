/** Lista de precios de lo que la coach cobra aparte del plan.
 *
 *  Los planes viven en su propio bloque porque son una suscripción: tienen duración y una
 *  alumna pertenece a uno. Esto es lo contrario —una consulta suelta, material, una
 *  inscripción— y por eso está aparte en lugar de ser un plan con campos vacíos.
 *
 *  El precio se **copia** al cobro al programarlo. Subirlo aquí no reescribe lo que ya se
 *  pactó con nadie, que es justo lo que se quiere.
 */

import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { Dialogo } from "@/componentes/Dialogo";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Chip,
  Entrada,
  Etiqueta,
  Selector,
  Titulo,
  Vacio,
} from "@/componentes/primitivas";
import { ErrorApi, api, type MotivoDeCobro, type ServicioApi } from "@/lib/api";
import { num } from "@/lib/formato";
import { usarApi } from "@/lib/usarApi";

/** Los mismos motivos del calendario de cobros: lo que se elige aquí es lo que aparece
 *  ahí cuando programa uno. `mensualidad` no está: eso es un plan. */
const MOTIVOS: [MotivoDeCobro, string][] = [
  ["cita", "Consulta"],
  ["inscripcion", "Inscripción"],
  ["material", "Material"],
  ["otro", "Otro concepto"],
];

const ROTULO = Object.fromEntries(MOTIVOS) as Record<MotivoDeCobro, string>;

const VACIO = { nombre: "", descripcion: "", motivo: "cita" as MotivoDeCobro, precio: 0 };

export function Servicios() {
  const carga = usarApi<ServicioApi[]>((s) => api.coach.servicios(s));
  const [editando, setEditando] = useState<ServicioApi | null>(null);
  const [creando, setCreando] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);

  const servicios = carga.datos ?? [];

  async function borrar(ulid: string) {
    setFallo(null);
    try {
      await api.coach.borrarServicio(ulid);
      carga.recargar();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo borrar.");
    }
  }

  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <Titulo>Tus precios</Titulo>
          <Apoyo>
            Consultas, inscripciones y todo lo que cobras suelto. Al programar un cobro los
            eliges de aquí en vez de teclear el importe.
          </Apoyo>
        </div>
        <Boton tono="contorno" medida="chica" onClick={() => setCreando(true)}>
          <Plus className="size-3.5" /> Precio
        </Boton>
      </div>

      {fallo ? <Aviso tono="error">{fallo}</Aviso> : null}

      {carga.cargando ? null : servicios.length === 0 ? (
        <Vacio>
          Todavía no tienes precios sueltos. Agrega el de una consulta y aparecerá al
          programar cobros.
        </Vacio>
      ) : (
        <ul className="flex flex-col divide-y divide-linea border-y border-linea">
          {servicios.map((x) => (
            <li key={x.ulid} className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3">
              <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="text-menor font-medium">{x.nombre}</span>
                  <Chip>{ROTULO[x.motivo] ?? x.motivo}</Chip>
                  {!x.activo ? <Chip tono="espera">Apagado</Chip> : null}
                </span>
                {x.descripcion ? (
                  <span className="text-micro text-tinta-suave">{x.descripcion}</span>
                ) : null}
              </span>
              <span className="cifra font-semibold">${num(x.precio)}</span>
              <Boton tono="contorno" medida="chica" onClick={() => setEditando(x)}>
                Editar
              </Boton>
              <Boton
                tono="discreto"
                medida="icono"
                aria-label={`Borrar ${x.nombre}`}
                onClick={() => void borrar(x.ulid)}
              >
                <Trash2 className="size-3.5" />
              </Boton>
            </li>
          ))}
        </ul>
      )}

      {creando || editando ? (
        <Formulario
          servicio={editando}
          onCerrar={() => {
            setCreando(false);
            setEditando(null);
          }}
          onGuardado={() => {
            setCreando(false);
            setEditando(null);
            carga.recargar();
          }}
        />
      ) : null}
    </section>
  );
}

function Formulario({
  servicio,
  onCerrar,
  onGuardado,
}: {
  servicio: ServicioApi | null;
  onCerrar: () => void;
  onGuardado: () => void;
}) {
  const [borrador, setBorrador] = useState(
    servicio
      ? {
          nombre: servicio.nombre,
          descripcion: servicio.descripcion ?? "",
          motivo: servicio.motivo,
          precio: servicio.precio,
        }
      : VACIO,
  );
  const [activo, setActivo] = useState(servicio?.activo ?? true);
  const [ocupado, setOcupado] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);

  const problema = !borrador.nombre.trim()
    ? "Ponle nombre: es lo que la alumna ve en su cobro."
    : borrador.precio <= 0
      ? "El precio tiene que ser mayor que cero."
      : null;

  async function guardar() {
    if (problema) {
      setFallo(problema);
      return;
    }
    setFallo(null);
    setOcupado(true);
    try {
      const cuerpo = {
        nombre: borrador.nombre,
        descripcion: borrador.descripcion || null,
        motivo: borrador.motivo,
        precio: borrador.precio,
        activo,
      };
      if (servicio) await api.coach.editarServicio(servicio.ulid, cuerpo);
      else await api.coach.crearServicio(cuerpo);
      onGuardado();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo guardar.");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={servicio ? "Editar precio" : "Precio nuevo"}
      titulo={servicio?.nombre || "Algo que cobras aparte"}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton medida="chica" disabled={ocupado || problema !== null} onClick={() => void guardar()}>
            Guardar
          </Boton>
        </>
      }
    >
      <Campo id="sv-nombre" etiqueta="Nombre">
        <Entrada
          id="sv-nombre"
          value={borrador.nombre}
          onChange={(e) => setBorrador((b) => ({ ...b, nombre: e.target.value }))}
          placeholder="Consulta de seguimiento"
        />
      </Campo>

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="sv-motivo" etiqueta="Se cobra como" ayuda="Decide dónde aparece al programar.">
          <Selector
            id="sv-motivo"
            value={borrador.motivo}
            onChange={(e) =>
              setBorrador((b) => ({ ...b, motivo: e.target.value as MotivoDeCobro }))
            }
          >
            {MOTIVOS.map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </Selector>
        </Campo>
        <Campo id="sv-precio" etiqueta="Precio" sufijo="MXN">
          <Entrada
            id="sv-precio"
            type="number"
            min={1}
            step="1"
            value={borrador.precio}
            onChange={(e) => setBorrador((b) => ({ ...b, precio: Number(e.target.value) }))}
            className="rounded-r-none"
          />
        </Campo>
      </div>

      <Campo id="sv-desc" etiqueta="Descripción (opcional)">
        <Entrada
          id="sv-desc"
          value={borrador.descripcion}
          onChange={(e) => setBorrador((b) => ({ ...b, descripcion: e.target.value }))}
          placeholder="45 minutos por video."
        />
      </Campo>

      <label className="flex items-center gap-2 text-menor">
        <input
          type="checkbox"
          checked={activo}
          onChange={(e) => setActivo(e.target.checked)}
          className="size-4 accent-[var(--acento-texto)]"
        />
        Ofrecerlo al programar cobros
      </label>

      <Etiqueta>
        Cambiar el precio no toca los cobros ya programados: ahí el importe quedó copiado.
      </Etiqueta>

      {fallo ? <Aviso tono="error">{fallo}</Aviso> : null}
    </Dialogo>
  );
}
