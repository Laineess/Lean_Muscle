/** Las coaches de la plataforma: alta, plan, límite, estado y suscripción.
 *
 *  Cuántas alumnas, no quiénes. La restricción se impone en `app/datos/repos/plataforma.py`,
 *  no aquí.
 */

import { AlertTriangle, Plus } from "lucide-react";
import { useState } from "react";

import { Dialogo } from "@/componentes/Dialogo";
import { Cargando } from "@/componentes/Estado";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Chip,
  Entrada,
  Etiqueta,
  Portada,
  Selector,
  Titulo,
  Vacio,
} from "@/componentes/primitivas";
import {
  ErrorApi,
  api,
  type CobroApi,
  type FilaDeCoachApi,
  type SuscripcionApi,
} from "@/lib/api";
import { fecha, num } from "@/lib/formato";
import { usarApi } from "@/lib/usarApi";
import { cn } from "@/lib/utils";

const ROTULO_SUSCRIPCION: Record<SuscripcionApi["estado"], string> = {
  cortesia: "Cortesía",
  al_corriente: "Al corriente",
  por_vencer: "Por vencer",
  vencida: "Vencida",
  cancelada: "Cancelada",
};

const PLANES = ["basico", "profesional", "estudio"];

export function Coaches() {
  const { datos, cargando, error, recargar } = usarApi<FilaDeCoachApi[]>((senal) =>
    api.plataforma.coaches(senal),
  );

  const [dandoDeAlta, setDandoDeAlta] = useState(false);
  const [editando, setEditando] = useState<FilaDeCoachApi | null>(null);
  const [cobrando, setCobrando] = useState<FilaDeCoachApi | null>(null);

  if (cargando) return <Cargando que="las coaches" />;
  if (error) {
    return (
      <Aviso tono="error" titulo="No se pudo cargar el panel">
        {error.message}
      </Aviso>
    );
  }

  const filas = datos ?? [];

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-3">
          <Etiqueta>
            {filas.length} {filas.length === 1 ? "coach" : "coaches"} ·{" "}
            {filas.reduce((s, f) => s + f.alumnasActivas, 0)} alumnas activas
          </Etiqueta>
          <Portada>Coaches</Portada>
        </div>
        <Boton onClick={() => setDandoDeAlta(true)}>
          <Plus className="size-4" /> Dar de alta
        </Boton>
      </header>

      {filas.length === 0 ? (
        <Vacio>Todavía no hay ninguna coach dada de alta.</Vacio>
      ) : (
        <ul className="flex flex-col divide-y divide-linea border-y border-linea">
          {filas.map((f) => {
            const cerca = f.alumnasActivas >= f.limiteAlumnas * 0.9;
            return (
              <li key={f.ulid} className="flex flex-col gap-3 py-4">
                <div className="flex flex-wrap items-baseline gap-3">
                  <h2 className="text-cuerpo font-semibold">{f.nombre}</h2>
                  <span className="text-micro text-tinta-suave">{f.email}</span>

                  {f.estado !== "activa" ? (
                    <Chip tono="error">{f.estado === "pausa" ? "En pausa" : "Baja"}</Chip>
                  ) : null}
                  {f.suscripcion ? (
                    <Chip
                      tono={
                        f.suscripcion.estado === "vencida"
                          ? "error"
                          : f.suscripcion.estado === "al_corriente"
                            ? "exito"
                            : "espera"
                      }
                    >
                      {ROTULO_SUSCRIPCION[f.suscripcion.estado]}
                    </Chip>
                  ) : null}
                  {f.diasInactiva === null || f.diasInactiva >= 30 ? (
                    <Chip tono="espera">
                      {f.diasInactiva === null ? "Nunca entró" : `${f.diasInactiva} días sin entrar`}
                    </Chip>
                  ) : null}

                  <div className="ml-auto flex gap-1">
                    <Boton tono="discreto" medida="chica" onClick={() => setCobrando(f)}>
                      Cobros
                    </Boton>
                    <Boton tono="contorno" medida="chica" onClick={() => setEditando(f)}>
                      Editar
                    </Boton>
                  </div>
                </div>

                <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-5">
                  <Cifra
                    rotulo="Alumnas"
                    valor={`${f.alumnasActivas} / ${f.limiteAlumnas}`}
                    alerta={cerca}
                  />
                  <Cifra rotulo="Por validar" valor={String(f.chequeosPorValidar)} />
                  <Cifra rotulo="Chequeos del mes" valor={String(f.chequeosDelMes)} />
                  <Cifra rotulo="Fotos" valor={`${f.fotos} · ${f.mbFotos} MB`} />
                  <Cifra rotulo="Plan" valor={f.plan} />
                </dl>

                {cerca ? (
                  <Aviso tono="atencion">
                    <span className="flex items-center gap-2">
                      <AlertTriangle className="size-3.5 shrink-0" />
                      Está por llegar a su límite de alumnas. Súbelo antes de que un alta le
                      falle.
                    </span>
                  </Aviso>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}

      {dandoDeAlta ? (
        <FormularioAlta
          onCerrar={() => setDandoDeAlta(false)}
          onCreada={() => {
            setDandoDeAlta(false);
            recargar();
          }}
        />
      ) : null}

      {editando ? (
        <FormularioEdicion
          coach={editando}
          onCerrar={() => setEditando(null)}
          onGuardada={() => {
            setEditando(null);
            recargar();
          }}
        />
      ) : null}

      {cobrando ? (
        <PanelDeCobros
          coach={cobrando}
          onCerrar={() => setCobrando(null)}
          onCambio={recargar}
        />
      ) : null}
    </div>
  );
}

function Cifra({ rotulo, valor, alerta }: { rotulo: string; valor: string; alerta?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-micro tracking-[0.06em] text-tinta-suave uppercase">{rotulo}</dt>
      <dd className={cn("cifra text-menor font-semibold", alerta && "text-peligro")}>{valor}</dd>
    </div>
  );
}

/* ------------------------------------------------------------------ Alta --- */

function FormularioAlta({
  onCerrar,
  onCreada,
}: {
  onCerrar: () => void;
  onCreada: () => void;
}) {
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [plan, setPlan] = useState("basico");
  const [limite, setLimite] = useState(50);
  const [precio, setPrecio] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [clave, setClave] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function crear() {
    setError(null);
    setEnviando(true);
    try {
      const hecha = await api.plataforma.darDeAltaCoach({
        nombre,
        email,
        slug: null,
        plan,
        limiteAlumnas: limite,
        precioCiclo: precio,
        colorAcento: "#c9a227",
        zonaHoraria: "America/Mexico_City",
      });
      setClave(hecha.claveTemporal);
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo dar de alta.");
    } finally {
      setEnviando(false);
    }
  }

  if (clave !== null) {
    return (
      <Dialogo
        abierto
        onCambio={(v) => !v && onCreada()}
        etiqueta="Coach creada"
        titulo={nombre}
        pie={
          <Boton medida="chica" onClick={onCreada}>
            Listo
          </Boton>
        }
      >
        <Aviso tono="atencion" titulo="Apúntala ahora: no se vuelve a mostrar">
          <p className="cifra mt-2 text-titulo font-semibold tracking-[0.08em]">{clave}</p>
        </Aviso>
        <Apoyo>
          Es temporal y se le pide cambiarla al entrar. Después de cerrar esto solo queda su
          hash, así que ni tú ni nadie puede volver a leerla.
        </Apoyo>
      </Dialogo>
    );
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta="Nueva coach"
      titulo="Dar de alta"
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            Cerrar
          </Boton>
          <Boton
            medida="chica"
            disabled={enviando || !nombre.trim() || !email.includes("@")}
            onClick={() => void crear()}
          >
            Crear
          </Boton>
        </>
      }
    >
      <Campo id="c-nombre" etiqueta="Nombre">
        <Entrada id="c-nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} />
      </Campo>
      <Campo id="c-email" etiqueta="Correo" ayuda="Es su usuario para entrar. Único en toda la plataforma.">
        <Entrada id="c-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      </Campo>

      <div className="grid gap-4 sm:grid-cols-3">
        <Campo id="c-plan" etiqueta="Plan">
          <Selector id="c-plan" value={plan} onChange={(e) => setPlan(e.target.value)}>
            {PLANES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </Selector>
        </Campo>
        <Campo id="c-limite" etiqueta="Límite de alumnas">
          <Entrada
            id="c-limite"
            type="number"
            min={1}
            value={limite}
            onChange={(e) => setLimite(Number(e.target.value))}
          />
        </Campo>
        <Campo id="c-precio" etiqueta="Precio de su ciclo" ayuda="Lo que ella le cobra a sus alumnas.">
          <Entrada
            id="c-precio"
            type="number"
            min={0}
            value={precio}
            onChange={(e) => setPrecio(Number(e.target.value))}
          />
        </Campo>
      </div>

      <Apoyo>
        Nace en cortesía: cobrarle desde el primer día a quien todavía no ha subido una sola
        alumna genera una factura que nadie va a pagar. La suscripción se ajusta después.
      </Apoyo>

      {error ? <Aviso tono="error">{error}</Aviso> : null}
    </Dialogo>
  );
}

/* -------------------------------------------------------------- Edición --- */

function FormularioEdicion({
  coach,
  onCerrar,
  onGuardada,
}: {
  coach: FilaDeCoachApi;
  onCerrar: () => void;
  onGuardada: () => void;
}) {
  const [nombre, setNombre] = useState(coach.nombre);
  const [plan, setPlan] = useState(coach.plan);
  const [limite, setLimite] = useState(coach.limiteAlumnas);
  const [estado, setEstado] = useState(coach.estado);
  const [precio, setPrecio] = useState(coach.precioCiclo);

  const s = coach.suscripcion;
  const [subPrecio, setSubPrecio] = useState(s?.precio ?? 0);
  const [periodicidad, setPeriodicidad] = useState(s?.periodicidad ?? "mensual");
  const [subEstado, setSubEstado] = useState<string>(s?.estado ?? "cortesia");
  const [vigente, setVigente] = useState(s?.vigenteHasta ?? "");

  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function guardar() {
    setError(null);
    setEnviando(true);
    try {
      await api.plataforma.editarCoach(coach.ulid, {
        nombre,
        plan,
        limiteAlumnas: limite,
        estado,
        precioCiclo: precio,
        colorAcento: "#c9a227",
      });
      await api.plataforma.editarSuscripcion(coach.ulid, {
        // La suscripción hereda el plan de la cuenta: dos «planes» distintos para la misma
        // coach es una inconsistencia esperando a que alguien la descubra facturando.
        plan,
        precio: subPrecio,
        periodicidad,
        estado: subEstado,
        vigenteHasta: vigente || null,
        nota: s?.nota ?? null,
      });
      onGuardada();
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo guardar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta="Editar"
      titulo={coach.nombre}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            Cerrar
          </Boton>
          <Boton medida="chica" disabled={enviando} onClick={() => void guardar()}>
            Guardar
          </Boton>
        </>
      }
    >
      <Campo id="e-nombre" etiqueta="Nombre">
        <Entrada id="e-nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} />
      </Campo>

      <div className="grid gap-4 sm:grid-cols-3">
        <Campo id="e-plan" etiqueta="Plan">
          <Selector id="e-plan" value={plan} onChange={(e) => setPlan(e.target.value)}>
            {PLANES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </Selector>
        </Campo>
        <Campo
          id="e-limite"
          etiqueta="Límite de alumnas"
          ayuda={`Tiene ${coach.alumnasActivas} activas.`}
        >
          <Entrada
            id="e-limite"
            type="number"
            min={1}
            value={limite}
            onChange={(e) => setLimite(Number(e.target.value))}
          />
        </Campo>
        <Campo id="e-precio" etiqueta="Precio de su ciclo">
          <Entrada
            id="e-precio"
            type="number"
            min={0}
            value={precio}
            onChange={(e) => setPrecio(Number(e.target.value))}
          />
        </Campo>
      </div>

      <Campo id="e-estado" etiqueta="Estado de la cuenta">
        <Selector id="e-estado" value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="activa">Activa</option>
          <option value="pausa">En pausa</option>
          <option value="baja">Baja</option>
        </Selector>
      </Campo>

      <Aviso tono="info">
        Poner una cuenta en baja <strong>no borra nada</strong>. Sus alumnas y sus expedientes
        siguen ahí: eliminar datos personales es otro flujo, con sus propios plazos, y no puede
        dispararse desde un selector.
      </Aviso>

      <Titulo>Suscripción</Titulo>

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="s-precio" etiqueta="Precio">
          <Entrada
            id="s-precio"
            type="number"
            min={0}
            value={subPrecio}
            onChange={(e) => setSubPrecio(Number(e.target.value))}
          />
        </Campo>
        <Campo id="s-periodicidad" etiqueta="Periodicidad">
          <Selector
            id="s-periodicidad"
            value={periodicidad}
            onChange={(e) => setPeriodicidad(e.target.value as "mensual" | "anual")}
          >
            <option value="mensual">Mensual</option>
            <option value="anual">Anual</option>
          </Selector>
        </Campo>
        <Campo id="s-estado" etiqueta="Estado">
          <Selector id="s-estado" value={subEstado} onChange={(e) => setSubEstado(e.target.value)}>
            {Object.entries(ROTULO_SUSCRIPCION).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </Selector>
        </Campo>
        <Campo id="s-vigente" etiqueta="Pagado hasta">
          <Entrada
            id="s-vigente"
            type="date"
            value={vigente}
            onChange={(e) => setVigente(e.target.value)}
          />
        </Campo>
      </div>

      {error ? <Aviso tono="error">{error}</Aviso> : null}
    </Dialogo>
  );
}

/* --------------------------------------------------------------- Cobros --- */

function PanelDeCobros({
  coach,
  onCerrar,
  onCambio,
}: {
  coach: FilaDeCoachApi;
  onCerrar: () => void;
  onCambio: () => void;
}) {
  const carga = usarApi<CobroApi[]>((senal) => api.plataforma.cobros(coach.ulid, senal), [
    coach.ulid,
  ]);

  const hoy = new Date().toISOString().slice(0, 10);
  const [monto, setMonto] = useState(coach.suscripcion?.precio ?? 0);
  const [cuando, setCuando] = useState(hoy);
  const [hasta, setHasta] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function registrar() {
    setError(null);
    setEnviando(true);
    try {
      await api.plataforma.registrarCobro(coach.ulid, {
        monto,
        fecha: cuando,
        metodo: "transferencia",
        periodoInicia: cuando,
        periodoTermina: hasta || null,
        nota: null,
      });
      carga.recargar();
      onCambio();
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo registrar el cobro.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta="Cobros"
      titulo={coach.nombre}
      descripcion={
        coach.suscripcion?.vigenteHasta
          ? `Pagada hasta el ${fecha(coach.suscripcion.vigenteHasta)}`
          : "Sin periodo pagado registrado"
      }
      pie={
        <Boton tono="contorno" medida="chica" onClick={onCerrar}>
          Cerrar
        </Boton>
      }
    >
      <div className="grid gap-4 sm:grid-cols-3">
        <Campo id="k-monto" etiqueta="Monto">
          <Entrada
            id="k-monto"
            type="number"
            value={monto}
            onChange={(e) => setMonto(Number(e.target.value))}
          />
        </Campo>
        <Campo id="k-fecha" etiqueta="Fecha">
          <Entrada
            id="k-fecha"
            type="date"
            value={cuando}
            onChange={(e) => setCuando(e.target.value)}
          />
        </Campo>
        <Campo id="k-hasta" etiqueta="Cubre hasta" ayuda="Mueve la suscripción a «al corriente».">
          <Entrada id="k-hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        </Campo>
      </div>

      <div>
        <Boton medida="chica" disabled={enviando || monto === 0} onClick={() => void registrar()}>
          Registrar cobro
        </Boton>
      </div>

      <Apoyo>
        Solo se agrega. Para corregir un cobro mal capturado se registra otro en negativo: lo
        que se cobró es un hecho, y un historial que se puede reescribir no sirve para cuadrar
        cuentas.
      </Apoyo>

      {error ? <Aviso tono="error">{error}</Aviso> : null}

      {carga.datos && carga.datos.length > 0 ? (
        <ul className="flex flex-col divide-y divide-linea border-y border-linea">
          {carga.datos.map((c) => (
            <li key={c.ulid} className="flex items-baseline justify-between gap-3 py-2">
              <span className="text-menor">{fecha(c.fecha)}</span>
              <span className="flex items-baseline gap-3">
                {c.periodoTermina ? (
                  <span className="text-micro text-tinta-suave">
                    hasta {fecha(c.periodoTermina)}
                  </span>
                ) : null}
                <span className="cifra font-semibold">${num(c.monto)}</span>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <Vacio>Todavía no le has registrado ningún cobro.</Vacio>
      )}
    </Dialogo>
  );
}
