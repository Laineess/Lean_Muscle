/** Constructor de planes con la calculadora metabólica integrada.
 *
 *  Dos guardas que también vive el servidor (`app/dominio/plan.py`): sin chequeo validado no
 *  se publica plan nuevo, y sin calorías ni macros tampoco.
 *
 *  La proyección solo la ve la coach: asume adherencia perfecta, y enseñársela a la alumna
 *  convertiría una estimación en una promesa.
 */

import { ArrowLeft, Dumbbell, UtensilsCrossed } from "lucide-react";
import { useMemo, useState } from "react";
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
  const [reparto, setReparto] = useState({
    carbohidrato: Math.round(p.reparto.carbohidrato * 100),
    proteina: Math.round(p.reparto.proteina * 100),
    grasa: Math.round(p.reparto.grasa * 100),
  });
  const [baseProteina, setBaseProteina] = useState<BaseProteina>(p.baseProteina as BaseProteina);
  const [diasRefeed, setDiasRefeed] = useState(p.diasRefeed);
  const [refeedPct, setRefeedPct] = useState(Math.round(p.porcentajeDiaRefeed * 100));
  const [pesoKg, setPesoKg] = useState<number>(chequeo?.pesoKg ?? 65);
  const [grasaPct, setGrasaPct] = useState<number>(chequeo?.porcentajeGrasa ?? 0.26);
  const [estaturaCm, setEstaturaCm] = useState<number>(exp.estaturaCm ?? 165);
  const [edadAnios, setEdadAnios] = useState<number>(
    edadEn(exp.fechaNacimiento, new Date().toISOString().slice(0, 10)) || 30,
  );
  const [sexoCliente, setSexoCliente] = useState<Sexo>(
    exp.sexo === "M" ? "masculino" : "femenino",
  );
  const [semanasGanancia, setSemanasGanancia] = useState(SEMANAS_GANANCIA);
  const [grasaObjetivoPct, setGrasaObjetivoPct] = useState<number>(
    exp.porcentajeGrasaObjetivo ??
      (chequeo?.porcentajeGrasa ? Math.round(chequeo.porcentajeGrasa * 0.75 * 100) / 100 : 0.15),
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
  const chequeoValidado = chequeo?.estado === "validado";

  const r = useMemo(() => {
    if (!repartoCuadra) return null;
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
          {seccion === "expediente" ? <section className="flex flex-col gap-4">
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
          </section> : null}

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

            <div className="grid gap-4 sm:grid-cols-3">
              <Campo id="c-actividad" etiqueta={t("Nivel de actividad")}>
                <Selector
                  id="c-actividad"
                  value={actividad}
                  onChange={(e) => setActividad(e.target.value as IdActividad)}
                >
                  {ACTIVIDAD.map((n) => (
                    <option key={n.id} value={n.id}>
                      {t(n.rotulo)} · ×{n.factor}
                    </option>
                  ))}
                </Selector>
              </Campo>

              <Campo
                id="c-ajuste"
                etiqueta={t("Ajuste calórico")}
                sufijo="%"
                ayuda={t("Negativo es déficit, positivo es superávit.")}
              >
                <Entrada
                  id="c-ajuste"
                  type="number"
                  step={1}
                  min={-50}
                  max={30}
                  value={ajustePct}
                  onChange={(e) => setAjustePct(Number(e.target.value))}
                  className="rounded-r-none"
                />
              </Campo>

              <Campo
                id="c-grasa-obj"
                etiqueta={t("% Grasa objetivo")}
                sufijo="%"
                ayuda={t("Meta para proyectar la pérdida.")}
              >
                <Entrada
                  id="c-grasa-obj"
                  type="number"
                  step={0.5}
                  min={3}
                  max={50}
                  value={Math.round(grasaObjetivoPct * 1000) / 10}
                  onChange={(e) => setGrasaObjetivoPct(Number(e.target.value) / 100)}
                  className="rounded-r-none"
                />
              </Campo>
            </div>

            <div className="flex flex-col gap-2">
              <Etiqueta>{t("Reparto de macros — tiene que sumar 100 %")}</Etiqueta>
              <div className="grid gap-4 sm:grid-cols-3">
                {MACROS.map((m) => (
                  <Campo key={m} id={`c-r-${m}`} etiqueta={t(ROTULO_MACRO[m])} sufijo="%">
                    <Entrada
                      id={`c-r-${m}`}
                      type="number"
                      step={1}
                      min={0}
                      max={100}
                      value={reparto[m]}
                      onChange={(e) => setReparto((v) => ({ ...v, [m]: Number(e.target.value) }))}
                      className="rounded-r-none"
                    />
                  </Campo>
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
                  value={baseProteina}
                  onChange={(e) => setBaseProteina(e.target.value as BaseProteina)}
                >
                  <option value="masa_libre_de_grasa">{t("Masa libre de grasa")}</option>
                  <option value="peso_total">{t("Peso total")}</option>
                </Selector>
              </Campo>

              <Campo id="c-refeed" etiqueta={t("Días de refeed")}>
                <Selector
                  id="c-refeed"
                  value={diasRefeed}
                  onChange={(e) => setDiasRefeed(Number(e.target.value))}
                >
                  <option value={0}>{t("Ninguno")}</option>
                  <option value={1}>{t("1 día por semana")}</option>
                  <option value={2}>{t("2 días por semana")}</option>
                </Selector>
              </Campo>

              <Campo
                id="c-refeed-pct"
                etiqueta={t("Déficit del refeed")}
                sufijo="%"
                ayuda={t("Cero es mantenimiento, que es lo habitual.")}
              >
                <Entrada
                  id="c-refeed-pct"
                  type="number"
                  step={1}
                  min={0}
                  max={40}
                  value={refeedPct}
                  onChange={(e) => setRefeedPct(Number(e.target.value))}
                  className="rounded-r-none"
                />
              </Campo>
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

              {r.deficitPromedioSemanal !== null ? (
                <Aviso
                  tono="info"
                  titulo={t("Con {n} {dias} de refeed, el déficit real de la semana es {pct} %", {
                    n: String(diasRefeed),
                    dias: diasRefeed === 1 ? t("día") : t("días"),
                    pct: num(r.deficitPromedioSemanal * 100),
                  })}
                >
                  {t("El día bajo va al {pct} %, pero lo que manda sobre el resultado es el promedio semanal.", {
                    pct: num(Math.abs(ajustePct)),
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
              onAjustePct={setAjustePct}
            />
          ) : null}

          {seccion === "calculadora" && r ? (
            <TablaProyeccionGanancia
              comp={r.composicion}
              energia={r.energia}
              semanas={semanasGanancia}
              onSemanas={setSemanasGanancia}
              ajustePct={ajustePct}
              onAjustePct={setAjustePct}
            />
          ) : null}

          {seccion === "calculadora" && r ? (
            <TablaRefeeds
              diaBajoPct={ajustePct}
              onDiaBajoPct={setAjustePct}
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

