/** Constructor de planes con la calculadora metabólica integrada.
 *
 *  Dos guardas que también vive el servidor (`app/dominio/plan.py`): sin chequeo validado no
 *  se publica plan nuevo, y sin calorías ni macros tampoco.
 *
 *  La proyección solo la ve la coach: asume adherencia perfecta, y enseñársela a la alumna
 *  convertiría una estimación en una promesa.
 */

import { ArrowLeft, Dumbbell, UtensilsCrossed } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, KeyboardEvent } from "react";
import { Link, useParams } from "react-router-dom";

import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Chip,
  Entrada,
  Etiqueta,
  Portada,
  Regla,
  Selector,
  Titulo,
  Vacio,
} from "@/componentes/primitivas";
import { normalizarAlimento } from "@/lib/alimentos";
import {
  EditorEntrenamiento,
  EditorNutricion,
  type DiaDeEntrenamiento,
  type TiempoDeComida,
} from "@/coach/EditorPlan";
import { CalendarioDeCobros } from "@/coach/CalendarioDeCobros";
import { Hoja } from "@/coach/Hoja";
import { TablaDatosCliente } from "@/coach/TablaDatosCliente";
import { TablaDistribucionMacros } from "@/coach/TablaDistribucionMacros";
import { TablaProyeccionGanancia } from "@/coach/TablaProyeccionGanancia";
import { TablaProyeccionPerdida } from "@/coach/TablaProyeccionPerdida";
import { TablaRefeeds } from "@/coach/TablaRefeeds";
import {
  ErrorApi,
  api,
  descargarPdf,
  urlDeFotoDeComida,
  type ExpedienteDeConstructorApi,
  type FotoDeComidaApi,
  type FrecuenciaFotos,
  type HistorialApi,
  type PlanApi,
  type RespuestaDeAlumnaApi,
} from "@/lib/api";
import {
  ACTIVIDAD,
  calcular,
  deficitPromedioSemanal,
  ROTULO_MACRO,
  type BaseProteina,
  type IdActividad,
  type Macro,
  type RelacionGanancia,
  type Sexo,
} from "@/lib/calculadora";
import { edadEn, fecha, num } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
import { usarApi } from "@/lib/usarApi";
import { cn } from "@/lib/utils";

const MACROS: Macro[] = ["carbohidrato", "proteina", "grasa"];

/** Cada cuánto se le piden fotos de sus platos. Se guarda con el plan de nutrición. */
const FRECUENCIAS: [FrecuenciaFotos, string][] = [
  ["ninguna", "No pedirle fotos"],
  ["diaria", "Todos los días"],
  ["semanal", "Una vez por semana"],
  ["quincenal", "Cada quince días"],
  ["mensual", "Una vez al mes"],
];

/** Horizonte de la proyección de ganancia, el mismo que trae la hoja en H20. Es una
 *  hipótesis que la coach mueve para ver escenarios, no un dato del plan: no se guarda. */
const SEMANAS_GANANCIA = 20;

type SeccionExpediente = "expediente" | "calculadora" | "programa";

function contenidoDeNutricion(plan: PlanApi | null) {
  const c = plan?.contenido ?? {};
  return {
    notas: c.notas ?? "",
    tiempos: (c.tiempos ?? []).map((t) => ({
      ...t,
      alimentos: t.alimentos.map(normalizarAlimento),
    })),
  };
}

function contenidoDeEntrenamiento(plan: PlanApi | null) {
  const c = plan?.contenido ?? {};
  return {
    notas: c.notas ?? "",
    plantilla: c.plantilla ?? "",
    dias: (c.dias ?? []).map((d) => ({ ...d, ejercicios: [...d.ejercicios] })),
  };
}

/** Campo numérico con texto local: se escribe con libertad, se aplica en vivo (cada tecla recalcula
 *  el resto de la calculadora) y se finaliza al salir o con Enter. El scroll del ratón/trackpad no
 *  mueve el valor.
 *
 *  Mientras el campo tiene el foco no se deja que el valor de la prop lo sobreescriba, para que el
 *  usuario pueda escribir decimales y borrar sin que el texto "salte". */
function usarCampoNumero(real: number, aplicar: (n: number) => void) {
  const [texto, setTexto] = useState(String(real ?? ""));
  const enfocado = useRef(false);
  useEffect(() => {
    if (!enfocado.current) setTexto(String(real ?? ""));
  }, [real]);
  const finalizar = () => {
    enfocado.current = false;
    const n = Number(String(texto).replace(",", "."));
    if (Number.isNaN(n)) {
      setTexto(String(real ?? ""));
    } else {
      aplicar(n);
    }
  };
  const alEnfocar = () => {
    enfocado.current = true;
  };
  const alTeclear = (e: ChangeEvent<HTMLInputElement>) => {
    const s = e.target.value;
    setTexto(s);
    // En vivo: si el texto ya es un número completo, propágalo al momento.
    const n = Number(String(s).replace(",", "."));
    if (String(s).trim() !== "" && !Number.isNaN(n)) aplicar(n);
  };
  const alTocarTecla = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") finalizar();
  };
  const alGirarRueda = (e: { currentTarget: { blur: () => void } }) => {
    // Quita el foco al girar la rueda para que el navegador no suba/baje el número.
    e.currentTarget.blur();
  };
  return {
    value: texto,
    onChange: alTeclear,
    onBlur: finalizar,
    onFocus: alEnfocar,
    onWheel: alGirarRueda,
    onKeyDown: alTocarTecla,
  };
}

