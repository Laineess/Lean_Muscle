/** Los planes que vende la coach: nombre, costo e intensidad. Cada alumna pertenece a uno
 *  y de ahí sale cuánto se le cobra.
 *
 *  Un plan con alumnas dentro no se borra, se desactiva: con él se iría la explicación de
 *  por qué esas alumnas pagan lo que pagan.
 */

import { Plus } from "lucide-react";
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
  Selector,
  Titulo,
  Vacio,
} from "@/componentes/primitivas";
import { ErrorApi, api, type PlanComercialApi } from "@/lib/api";
import { num } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
import { usarApi } from "@/lib/usarApi";

const INTENSIDADES = [
  ["baja", "Baja"],
  ["media", "Media"],
  ["alta", "Alta"],
] as const;

export function Planes() {
  const { t } = useIdioma();
  const carga = usarApi<PlanComercialApi[]>((senal) => api.coach.planes(senal));
  const [editando, setEditando] = useState<PlanComercialApi | null>(null);
  const [creando, setCreando] = useState(false);

  if (carga.cargando) return <CargandoPantalla que={t("tus planes")} filas={4} />;

  const planes = carga.datos ?? [];

  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <Titulo>{t("Tus planes")}</Titulo>
          <Apoyo>
            {t(
              "Cada alumna pertenece a uno y de ahí sale cuánto se le cobra. Puedes tener los que quieras, con el precio que quieras.",
            )}
          </Apoyo>
        </div>
        <Boton medida="chica" onClick={() => setCreando(true)}>
          <Plus className="size-4" /> {t("Nuevo plan")}
        </Boton>
      </div>

      {carga.error ? <Aviso tono="error">{carga.error.message}</Aviso> : null}

      {planes.length === 0 ? (
        <Vacio>{t("Todavía no tienes planes. Crea el primero para poder dar de alta alumnas.")}</Vacio>
      ) : (
        <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
          {planes.map((p) => (
            <li key={p.ulid} className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3">
              <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="text-menor font-medium">{p.nombre}</span>
                  <Chip>{p.intensidad}</Chip>
                  {!p.activa ? <Chip tono="error">{t("Inactivo")}</Chip> : null}
                </span>
                <span className="text-micro text-tinta-suave">
                  {p.alumnas === 0
                    ? t("sin alumnas")
                    : t(p.alumnas === 1 ? "{n} alumna" : "{n} alumnas", { n: p.alumnas })}{" "}
                  · {t("cada {n} días", { n: p.dias })}
                </span>
              </span>
              <span className="cifra font-semibold">${num(p.precio)}</span>
              <Boton tono="contorno" medida="chica" onClick={() => setEditando(p)}>
                {t("Editar")}
              </Boton>
            </li>
          ))}
        </ul>
      )}

      {creando || editando ? (
        <FormularioDePlan
          plan={editando}
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

function FormularioDePlan({
  plan,
  onCerrar,
  onGuardado,
}: {
  plan: PlanComercialApi | null;
  onCerrar: () => void;
  onGuardado: () => void;
}) {
  const { t } = useIdioma();
  const [nombre, setNombre] = useState(plan?.nombre ?? "");
  const codigo = plan?.codigo ?? "";
  const [precio, setPrecio] = useState(plan?.precio ?? 0);
  const [dias, setDias] = useState(plan?.dias ?? 30);
  const [intensidad, setIntensidad] = useState<PlanComercialApi["intensidad"]>(
    plan?.intensidad ?? "media",
  );
  const [activa, setActiva] = useState(plan?.activa ?? true);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function guardar() {
    setError(null);
    setEnviando(true);
    try {
      const cuerpo = {
        codigo: codigo.trim() || nombre.trim().toUpperCase().replaceAll(" ", "-").slice(0, 30),
        nombre,
        descripcion: plan?.descripcion ?? null,
        precio,
        dias,
        intensidad,
        activa,
      };
      if (plan) await api.coach.editarPlan(plan.ulid, cuerpo);
      else await api.coach.crearPlan(cuerpo);
      onGuardado();
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : t("No se pudo guardar el plan."));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={plan ? t("Editar plan") : t("Nuevo plan")}
      titulo={nombre || t("Sin nombre")}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            {t("Cerrar")}
          </Boton>
          <Boton
            medida="chica"
            disabled={enviando || !nombre.trim() || precio <= 0}
            onClick={() => void guardar()}
          >
            {t("Guardar")}
          </Boton>
        </>
      }
    >
      <Campo id="pl-nombre" etiqueta={t("Nombre del plan")} ayuda={t("Es lo que ve la alumna al darse de alta.")}>
        <Entrada
          id="pl-nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder={t("Pérdida de grasa · 3 días")}
        />
      </Campo>

      <div className="grid gap-4 sm:grid-cols-3">
        <Campo id="pl-precio" etiqueta={t("Costo")} sufijo="MXN">
          <Entrada
            id="pl-precio"
            type="number"
            min={1}
            value={precio}
            onChange={(e) => setPrecio(Number(e.target.value))}
            className="rounded-r-none"
          />
        </Campo>
        <Campo id="pl-intensidad" etiqueta={t("Intensidad")}>
          <Selector
            id="pl-intensidad"
            value={intensidad}
            onChange={(e) => setIntensidad(e.target.value as PlanComercialApi["intensidad"])}
          >
            {INTENSIDADES.map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {t(rotulo)}
              </option>
            ))}
          </Selector>
        </Campo>
        <Campo id="pl-dias" etiqueta={t("Duración")} sufijo={t("días")}>
          <Entrada
            id="pl-dias"
            type="number"
            min={1}
            max={365}
            value={dias}
            onChange={(e) => setDias(Number(e.target.value))}
            className="rounded-r-none"
          />
        </Campo>
      </div>

      {plan ? (
        <>
          <Campo id="pl-activa" etiqueta={t("Estado")}>
            <Selector
              id="pl-activa"
              value={activa ? "si" : "no"}
              onChange={(e) => setActiva(e.target.value === "si")}
            >
              <option value="si">{t("Activo · se puede asignar")}</option>
              <option value="no">{t("Inactivo · no aparece al dar de alta")}</option>
            </Selector>
          </Campo>
          <Apoyo>
            {t(
              "Cambiar el precio no toca lo ya programado: cada cobro guarda su propio monto, así que subirlo afecta a lo que programes desde hoy.",
            )}
          </Apoyo>
        </>
      ) : null}

      {error ? <Aviso tono="error">{error}</Aviso> : null}
    </Dialogo>
  );
}
