/** Las coaches de la plataforma: alta, plan, límite, estado y suscripción.
 *
 *  Cuántas alumnas, no quiénes. La restricción se impone en `app/datos/repos/plataforma.py`,
 *  no aquí.
 */

import { AlertTriangle, Plus } from "lucide-react";
import { useState } from "react";

import { Dialogo } from "@/componentes/Dialogo";
import { CargandoPantalla } from "@/componentes/Estado";
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
import { useIdioma } from "@/lib/idioma";
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
  const { t } = useIdioma();

  const [dandoDeAlta, setDandoDeAlta] = useState(false);
  const [editando, setEditando] = useState<FilaDeCoachApi | null>(null);
  const [cobrando, setCobrando] = useState<FilaDeCoachApi | null>(null);

  if (cargando) return <CargandoPantalla que={t("las coaches")} filas={5} />;
  if (error) {
    return (
      <Aviso tono="error" titulo={t("No se pudo cargar el panel")}>
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
            {filas.length} {filas.length === 1 ? t("coach") : t("coaches")} ·{" "}
            {filas.reduce((s, f) => s + f.alumnasActivas, 0)} {t("alumnas activas")}
          </Etiqueta>
          <Portada>{t("Coaches")}</Portada>
        </div>
        <Boton onClick={() => setDandoDeAlta(true)}>
          <Plus className="size-4" /> {t("Dar de alta")}
        </Boton>
      </header>

      {filas.length === 0 ? (
        <Vacio>{t("Todavía no hay ninguna coach dada de alta.")}</Vacio>
      ) : (
        <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
          {filas.map((f) => {
            const cerca = f.alumnasActivas >= f.limiteAlumnas * 0.9;
            return (
              <li key={f.ulid} className="flex flex-col gap-3 py-4">
                <div className="flex flex-wrap items-baseline gap-3">
                  <h2 className="text-cuerpo font-semibold">{f.marca}</h2>
                  <span className="text-micro text-tinta-suave">
                    {f.nombre} · {f.email}
                  </span>

                  {f.estado !== "activa" ? (
                    <Chip tono="error">{f.estado === "pausa" ? t("En pausa") : t("Baja")}</Chip>
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
                      {t(ROTULO_SUSCRIPCION[f.suscripcion.estado])}
                    </Chip>
                  ) : null}
                  {f.diasInactiva === null || f.diasInactiva >= 30 ? (
                    <Chip tono="espera">
                      {f.diasInactiva === null
                        ? t("Nunca entró")
                        : t("{n} días sin entrar", { n: f.diasInactiva })}
                    </Chip>
                  ) : null}

                  <div className="ml-auto flex gap-1">
                    <Boton tono="discreto" medida="chica" onClick={() => setCobrando(f)}>
                      {t("Cobros")}
                    </Boton>
                    <Boton tono="contorno" medida="chica" onClick={() => setEditando(f)}>
                      {t("Editar")}
                    </Boton>
                  </div>
                </div>

                <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-5">
                  <Cifra
                    rotulo={t("Alumnas")}
                    valor={`${f.alumnasActivas} / ${f.limiteAlumnas}`}
                    alerta={cerca}
                  />
                  <Cifra rotulo={t("Por validar")} valor={String(f.chequeosPorValidar)} />
                  <Cifra rotulo={t("Chequeos del mes")} valor={String(f.chequeosDelMes)} />
                  <Cifra rotulo={t("Fotos")} valor={`${f.fotos} · ${f.mbFotos} MB`} />
                  <Cifra rotulo={t("Plan")} valor={f.plan} />
                </dl>

                {cerca ? (
                  <Aviso tono="atencion">
                    <span className="flex items-center gap-2">
                      <AlertTriangle className="size-3.5 shrink-0" />
                      {t(
                        "Está por llegar a su límite de alumnas. Súbelo antes de que un alta le falle.",
                      )}
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
  const [marca, setMarca] = useState("");
  const [email, setEmail] = useState("");
  const [plan, setPlan] = useState("basico");
  const [limite, setLimite] = useState(50);
  const [precio, setPrecio] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [clave, setClave] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const { t } = useIdioma();

  async function crear() {
    setError(null);
    setEnviando(true);
    try {
      const hecha = await api.plataforma.darDeAltaCoach({
        nombre,
        marca,
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
      setError(causa instanceof ErrorApi ? causa.message : t("No se pudo dar de alta."));
    } finally {
      setEnviando(false);
    }
  }

  if (clave !== null) {
    return (
      <Dialogo
        abierto
        onCambio={(v) => !v && onCreada()}
        etiqueta={t("Coach creada")}
        titulo={nombre}
        pie={
          <Boton medida="chica" onClick={onCreada}>
            {t("Listo")}
          </Boton>
        }
      >
        <Aviso tono="atencion" titulo={t("Apúntala ahora: no se vuelve a mostrar")}>
          <p className="cifra mt-2 text-titulo font-semibold tracking-[0.08em]">{clave}</p>
        </Aviso>
        <Apoyo>
          {t(
            "Es temporal y se le pide cambiarla al entrar. Después de cerrar esto solo queda su hash, así que ni tú ni nadie puede volver a leerla.",
          )}
        </Apoyo>
      </Dialogo>
    );
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={t("Nueva coach")}
      titulo={t("Dar de alta")}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            {t("Cerrar")}
          </Boton>
          <Boton
            medida="chica"
            disabled={enviando || !nombre.trim() || !email.includes("@")}
            onClick={() => void crear()}
          >
            {t("Crear")}
          </Boton>
        </>
      }
    >
      <Campo id="c-nombre" etiqueta={t("Nombre de la persona")}>
        <Entrada id="c-nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} />
      </Campo>
      <Campo
        id="c-marca"
        etiqueta={t("Nombre de la marca")}
        ayuda={t("Lo que ven sus alumnas en la app y en los correos. Vacío = se usa su nombre.")}
      >
        <Entrada
          id="c-marca"
          value={marca}
          onChange={(e) => setMarca(e.target.value)}
          placeholder={nombre || "LeanMuscle"}
        />
      </Campo>
      <Campo
        id="c-email"
        etiqueta={t("Correo")}
        ayuda={t("Es su usuario para entrar. Único en toda la plataforma.")}
      >
        <Entrada id="c-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      </Campo>

      <div className="grid gap-4 sm:grid-cols-3">
        <Campo id="c-plan" etiqueta={t("Plan")}>
          <Selector id="c-plan" value={plan} onChange={(e) => setPlan(e.target.value)}>
            {PLANES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </Selector>
        </Campo>
        <Campo id="c-limite" etiqueta={t("Límite de alumnas")}>
          <Entrada
            id="c-limite"
            type="number"
            min={1}
            value={limite}
            onChange={(e) => setLimite(Number(e.target.value))}
          />
        </Campo>
        <Campo
          id="c-precio"
          etiqueta={t("Precio de su ciclo")}
          ayuda={t("Lo que ella le cobra a sus alumnas.")}
        >
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
        {t(
          "Nace en cortesía: cobrarle desde el primer día a quien todavía no ha subido una sola alumna genera una factura que nadie va a pagar. La suscripción se ajusta después.",
        )}
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
  const [marca, setMarca] = useState(coach.marca);
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
  const { t } = useIdioma();

  async function guardar() {
    setError(null);
    setEnviando(true);
    try {
      await api.plataforma.editarCoach(coach.ulid, {
        nombre,
        marca,
        plan,
        limiteAlumnas: limite,
        estado,
        precioCiclo: precio,
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
      setError(causa instanceof ErrorApi ? causa.message : t("No se pudo guardar."));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={t("Editar")}
      titulo={coach.nombre}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            {t("Cerrar")}
          </Boton>
          <Boton medida="chica" disabled={enviando} onClick={() => void guardar()}>
            {t("Guardar")}
          </Boton>
        </>
      }
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="e-nombre" etiqueta={t("Nombre de la persona")}>
          <Entrada id="e-nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} />
        </Campo>
        <Campo id="e-marca" etiqueta={t("Nombre de la marca")} ayuda={t("Lo que ven sus alumnas.")}>
          <Entrada id="e-marca" value={marca} onChange={(e) => setMarca(e.target.value)} />
        </Campo>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Campo id="e-plan" etiqueta={t("Plan")}>
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
          etiqueta={t("Límite de alumnas")}
          ayuda={t("Tiene {n} activas.", { n: coach.alumnasActivas })}
        >
          <Entrada
            id="e-limite"
            type="number"
            min={1}
            value={limite}
            onChange={(e) => setLimite(Number(e.target.value))}
          />
        </Campo>
        <Campo id="e-precio" etiqueta={t("Precio de su ciclo")}>
          <Entrada
            id="e-precio"
            type="number"
            min={0}
            value={precio}
            onChange={(e) => setPrecio(Number(e.target.value))}
          />
        </Campo>
      </div>

      <Campo id="e-estado" etiqueta={t("Estado de la cuenta")}>
        <Selector id="e-estado" value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="activa">{t("Activa")}</option>
          <option value="pausa">{t("En pausa")}</option>
          <option value="baja">{t("Baja")}</option>
        </Selector>
      </Campo>

      <Aviso tono="info">
        {t("Poner una cuenta en baja")} <strong>{t("no borra nada")}</strong>.{" "}
        {t(
          "Sus alumnas y sus expedientes siguen ahí: eliminar datos personales es otro flujo, con sus propios plazos, y no puede dispararse desde un selector.",
        )}
      </Aviso>

      <Titulo>{t("Suscripción")}</Titulo>

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="s-precio" etiqueta={t("Precio")}>
          <Entrada
            id="s-precio"
            type="number"
            min={0}
            value={subPrecio}
            onChange={(e) => setSubPrecio(Number(e.target.value))}
          />
        </Campo>
        <Campo id="s-periodicidad" etiqueta={t("Periodicidad")}>
          <Selector
            id="s-periodicidad"
            value={periodicidad}
            onChange={(e) => setPeriodicidad(e.target.value as "mensual" | "anual")}
          >
            <option value="mensual">{t("Mensual")}</option>
            <option value="anual">{t("Anual")}</option>
          </Selector>
        </Campo>
        <Campo id="s-estado" etiqueta={t("Estado")}>
          <Selector id="s-estado" value={subEstado} onChange={(e) => setSubEstado(e.target.value)}>
            {Object.entries(ROTULO_SUSCRIPCION).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {t(rotulo)}
              </option>
            ))}
          </Selector>
        </Campo>
        <Campo id="s-vigente" etiqueta={t("Pagado hasta")}>
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
  const { t } = useIdioma();

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
      setError(causa instanceof ErrorApi ? causa.message : t("No se pudo registrar el cobro."));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={t("Cobros")}
      titulo={coach.nombre}
      descripcion={
        coach.suscripcion?.vigenteHasta
          ? t("Pagada hasta el {fecha}", { fecha: fecha(coach.suscripcion.vigenteHasta) })
          : t("Sin periodo pagado registrado")
      }
      pie={
        <Boton tono="contorno" medida="chica" onClick={onCerrar}>
          {t("Cerrar")}
        </Boton>
      }
    >
      <div className="grid gap-4 sm:grid-cols-3">
        <Campo id="k-monto" etiqueta={t("Monto")}>
          <Entrada
            id="k-monto"
            type="number"
            value={monto}
            onChange={(e) => setMonto(Number(e.target.value))}
          />
        </Campo>
        <Campo id="k-fecha" etiqueta={t("Fecha")}>
          <Entrada
            id="k-fecha"
            type="date"
            value={cuando}
            onChange={(e) => setCuando(e.target.value)}
          />
        </Campo>
        <Campo
          id="k-hasta"
          etiqueta={t("Cubre hasta")}
          ayuda={t("Mueve la suscripción a «al corriente».")}
        >
          <Entrada id="k-hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        </Campo>
      </div>

      <div>
        <Boton medida="chica" disabled={enviando || monto === 0} onClick={() => void registrar()}>
          {t("Registrar cobro")}
        </Boton>
      </div>

      <Apoyo>
        {t(
          "Solo se agrega. Para corregir un cobro mal capturado se registra otro en negativo: lo que se cobró es un hecho, y un historial que se puede reescribir no sirve para cuadrar cuentas.",
        )}
      </Apoyo>

      {error ? <Aviso tono="error">{error}</Aviso> : null}

      {carga.datos && carga.datos.length > 0 ? (
        <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
          {carga.datos.map((c) => (
            <li key={c.ulid} className="flex items-baseline justify-between gap-3 py-2">
              <span className="text-menor">{fecha(c.fecha)}</span>
              <span className="flex items-baseline gap-3">
                {c.periodoTermina ? (
                  <span className="text-micro text-tinta-suave">
                    {t("hasta {fecha}", { fecha: fecha(c.periodoTermina) })}
                  </span>
                ) : null}
                <span className="cifra font-semibold">${num(c.monto)}</span>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <Vacio>{t("Todavía no le has registrado ningún cobro.")}</Vacio>
      )}
    </Dialogo>
  );
}