/** Campo de porcentaje editable con el patrón de texto local (libre al teclear). */
function CampoPorcentaje({
  id,
  etiqueta,
  minimo,
  maximo,
  valor,
  onAplicar,
  deshabilitado,
}: {
  id: string;
  etiqueta: string;
  minimo?: number;
  maximo?: number;
  valor: number;
  onAplicar: (n: number) => void;
  deshabilitado: boolean;
}) {
  const campo = usarCampoNumero(valor, onAplicar);
  return (
    <Campo id={id} etiqueta={etiqueta} sufijo="%">
      <Entrada
        id={id}
        type="number"
        step={1}
        min={minimo}
        max={maximo}
        disabled={deshabilitado}
        {...campo}
        className="rounded-r-none"
      />
    </Campo>
  );
}

/** Campo numérico editable sin el problema del «0 pegado»: aplica el valor al salir. */
function CampoNumeroEditable({
  id,
  etiqueta,
  ayuda,
  sufijo,
  minimo,
  maximo,
  paso,
  valor,
  onAplicar,
  deshabilitado,
}: {
  id: string;
  etiqueta: string;
  ayuda?: string;
  sufijo: string;
  minimo?: number;
  maximo?: number;
  paso?: number;
  valor: number;
  onAplicar: (n: number) => void;
  deshabilitado: boolean;
}) {
  const campo = usarCampoNumero(valor, onAplicar);
  return (
    <Campo id={id} etiqueta={etiqueta} sufijo={sufijo} ayuda={ayuda}>
      <Entrada
        id={id}
        type="number"
        step={paso}
        min={minimo}
        max={maximo}
        disabled={deshabilitado}
        {...campo}
        className="rounded-r-none"
      />
    </Campo>
  );
}

export function Constructor() {
  const { t } = useIdioma();
  const { alumnaUlid = "" } = useParams();
  const carga = usarApi<ExpedienteDeConstructorApi>(
    (senal) => api.coach.expedienteDePlan(alumnaUlid, senal),
    [alumnaUlid],
  );
  const clinico = usarApi<HistorialApi>(
    (senal) => api.coach.historial(alumnaUlid, senal),
    [alumnaUlid],
  );

  if (carga.cargando) return <Vacio>{t("Abriendo el expediente…")}</Vacio>;
  if (carga.error || !carga.datos) {
    return (
      <Aviso tono="error" titulo={t("No se pudo abrir el plan")}>
        {carga.error?.message ?? t("Vuelve a intentarlo.")}
      </Aviso>
    );
  }
  // La clave fuerza el remonte al cambiar de alumna: el estado de abajo nace de las props.
  return <Editor key={alumnaUlid} exp={carga.datos} clinico={clinico.datos} />;
}

function Editor({ exp, clinico }: { exp: ExpedienteDeConstructorApi; clinico: HistorialApi | null }) {
  const { t } = useIdioma();
  const p = exp.parametros;
  const chequeo = exp.chequeo;
  const nutricion = contenidoDeNutricion(exp.nutricion);
  const entrenamiento = contenidoDeEntrenamiento(exp.entrenamiento);

  // Parámetros del ciclo, heredados del anterior. La coach los ajusta si hace falta.
  const [actividad, setActividad] = useState<IdActividad>(p.actividad as IdActividad);
  const [ajustePct, setAjustePct] = useState(Math.round(p.porcentajeAjuste * 100));
  // Porcentaje del «día bajo» de la tabla de refeeds, independiente del ajuste calórico global:
  // en la hoja son columnas distintas y tocar uno no debe recalcular el déficit del plan.
  const [diaBajoPct, setDiaBajoPct] = useState(Math.abs(Math.round(p.porcentajeAjuste * 100)));
  const [reparto, setReparto] = useState({
    carbohidrato: Math.round(p.reparto.carbohidrato * 100),
    proteina: Math.round(p.reparto.proteina * 100),
    grasa: Math.round(p.reparto.grasa * 100),
  });
  const [baseProteina, setBaseProteina] = useState<BaseProteina>(p.baseProteina as BaseProteina);
  const [diasRefeed, setDiasRefeed] = useState(p.diasRefeed);
  const [refeedPct, setRefeedPct] = useState(Math.round(p.porcentajeDiaRefeed * 100));
  // Sin chequeo validado no hay cuerpo real que calcular: no se siembran valores inventados
  // (65 kg, 26 % grasa, 165 cm…) que la coach pudiera leer como si fueran del alumno. Hasta
  // validar el primer chequeo, peso/estatura/edad quedan vacíos y la calculadora no arroja.
  const chequeoValidado = chequeo?.estado === "validado";
  const [pesoKg, setPesoKg] = useState<number>(chequeoValidado ? (chequeo?.pesoKg ?? 0) : 0);
  const [grasaPct, setGrasaPct] = useState<number>(chequeoValidado ? (chequeo?.porcentajeGrasa ?? 0) : 0);
  const [estaturaCm, setEstaturaCm] = useState<number>(chequeoValidado ? (exp.estaturaCm ?? 0) : 0);
  const [edadAnios, setEdadAnios] = useState<number>(
    chequeoValidado ? (edadEn(exp.fechaNacimiento, new Date().toISOString().slice(0, 10)) || 0) : 0,
  );
  const [sexoCliente, setSexoCliente] = useState<Sexo>(
    exp.sexo === "M" ? "masculino" : "femenino",
  );
  const [semanasGanancia, setSemanasGanancia] = useState(SEMANAS_GANANCIA);
  const [grasaObjetivoPct, setGrasaObjetivoPct] = useState<number>(
    exp.porcentajeGrasaObjetivo ??
      (chequeoValidado && chequeo?.porcentajeGrasa
        ? Math.round(chequeo.porcentajeGrasa * 0.75 * 100) / 100
        : 0),
  );
  const [seccion, setSeccion] = useState<SeccionExpediente>("expediente");

  // Contenido editable del plan. Arranca de lo que ya tenía el ciclo anterior.
  const [pestana, setPestana] = useState<"nutricion" | "entrenamiento">("nutricion");
  const [tiempos, setTiempos] = useState<TiempoDeComida[]>(nutricion.tiempos);
  const [dias, setDias] = useState<DiaDeEntrenamiento[]>(entrenamiento.dias);
  const [plantilla, setPlantilla] = useState(entrenamiento.plantilla);
  const [notasNutricion, setNotasNutricion] = useState(nutricion.notas);
  const [frecuenciaFotos, setFrecuenciaFotos] = useState<FrecuenciaFotos>(
    exp.nutricion?.frecuenciaFotos ?? "ninguna",
  );
  const [notasEntrenamiento, setNotasEntrenamiento] = useState(entrenamiento.notas);
  const [guardando, setGuardando] = useState<"borrador" | "publicar" | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [hecho, setHecho] = useState<string | null>(null);

  const sumaReparto = reparto.carbohidrato + reparto.proteina + reparto.grasa;
  const repartoCuadra = sumaReparto === 100;
  // Sin chequeo validado no hay peso/estatura reales: se cuelga el cálculo (guardaría un
  // plan basado en un cuerpo inventado) y se enseña a validar primero.
  const sinReferenciaReal = !chequeoValidado || pesoKg <= 0 || estaturaCm <= 0;

  // Sin chequeo validado se muestran en 0, no los parámetros heredados del ciclo anterior:
  // leerlos como del alumno sería lo mismo que presentar cifras inventadas.
  const mActividad = sinReferenciaReal ? "" : actividad;
  const mBase = sinReferenciaReal ? "peso_total" : baseProteina;
  const mDiasRefeed = sinReferenciaReal ? 0 : diasRefeed;

  const r = useMemo(() => {
    if (!repartoCuadra) return null;
    if (sinReferenciaReal) return null;
    return calcular({
      pesoKg,
      porcentajeGrasa: grasaPct,
      estaturaCm,
      edad: edadAnios,
      sexo: sexoCliente,
      actividad,
      porcentajeAjuste: ajustePct / 100,
      reparto: {
        carbohidrato: reparto.carbohidrato / 100,
        proteina: reparto.proteina / 100,
        grasa: reparto.grasa / 100,
      },
      baseProteina,
      diasRefeed,
      porcentajeDiaRefeed: refeedPct / 100,
      porcentajeGrasaObjetivo: grasaObjetivoPct,
      relacionGanancia: p.relacionGanancia as RelacionGanancia,
      semanasGanancia,
    });
  }, [
    repartoCuadra,
    sinReferenciaReal,
    pesoKg,
    grasaPct,
    estaturaCm,
    edadAnios,
    sexoCliente,
    p,
    actividad,
    ajustePct,
    reparto,
    baseProteina,
    diasRefeed,
    refeedPct,
    grasaObjetivoPct,
    semanasGanancia,
  ]);

  const comp = r?.composicion;

  /** Guarda el borrador o publica. Las guardas se vuelven a evaluar en el servidor: guardar
   *  siempre se permite —el plan puede quedar a medias— pero publicar exige que esté completo. */
  async function guardar(publicar: boolean) {
    setFallo(null);
    setHecho(null);
    setGuardando(publicar ? "publicar" : "borrador");
    try {
      await api.coach.guardarPlan(exp.alumnaUlid, {
        tipo: "nutricion",
        contenido: { notas: notasNutricion, tiempos },
        kcalObjetivo: r ? Math.round(r.energia.ajustadasKcal) : null,
        proteinaG: r ? Math.round(r.macros.proteina) : null,
        carbohidratoG: r ? Math.round(r.macros.carbohidrato) : null,
        grasaG: r ? Math.round(r.macros.grasa) : null,
        publicar,
        frecuenciaFotos,
        // Solo si cuadran: la base exige que el reparto sume exactamente 1.
        ...(repartoCuadra
          ? {
              parametros: {
                actividad,
                porcentajeAjuste: ajustePct / 100,
                reparto: {
                  carbohidrato: reparto.carbohidrato / 100,
                  proteina: reparto.proteina / 100,
                  grasa: reparto.grasa / 100,
                },
                baseProteina,
                diasRefeed,
                porcentajeDiaRefeed: refeedPct / 100,
                relacionGanancia: p.relacionGanancia,
              },
            }
          : {}),
      });
      await api.coach.guardarPlan(exp.alumnaUlid, {
        tipo: "entrenamiento",
        contenido: { notas: notasEntrenamiento, plantilla, dias },
        publicar,
      });
      setHecho(publicar ? t("Plan publicado. La alumna ya lo ve.") : t("Borrador guardado."));
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : t("No se pudo guardar."));
    } finally {
      setGuardando(null);
    }
  }

  return (
    <div className="flex flex-col gap-10">
      <div className="flex flex-col gap-4">
        <Link
          to={`/coach/alumnas`}
          className="flex w-fit items-center gap-2 text-menor text-tinta-media hover:text-tinta"
        >
          <ArrowLeft className="size-4" /> {t("Pacientes")}
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-3">
            <Etiqueta>{t("Ciclo {n} · borrador", { n: String(exp.ciclo) })}</Etiqueta>
            <Portada>{t("Plan de {alumna}", { alumna: exp.alumna })}</Portada>
          </div>
          <div className="flex flex-wrap gap-2">
            <Boton
              tono="discreto"
              onClick={() =>
                void descargarPdf(
                  `/documentos/plan-nutricion?alumna_ulid=${exp.alumnaUlid}`,
                  `plan-${exp.alumna}.pdf`,
                ).catch(() => undefined)
              }
            >
              {t("PDF nutrición")}
            </Boton>
            <Boton
              tono="discreto"
              onClick={() =>
                void descargarPdf(
                  `/documentos/rutina?alumna_ulid=${exp.alumnaUlid}`,
                  `rutina-${exp.alumna}.pdf`,
                ).catch(() => undefined)
              }
            >
              {t("PDF rutina")}
            </Boton>
            <Boton tono="contorno" disabled={guardando !== null} onClick={() => void guardar(false)}>
              {guardando === "borrador" ? t("Guardando…") : t("Guardar borrador")}
            </Boton>
            <Boton
              disabled={!chequeoValidado || !r || guardando !== null}
              onClick={() => void guardar(true)}
            >
              {guardando === "publicar" ? t("Publicando…") : t("Publicar")}
            </Boton>
          </div>
        </div>
      </div>

      {fallo ? <Aviso tono="error" titulo={t("No se pudo guardar")}>{fallo}</Aviso> : null}
      {hecho ? <Aviso tono="exito">{hecho}</Aviso> : null}

      {!chequeoValidado ? (
        <Aviso tono="error" titulo={t("No se puede publicar todavía")}>
          {chequeo
            ? t("El chequeo de {fecha} sigue sin validar.", { fecha: fecha(chequeo.fecha) })
            : t("Todavía no hay ningún chequeo en este ciclo.")}{" "}
          {t("Sin chequeo validado no se publica plan nuevo: es la guarda de continuidad del método.")}{" "}
          <Link to={`/coach/validar/${exp.alumnaUlid}`} className="underline underline-offset-2">
            {t("Ir a validarlo")}
          </Link>
        </Aviso>
      ) : null}

      <div role="tablist" aria-label={t("Secciones del expediente")} className="flex gap-6 border-b border-linea">
        {(
          [
            ["expediente", "Expediente"],
            ["calculadora", "Calculadora"],
            ["programa", "Programa"],
          ] as const
        ).map(([id, rotulo]) => (
          <button
            key={id}
            role="tab"
            aria-selected={seccion === id}
            onClick={() => setSeccion(id)}
            className={cn(
              "-mb-px border-b-2 pb-3 text-menor font-medium",
              "transition-colors duration-[var(--mov-rapido)] ease-suave",
              seccion === id
                ? "border-acento text-tinta"
                : "border-transparent text-tinta-suave hover:text-tinta",
            )}
          >
            {t(rotulo)}
          </button>
        ))}
      </div>

      <div
        className={cn(
          "grid gap-10",
          seccion === "expediente" && "lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]",
        )}
      >
        <div className="flex flex-col gap-10">
          {/* ---- Composición: sale del chequeo, no se teclea ---- */}
          {seccion === "expediente" && chequeoValidado ? <section className="flex flex-col gap-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div className="flex flex-col gap-1">
                <Titulo>{t("Composición corporal")}</Titulo>
                <Apoyo>
                  {chequeo
                    ? t("Del chequeo del {fecha}. No se captura aquí.", { fecha: fecha(chequeo.fecha) })
                    : t("Sin chequeo en este ciclo todavía.")}
                </Apoyo>
              </div>
              <Boton asChild tono="discreto" medida="chica">
                <Link to={`/coach/validar/${exp.alumnaUlid}`}>{t("Ver el chequeo")}</Link>
              </Boton>
            </div>

            {comp ? (
              <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
                {[
                  ["Peso", `${num(comp.pesoKg)} kg`],
                  ["% de grasa", `${num(comp.porcentajeGrasa * 100, 1)} %`],
                  ["Masa grasa", `${num(comp.masaGrasaKg)} kg`],
                  ["Masa magra", `${num(comp.masaLibreDeGrasaKg)} kg`],
                  ["IMC", num(comp.imc)],
                  ["Clasificación", comp.clasificacionImc],
                  ["Peso ideal (Broca)", `${num(comp.pesoIdealBrocaKg, 0)} kg`],
                  ["Diferencia", `${num(comp.diferenciaPesoEstaturaKg)} kg`],
                ].map(([k, v]) => (
                  <div key={k} className="flex flex-col gap-0.5">
                    <dt className="text-micro font-semibold uppercase tracking-[0.08em] text-tinta-suave">
                      {t(k ?? "")}
                    </dt>
                    <dd className="cifra text-guia font-semibold">{v}</dd>
                  </div>
                ))}
              </dl>
            ) : (
              <Aviso tono="atencion" titulo={t("Falta el porcentaje de grasa")}>
                {t("Estímalo al validar el chequeo. Es la entrada que manda toda la cadena de cálculo.")}
              </Aviso>
            )}
          </section> : seccion === "expediente" ? (
            <section className="flex flex-col gap-4">
              <div className="flex flex-col gap-1">
                <Titulo>{t("Composición corporal")}</Titulo>
                <Apoyo>{t("Sin chequeo validado todavía.")}</Apoyo>
              </div>
              <Aviso tono="atencion" titulo={t("Aún no hay composición que mostrar")}>
                <p>
                  {t("Aún no hay un chequeo validado del que salga el peso, las medidas y la composición")}
                </p>
                <Link to={`/coach/validar/${exp.alumnaUlid}`} className="underline underline-offset-2">
                  {t("Ir a validar el chequeo")}
                </Link>
              </Aviso>
            </section>
          ) : null}

          {seccion === "expediente" ? <Regla /> : null}

          {seccion === "expediente" ? (
            <CalendarioDeCobros
              alumnaUlid={exp.alumnaUlid}
              precioSugerido={exp.planPrecio}
              nombreDelPlan={exp.planNombre}
            />
          ) : null}

          {/* ---- Entradas de la calculadora ---- */}
          {seccion === "calculadora" ? <section className="flex flex-col gap-5">
            <div className="flex flex-col gap-1">
              <Titulo>{t("Calculadora")}</Titulo>
              <Apoyo>
                {t("Mueve cualquier campo y todo se recalcula. Estos parámetros quedan guardados en el ciclo, para poder entender después por qué un mes funcionó y otro no.")}
              </Apoyo>
            </div>

            {sinReferenciaReal ? (
              <Aviso tono="atencion" titulo={t("Falta el primer chequeo validado")}>
                <p>
                  {t("Sin un chequeo validado no hay peso real con qué calcular, así que la calculadora queda vacía. Valida el primer chequeo de este ciclo y aquí aparecerán sus cifras.")}
                </p>
                <Link to={`/coach/validar/${exp.alumnaUlid}`} className="underline underline-offset-2">
                  {t("Ir a validar el chequeo")}
                </Link>
              </Aviso>
            ) : null}

            <div className="grid gap-3 sm:grid-cols-3">
              <Campo id="c-actividad" etiqueta={t("Nivel de actividad")}>
                <Selector
                  id="c-actividad"
                  value={mActividad}
                  disabled={sinReferenciaReal}
                  onChange={(e) => setActividad(e.target.value as IdActividad)}
                >
                  {ACTIVIDAD.map((n) => (
                    <option key={n.id} value={n.id}>
                      {t(n.rotulo)} · ×{n.factor}
                    </option>
                  ))}
                </Selector>
              </Campo>

              <CampoNumeroEditable
                id="c-ajuste"
                etiqueta={t("Ajuste calórico")}
                sufijo="%"
                ayuda={t("Negativo es déficit, positivo es superávit.")}
                minimo={-50}
                maximo={30}
                valor={sinReferenciaReal ? 0 : ajustePct}
                onAplicar={setAjustePct}
                deshabilitado={sinReferenciaReal}
              />

              <CampoNumeroEditable
                id="c-grasa-obj"
                etiqueta={t("% Grasa objetivo")}
                sufijo="%"
                ayuda={t("Meta para proyectar la pérdida.")}
                paso={0.5}
                minimo={3}
                maximo={50}
                valor={sinReferenciaReal ? 0 : Math.round(grasaObjetivoPct * 1000) / 10}
                onAplicar={(n) => setGrasaObjetivoPct(Number(n) / 100)}
                deshabilitado={sinReferenciaReal}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Etiqueta>{t("Reparto de macros — tiene que sumar 100 %")}</Etiqueta>
              <div className="grid gap-4 sm:grid-cols-3">
                {MACROS.map((m) => (
                  <CampoPorcentaje
                    key={m}
                    id={`c-r-${m}`}
                    etiqueta={t(ROTULO_MACRO[m])}
                    minimo={0}
                    maximo={100}
                    valor={sinReferenciaReal ? 0 : reparto[m]}
                    onAplicar={(n) => setReparto((v) => ({ ...v, [m]: Number(n) }))}
                    deshabilitado={sinReferenciaReal}
                  />
                ))}
              </div>
              {!repartoCuadra ? (
                <Aviso tono="error" titulo={t("El reparto suma {suma} %", { suma: String(sumaReparto) })}>
                  {t("Tiene que sumar exactamente 100 % para poder calcular los gramos.")}
                </Aviso>
              ) : null}
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <Campo id="c-base" etiqueta={t("Proteína contra")}>
                <Selector
                  id="c-base"
                  value={mBase}
                  disabled={sinReferenciaReal}
                  onChange={(e) => setBaseProteina(e.target.value as BaseProteina)}
                >
                  <option value="masa_libre_de_grasa">{t("Masa libre de grasa")}</option>
                  <option value="peso_total">{t("Peso total")}</option>
                </Selector>
              </Campo>

              <Campo id="c-refeed" etiqueta={t("Días de refeed")}>
                <Selector
                  id="c-refeed"
                  value={mDiasRefeed}
                  disabled={sinReferenciaReal}
                  onChange={(e) => setDiasRefeed(Number(e.target.value))}
                >
                  <option value={0}>{t("Ninguno")}</option>
                  <option value={1}>{t("1 día por semana")}</option>
                  <option value={2}>{t("2 días por semana")}</option>
                </Selector>
              </Campo>

              <CampoNumeroEditable
                id="c-dia-bajo"
                etiqueta={t("Día bajo")}
                sufijo="%"
                ayuda={t("El déficit del día bajo de la semana, no confundir con el ajuste global.")}
                minimo={1}
                maximo={60}
                valor={sinReferenciaReal ? 0 : diaBajoPct}
                onAplicar={setDiaBajoPct}
                deshabilitado={sinReferenciaReal}
              />

              <CampoNumeroEditable
                id="c-refeed-pct"
                etiqueta={t("Déficit del refeed")}
                sufijo="%"
                ayuda={t("Cero es mantenimiento, que es lo habitual.")}
                minimo={0}
                maximo={40}
                valor={sinReferenciaReal ? 0 : refeedPct}
                onAplicar={setRefeedPct}
                deshabilitado={sinReferenciaReal}
              />
            </div>
          </section> : null}

          {seccion === "calculadora" ? <Regla /> : null}

          {/* ---- Resultado ---- */}
          {seccion === "calculadora" && r ? (
            <section className="flex flex-col gap-5">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div className="flex flex-col gap-1">
                  <Titulo>{t("Resultado")}</Titulo>
                  <Apoyo>
                    {t("TMB {tmb} kcal · mantenimiento {manto} kcal", {
                      tmb: num(r.tmbKcal, 0),
                      manto: num(r.energia.mantenimientoKcal, 0),
                    })}
                  </Apoyo>
                </div>
                <Chip tono={r.energia.esDeficit ? "exito" : "espera"}>
                  {r.energia.esDeficit ? t("Déficit") : t("Superávit")}
                </Chip>
              </div>

              <div className="grid grid-cols-2 gap-6 sm:grid-cols-3">
                <div className="flex flex-col gap-0.5">
                  <Etiqueta>{t("Objetivo diario")}</Etiqueta>
                  <p className="cifra text-portada font-semibold tracking-[-0.03em]">
                    {num(r.energia.ajustadasKcal, 0)}
                    <span className="ml-1.5 text-guia font-medium text-tinta-suave">kcal</span>
                  </p>
                </div>
                <div className="flex flex-col gap-0.5">
                  <Etiqueta>{t("Ajuste diario")}</Etiqueta>
                  <p className="cifra text-guia font-semibold">{num(r.energia.ajusteDiarioKcal, 0)} kcal</p>
                  {/* Para bajar entre 0.5 % y 1 % del peso por semana, que es el ritmo sano. */}
                  {r.energia.esDeficit ? (
                    <p className="cifra text-micro text-tinta-media">
                      {t("Recomendado −{min} a −{max}", {
                        min: num(r.deficitRecomendado.minimoKcal, 0),
                        max: num(r.deficitRecomendado.maximoKcal, 0),
                      })}
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-col gap-0.5">
                  <Etiqueta>{t("Ajuste semanal")}</Etiqueta>
                  <p className="cifra text-guia font-semibold">{num(r.energia.ajusteSemanalKcal, 0)} kcal</p>
                </div>
              </div>

              {diasRefeed > 0 ? (
                <Aviso
                  tono="info"
                  titulo={t("Con {n} {dias} de refeed, el déficit real de la semana es {pct} %", {
                    n: String(diasRefeed),
                    dias: diasRefeed === 1 ? t("día") : t("días"),
                    pct: num(deficitPromedioSemanal(diaBajoPct / 100, diasRefeed, refeedPct / 100) * 100),
                  })}
                >
                  {t("El día bajo va al {pct} %, pero lo que manda sobre el resultado es el promedio semanal.", {
                    pct: num(diaBajoPct),
                  })}
                </Aviso>
              ) : null}
            </section>
          ) : null}

          {/* ---- Tablas de la Calculadora ---- */}
          {seccion === "calculadora" && r ? (
            <TablaDatosCliente
              comp={r.composicion}
              onPeso={setPesoKg}
              onPorcentajeGrasa={setGrasaPct}
              estaturaCm={estaturaCm}
              onEstaturaCm={setEstaturaCm}
              edad={edadAnios}
              onEdad={setEdadAnios}
              sexo={sexoCliente}
              onSexo={setSexoCliente}
              actividad={actividad}
              onActividad={setActividad}
              ajustePct={ajustePct}
              onAjustePct={setAjustePct}
              prescripcion={r}
            />
          ) : null}

          {seccion === "calculadora" && r ? (
            <TablaDistribucionMacros
              comp={r.composicion}
              energia={r.energia}
              reparto={reparto}
              onReparto={setReparto}
              baseProteina={baseProteina}
              onBaseProteina={setBaseProteina}
            />
          ) : null}

          {seccion === "calculadora" && r ? (
            <TablaProyeccionPerdida
              comp={r.composicion}
              energia={r.energia}
              porcentajeGrasaObjetivo={grasaObjetivoPct}
              onPorcentajeGrasaObjetivo={setGrasaObjetivoPct}
              ajustePct={ajustePct}
            />
          ) : null}

          {seccion === "calculadora" && r ? (
            <TablaProyeccionGanancia
              comp={r.composicion}
              energia={r.energia}
              semanas={semanasGanancia}
              onSemanas={setSemanasGanancia}
            />
          ) : null}

          {seccion === "calculadora" && r ? (
            <TablaRefeeds
              diaBajoPct={diaBajoPct}
              onDiaBajoPct={(v) => setDiaBajoPct(Math.abs(v))}
              diasRefeed={diasRefeed}
              onDiasRefeed={setDiasRefeed}
              refeedPct={refeedPct}
              onRefeedPct={setRefeedPct}
            />
          ) : null}

          {seccion === "calculadora" ? <Hoja alumnaUlid={exp.alumnaUlid} soloTablas /> : null}

          {seccion === "calculadora" ? <Regla /> : null}

          {seccion === "calculadora" ? <Regla /> : null}

          {/* ---- Contenido del plan: aquí se edita de verdad ---- */}
          {seccion === "programa" ? <section className="flex flex-col gap-6">
            <div role="tablist" aria-label={t("Tipo de plan")} className="flex gap-6 border-b border-linea">
              {(
                [
                  ["nutricion", "Nutrición", UtensilsCrossed],
                  ["entrenamiento", "Entrenamiento", Dumbbell],
                ] as const
              ).map(([id, rotulo, Icono]) => (
                <button
                  key={id}
                  role="tab"
                  aria-selected={pestana === id}
                  onClick={() => setPestana(id)}
                  className={cn(
                    "-mb-px flex items-center gap-2 border-b-2 pb-3 text-menor font-medium",
                    "transition-colors duration-[var(--mov-rapido)] ease-suave",
                    pestana === id
                      ? "border-acento text-tinta"
                      : "border-transparent text-tinta-suave hover:text-tinta",
                  )}
                >
                  <Icono
                    aria-hidden
                    className="size-4 shrink-0"
                    strokeWidth={pestana === id ? 2.2 : 1.6}
                  />
                  {t(rotulo)}
                </button>
              ))}
            </div>

            {pestana === "nutricion" ? (
              <>
                <EditorNutricion
                  tiempos={tiempos}
                  onCambio={setTiempos}
                  objetivoKcal={r ? Math.round(r.energia.ajustadasKcal) : 0}
                  objetivoMacros={
                    r
                      ? {
                          proteina: Math.round(r.macros.proteina),
                          carbohidrato: Math.round(r.macros.carbohidrato),
                          grasa: Math.round(r.macros.grasa),
                        }
                      : null
                  }
                />
                <Campo
                  id="c-fotos"
                  etiqueta={t("Fotos de sus comidas")}
                  ayuda={t("Cada foto se borra sola a las 36 horas de que la manda.")}
                >
                  <Selector
                    id="c-fotos"
                    value={frecuenciaFotos}
                    onChange={(e) => setFrecuenciaFotos(e.target.value as FrecuenciaFotos)}
                    className="max-w-64"
                  >
                    {FRECUENCIAS.map(([valor, rotulo]) => (
                      <option key={valor} value={valor}>
                        {t(rotulo)}
                      </option>
                    ))}
                  </Selector>
                </Campo>

                <Campo id="c-notas-n" etiqueta={t("Notas para la alumna")}>
                  <textarea
                    id="c-notas-n"
                    rows={3}
                    value={notasNutricion}
                    onChange={(e) => setNotasNutricion(e.target.value)}
                    className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
                  />
                </Campo>
              </>
            ) : (
              <>
                <EditorEntrenamiento
                  dias={dias}
                  onCambio={setDias}
                  plantilla={plantilla}
                  onPlantilla={setPlantilla}
                  lesiones={clinico?.lesiones ?? null}
                />
                <Campo id="c-notas-e" etiqueta={t("Notas de ejecución")}>
                  <textarea
                    id="c-notas-e"
                    rows={3}
                    value={notasEntrenamiento}
                    onChange={(e) => setNotasEntrenamiento(e.target.value)}
                    className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
                  />
                </Campo>
              </>
            )}
          </section> : null}
        </div>

        {seccion === "expediente" ? <aside className="flex flex-col gap-8">
          <section className="flex flex-col gap-2 border-l-2 border-l-peligro pl-4">
            <Etiqueta>{t("Restricciones")}</Etiqueta>
            {clinico?.restricciones ? <Apoyo>{clinico.restricciones}</Apoyo> : null}
            {clinico?.lesiones ? <Apoyo>{clinico.lesiones}</Apoyo> : null}
            {!clinico?.restricciones && !clinico?.lesiones ? (
              <Apoyo>{t("Sin restricciones registradas en su historial.")}</Apoyo>
            ) : null}
          </section>

          <Regla />

          <FotosDeSusComidas alumnaUlid={exp.alumnaUlid} />

          <Regla />

          <RespuestasDelCuestionario alumnaUlid={exp.alumnaUlid} />

          <Regla />
        </aside> : null}
      </div>
    </div>
  );
}

/** Lo que contestó al entrar. Vive junto al plan porque es donde se decide qué comer y qué
 *  entrenar: quien duerme cinco horas no lleva el mismo volumen que quien duerme ocho. */
function RespuestasDelCuestionario({ alumnaUlid }: { alumnaUlid: string }) {
  const { t } = useIdioma();
  const carga = usarApi<RespuestaDeAlumnaApi[]>(
    (senal) => api.coach.respuestasDeAlumna(alumnaUlid, senal),
    [alumnaUlid],
  );
  const filas = carga.datos ?? [];
  if (carga.cargando || filas.length === 0) return null;

  return (
    <section className="flex flex-col gap-3">
      <Etiqueta>{t("Su cuestionario")}</Etiqueta>
      <dl className="flex flex-col gap-3">
        {filas.map((r) => (
          <div key={r.pregunta} className="flex flex-col gap-0.5">
            <dt className="text-micro text-tinta-suave">{r.pregunta}</dt>
            <dd className="text-menor">{r.valor || "—"}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

/** Lo que mando de sus comidas. Solo lo vigente: a las 36 horas deja de existir.
 *
 *  Vive junto al plan porque es donde sirve: se mira el plato contra lo que se le pidio. */
function FotosDeSusComidas({ alumnaUlid }: { alumnaUlid: string }) {
  const { t } = useIdioma();
  const carga = usarApi<FotoDeComidaApi[]>(
    (senal) => api.coach.fotosDeComida(alumnaUlid, senal),
    [alumnaUlid],
  );
  const [comentando, setComentando] = useState<string | null>(null);
  const [texto, setTexto] = useState("");

  const fotos = carga.datos ?? [];
  if (carga.cargando) return null;
  // Se muestra aunque esté vacío: si desaparece, la coach no sabe dónde mirar ni si su
  // alumna mandó algo. Vacío es una respuesta, no la ausencia de la pantalla.

  async function guardar(ulid: string) {
    try {
      await api.coach.comentarFotoDeComida(ulid, texto);
    } finally {
      setComentando(null);
      setTexto("");
      carga.recargar();
    }
  }

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between gap-2">
        <Etiqueta>{t("Sus comidas")}</Etiqueta>
        <Chip>{fotos.length}</Chip>
      </div>
      <Apoyo>{t("Se borran solas a las 36 horas de que las manda.")}</Apoyo>

      {fotos.length === 0 ? (
        <Apoyo>{t("Ahora mismo no tiene ninguna vigente.")}</Apoyo>
      ) : null}

      <ul className="grid grid-cols-2 gap-2">
        {fotos.map((f) => (
          <li key={f.ulid} className="flex flex-col gap-1">
            <img
              src={urlDeFotoDeComida(f.ulid)}
              alt={f.tiempo ?? t("Comida")}
              className="aspect-square w-full rounded-marco border border-linea object-cover"
            />
            <span className="text-micro text-tinta-media">{f.tiempo ?? t("Sin titulo")}</span>
            {f.nota ? <span className="text-micro text-tinta-suave">{f.nota}</span> : null}
            {comentando === f.ulid ? (
              <div className="flex flex-col gap-1">
                <Entrada
                  value={texto}
                  onChange={(e) => setTexto(e.target.value)}
                  placeholder={t("Buena porcion.")}
                  aria-label={t("Comentario")}
                  className="h-8 text-micro"
                />
                <Boton medida="chica" onClick={() => void guardar(f.ulid)}>
                  {t("Guardar")}
                </Boton>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => {
                  setComentando(f.ulid);
                  setTexto(f.comentario ?? "");
                }}
                className="text-left text-micro text-tinta-suave underline underline-offset-2"
              >
                {f.comentario ?? t("Comentar")}
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

