/** Constructor de planes con la calculadora metabólica integrada.
 *
 *  La coach captura actividad, ajuste calórico y reparto de macros; el sistema saca
 *  calorías y gramos con las fórmulas de su propio Excel. Deja de teclear gramos a mano y
 *  de brincar entre la hoja y el panel.
 *
 *  Dos guardas que también vive el servidor (`app/dominio/plan.py`): sin chequeo validado
 *  no se publica plan nuevo, y sin calorías ni macros tampoco.
 *
 *  La proyección **solo la ve la coach**: asume adherencia perfecta, y enseñarle a la
 *  alumna una fecha exacta convierte una estimación en una promesa.
 */

import { ArrowLeft } from "lucide-react";
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
import { normalizarAlimento } from "@/coach/BuscadorCatalogo";
import {
  EditorEntrenamiento,
  EditorNutricion,
  type DiaDeEntrenamiento,
  type TiempoDeComida,
} from "@/coach/EditorPlan";
import { CalendarioDeCobros } from "@/coach/CalendarioDeCobros";
import { Hoja } from "@/coach/Hoja";
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
  ROTULO_MACRO,
  RANGO_GKG,
  calcular,
  kcalDe,
  type BaseProteina,
  type IdActividad,
  type Macro,
  type RelacionGanancia,
} from "@/lib/calculadora";
import { edadEn, fecha, num, porcentaje } from "@/lib/formato";
import { usarApi } from "@/lib/usarApi";

const MACROS: Macro[] = ["carbohidrato", "proteina", "grasa"];

/** Cada cuánto se le piden fotos de sus platos. Se guarda con el plan de nutrición. */
const FRECUENCIAS: [FrecuenciaFotos, string][] = [
  ["ninguna", "No pedirle fotos"],
  ["diaria", "Todos los días"],
  ["semanal", "Una vez por semana"],
  ["quincenal", "Cada quince días"],
  ["mensual", "Una vez al mes"],
];

/** Horizonte de la proyección de ganancia. No se captura: solo fija el «en N semanas». */
const SEMANAS_GANANCIA = 20;

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
  const { alumnaUlid = "" } = useParams();
  const carga = usarApi<ExpedienteDeConstructorApi>(
    (senal) => api.coach.expedienteDePlan(alumnaUlid, senal),
    [alumnaUlid],
  );
  const clinico = usarApi<HistorialApi>(
    (senal) => api.coach.historial(alumnaUlid, senal),
    [alumnaUlid],
  );

  if (carga.cargando) return <Vacio>Abriendo el expediente…</Vacio>;
  if (carga.error || !carga.datos) {
    return (
      <Aviso tono="error" titulo="No se pudo abrir el plan">
        {carga.error?.message ?? "Vuelve a intentarlo."}
      </Aviso>
    );
  }
  // La clave fuerza el remonte al cambiar de alumna: el estado de abajo nace de las props.
  return <Editor key={alumnaUlid} exp={carga.datos} clinico={clinico.datos} />;
}

function Editor({ exp, clinico }: { exp: ExpedienteDeConstructorApi; clinico: HistorialApi | null }) {
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
    if (!repartoCuadra || !chequeo?.pesoKg || chequeo.porcentajeGrasa === null) return null;
    if (exp.estaturaCm === null) return null;
    return calcular({
      pesoKg: chequeo.pesoKg,
      porcentajeGrasa: chequeo.porcentajeGrasa,
      estaturaCm: exp.estaturaCm,
      edad: edadEn(exp.fechaNacimiento, new Date().toISOString().slice(0, 10)),
      sexo: exp.sexo === "M" ? "masculino" : "femenino",
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
      // Sin meta de grasa no hay proyección: se pasa la actual y la calculadora la descarta.
      porcentajeGrasaObjetivo: exp.porcentajeGrasaObjetivo ?? chequeo.porcentajeGrasa,
      relacionGanancia: p.relacionGanancia as RelacionGanancia,
      semanasGanancia: SEMANAS_GANANCIA,
    });
  }, [repartoCuadra, chequeo, exp, p, actividad, ajustePct, reparto, baseProteina, diasRefeed, refeedPct]);

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
      setHecho(publicar ? "Plan publicado. La alumna ya lo ve." : "Borrador guardado.");
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo guardar.");
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
          <ArrowLeft className="size-4" /> Alumnas
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-3">
            <Etiqueta>Ciclo {exp.ciclo} · borrador</Etiqueta>
            <Portada>Plan de {exp.alumna}</Portada>
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
              PDF nutrición
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
              PDF rutina
            </Boton>
            <Boton tono="contorno" disabled={guardando !== null} onClick={() => void guardar(false)}>
              {guardando === "borrador" ? "Guardando…" : "Guardar borrador"}
            </Boton>
            <Boton
              disabled={!chequeoValidado || !r || guardando !== null}
              onClick={() => void guardar(true)}
            >
              {guardando === "publicar" ? "Publicando…" : "Publicar"}
            </Boton>
          </div>
        </div>
      </div>

      {fallo ? <Aviso tono="error" titulo="No se pudo guardar">{fallo}</Aviso> : null}
      {hecho ? <Aviso tono="exito">{hecho}</Aviso> : null}

      {!chequeoValidado ? (
        <Aviso tono="error" titulo="No se puede publicar todavía">
          {chequeo
            ? `El chequeo de ${fecha(chequeo.fecha)} sigue sin validar.`
            : "Todavía no hay ningún chequeo en este ciclo."}{" "}
          Sin chequeo validado no se publica plan nuevo: es la guarda de continuidad del
          método.{" "}
          <Link to={`/coach/validar/${exp.alumnaUlid}`} className="underline underline-offset-2">
            Ir a validarlo
          </Link>
        </Aviso>
      ) : null}

      <div className="grid gap-10 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-10">
          {/* ---- Composición: sale del chequeo, no se teclea ---- */}
          <section className="flex flex-col gap-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div className="flex flex-col gap-1">
                <Titulo>Composición corporal</Titulo>
                <Apoyo>
                  {chequeo
                    ? `Del chequeo del ${fecha(chequeo.fecha)}. No se captura aquí.`
                    : "Sin chequeo en este ciclo todavía."}
                </Apoyo>
              </div>
              <Boton asChild tono="discreto" medida="chica">
                <Link to={`/coach/validar/${exp.alumnaUlid}`}>Ver el chequeo</Link>
              </Boton>
            </div>

            {comp ? (
              <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
                {[
                  ["Peso", `${num(comp.pesoKg)} kg`],
                  ["% de grasa", porcentaje(comp.porcentajeGrasa)],
                  ["Masa grasa", `${num(comp.masaGrasaKg)} kg`],
                  ["Masa magra", `${num(comp.masaLibreDeGrasaKg)} kg`],
                  ["IMC", num(comp.imc)],
                  ["Clasificación", comp.clasificacionImc],
                  ["Peso ideal (Broca)", `${num(comp.pesoIdealBrocaKg, 0)} kg`],
                  ["Diferencia", `${num(comp.diferenciaPesoEstaturaKg)} kg`],
                ].map(([k, v]) => (
                  <div key={k} className="flex flex-col gap-0.5">
                    <dt className="text-micro font-semibold uppercase tracking-[0.08em] text-tinta-suave">
                      {k}
                    </dt>
                    <dd className="cifra text-guia font-semibold">{v}</dd>
                  </div>
                ))}
              </dl>
            ) : (
              <Aviso tono="atencion" titulo="Falta el porcentaje de grasa">
                Estímalo al validar el chequeo. Es la entrada que manda toda la cadena de cálculo.
              </Aviso>
            )}
          </section>

          <Regla />

          {/* ---- Entradas de la calculadora ---- */}
          <section className="flex flex-col gap-5">
            <div className="flex flex-col gap-1">
              <Titulo>Calculadora</Titulo>
              <Apoyo>
                Mueve cualquier campo y todo se recalcula. Estos parámetros quedan guardados en
                el ciclo, para poder entender después por qué un mes funcionó y otro no.
              </Apoyo>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Campo id="c-actividad" etiqueta="Nivel de actividad">
                <Selector
                  id="c-actividad"
                  value={actividad}
                  onChange={(e) => setActividad(e.target.value as IdActividad)}
                >
                  {ACTIVIDAD.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.rotulo} · ×{n.factor}
                    </option>
                  ))}
                </Selector>
              </Campo>

              <Campo
                id="c-ajuste"
                etiqueta="Ajuste calórico"
                sufijo="%"
                ayuda="Negativo es déficit, positivo es superávit."
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
            </div>

            <div className="flex flex-col gap-2">
              <Etiqueta>Reparto de macros — tiene que sumar 100 %</Etiqueta>
              <div className="grid gap-4 sm:grid-cols-3">
                {MACROS.map((m) => (
                  <Campo key={m} id={`c-r-${m}`} etiqueta={ROTULO_MACRO[m]} sufijo="%">
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
                <Aviso tono="error" titulo={`El reparto suma ${sumaReparto} %`}>
                  Tiene que sumar exactamente 100 % para poder calcular los gramos.
                </Aviso>
              ) : null}
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <Campo id="c-base" etiqueta="Proteína contra">
                <Selector
                  id="c-base"
                  value={baseProteina}
                  onChange={(e) => setBaseProteina(e.target.value as BaseProteina)}
                >
                  <option value="masa_libre_de_grasa">Masa libre de grasa</option>
                  <option value="peso_total">Peso total</option>
                </Selector>
              </Campo>

              <Campo id="c-refeed" etiqueta="Días de refeed">
                <Selector
                  id="c-refeed"
                  value={diasRefeed}
                  onChange={(e) => setDiasRefeed(Number(e.target.value))}
                >
                  <option value={0}>Ninguno</option>
                  <option value={1}>1 día por semana</option>
                  <option value={2}>2 días por semana</option>
                </Selector>
              </Campo>

              <Campo
                id="c-refeed-pct"
                etiqueta="Déficit del refeed"
                sufijo="%"
                ayuda="Cero es mantenimiento, que es lo habitual."
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
          </section>

          <Regla />

          {/* ---- Resultado ---- */}
          {r ? (
            <section className="flex flex-col gap-5">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div className="flex flex-col gap-1">
                  <Titulo>Resultado</Titulo>
                  <Apoyo>
                    TMB {num(r.tmbKcal, 0)} kcal · mantenimiento {num(r.energia.mantenimientoKcal, 0)} kcal
                  </Apoyo>
                </div>
                <Chip tono={r.energia.esDeficit ? "exito" : "espera"}>
                  {r.energia.esDeficit ? "Déficit" : "Superávit"}
                </Chip>
              </div>

              <div className="grid grid-cols-2 gap-6 sm:grid-cols-3">
                <div className="flex flex-col gap-0.5">
                  <Etiqueta>Objetivo diario</Etiqueta>
                  <p className="cifra text-portada font-semibold tracking-[-0.03em]">
                    {num(r.energia.ajustadasKcal, 0)}
                    <span className="ml-1.5 text-guia font-medium text-tinta-suave">kcal</span>
                  </p>
                </div>
                <div className="flex flex-col gap-0.5">
                  <Etiqueta>Ajuste diario</Etiqueta>
                  <p className="cifra text-guia font-semibold">{num(r.energia.ajusteDiarioKcal, 0)} kcal</p>
                </div>
                <div className="flex flex-col gap-0.5">
                  <Etiqueta>Ajuste semanal</Etiqueta>
                  <p className="cifra text-guia font-semibold">{num(r.energia.ajusteSemanalKcal, 0)} kcal</p>
                </div>
              </div>

              <ul className="flex flex-col divide-y divide-linea border-y border-linea">
                {MACROS.map((m) => {
                  const fuera = r.avisosDeRango.includes(m);
                  const [min, max] = RANGO_GKG[m];
                  return (
                    <li key={m} className="flex flex-wrap items-baseline justify-between gap-3 py-3">
                      <span className="text-menor font-medium">{ROTULO_MACRO[m]}</span>
                      <span className="flex items-baseline gap-5">
                        <span className="cifra text-guia font-semibold">{num(r.macros[m], 0)} g</span>
                        <span className="cifra text-menor text-tinta-suave">
                          {num(kcalDe(m, r.macros[m]), 0)} kcal
                        </span>
                        <span className="cifra w-14 text-right text-menor">
                          {num(r.gramosPorKilo[m], 2)}
                        </span>
                        {fuera ? (
                          <Chip tono="espera">
                            fuera de {min}–{max}
                          </Chip>
                        ) : (
                          <span className="w-24 text-micro text-tinta-suave">
                            ref. {min}–{max} g/kg
                          </span>
                        )}
                      </span>
                    </li>
                  );
                })}
              </ul>

              <Apoyo>
                Proteína expresada contra{" "}
                {baseProteina === "peso_total" ? "peso total" : "masa libre de grasa"}.
              </Apoyo>

              {r.avisosDeRango.length ? (
                <Aviso
                  tono="atencion"
                  titulo={`${r.avisosDeRango.map((m) => ROTULO_MACRO[m]).join(" y ")} fuera del rango de referencia`}
                >
                  No bloquea la publicación; revisa si es intencional.
                </Aviso>
              ) : null}

              {r.deficitPromedioSemanal !== null ? (
                <Aviso
                  tono="info"
                  titulo={`Con ${diasRefeed} ${diasRefeed === 1 ? "día" : "días"} de refeed, el déficit real de la semana es ${num(r.deficitPromedioSemanal * 100)} %`}
                >
                  El día bajo va al {num(Math.abs(ajustePct))} %, pero lo que manda sobre el
                  resultado es el promedio semanal.
                </Aviso>
              ) : null}
            </section>
          ) : null}

          <Regla />

          {/* ---- La misma cuenta, con la forma de su hoja ---- */}
          <Hoja alumnaUlid={exp.alumnaUlid} />

          <Regla />

          {/* ---- Contenido del plan: aquí se edita de verdad ---- */}
          <section className="flex flex-col gap-6">
            <div role="tablist" aria-label="Tipo de plan" className="flex gap-6 border-b border-linea">
              {(
                [
                  ["nutricion", "Nutrición"],
                  ["entrenamiento", "Entrenamiento"],
                ] as const
              ).map(([id, rotulo]) => (
                <button
                  key={id}
                  role="tab"
                  aria-selected={pestana === id}
                  onClick={() => setPestana(id)}
                  className={
                    pestana === id
                      ? "-mb-px border-b-2 border-acento pb-3 text-menor font-medium text-tinta"
                      : "-mb-px border-b-2 border-transparent pb-3 text-menor font-medium text-tinta-suave hover:text-tinta"
                  }
                >
                  {rotulo}
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
                  etiqueta="Fotos de sus comidas"
                  ayuda="Cada foto se borra sola a las 36 horas de que la manda."
                >
                  <Selector
                    id="c-fotos"
                    value={frecuenciaFotos}
                    onChange={(e) => setFrecuenciaFotos(e.target.value as FrecuenciaFotos)}
                    className="max-w-64"
                  >
                    {FRECUENCIAS.map(([valor, rotulo]) => (
                      <option key={valor} value={valor}>
                        {rotulo}
                      </option>
                    ))}
                  </Selector>
                </Campo>

                <Campo id="c-notas-n" etiqueta="Notas para la alumna">
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
                <Campo id="c-notas-e" etiqueta="Notas de ejecución">
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
          </section>
        </div>

        {/* ---- Proyección: solo la coach ---- */}
        <aside className="flex flex-col gap-8">
          <section className="filete flex flex-col gap-4">
            <Etiqueta>Proyección · solo tú la ves</Etiqueta>
            {r?.proyeccionPerdida ? (
              <>
                <Titulo>Al ritmo de este plan</Titulo>
                <dl className="flex flex-col gap-2 text-menor">
                  {[
                    ["Grasa por bajar", `${num(r.proyeccionPerdida.kgGrasaPorBajar)} kg`],
                    ["Masa magra que se va", `${num(r.proyeccionPerdida.kgMlgQueSePierden)} kg`],
                    ["Peso total por bajar", `${num(r.proyeccionPerdida.kgTotalesPorBajar)} kg`],
                    ["Pérdida semanal", `${num(r.proyeccionPerdida.perdidaSemanalKg, 2)} kg`],
                    ["Días estimados", num(r.proyeccionPerdida.diasEstimados, 0)],
                  ].map(([k, v]) => (
                    <div key={k} className="flex items-baseline justify-between gap-3">
                      <dt className="text-tinta-suave">{k}</dt>
                      <dd className="cifra font-semibold">{v}</dd>
                    </div>
                  ))}
                </dl>

                <Aviso tono={r.proyeccionPerdida.dentroDeLoRecomendado ? "exito" : "error"}>
                  {r.proyeccionPerdida.dentroDeLoRecomendado
                    ? `Dentro del ritmo recomendado (${num(r.proyeccionPerdida.recomendadoMinKg, 2)} a ${num(r.proyeccionPerdida.recomendadoMaxKg, 2)} kg por semana).`
                    : `Fuera del ritmo recomendado. Lo sano para ella es entre ${num(r.proyeccionPerdida.recomendadoMinKg, 2)} y ${num(r.proyeccionPerdida.recomendadoMaxKg, 2)} kg por semana. Suaviza el déficit.`}
                </Aviso>

                <Apoyo>
                  Supone adherencia perfecta. No se le muestra a la alumna: una fecha exacta
                  convierte una estimación en una promesa.
                </Apoyo>
              </>
            ) : r?.proyeccionGanancia ? (
              <>
                <Titulo>Fase de ganancia</Titulo>
                <dl className="flex flex-col gap-2 text-menor">
                  {[
                    ["Aumento semanal", `${num(r.proyeccionGanancia.aumentoSemanalKg, 2)} kg`],
                    ["De eso, músculo", `${num(r.proyeccionGanancia.musculoSemanalKg, 2)} kg`],
                    [`En ${r.proyeccionGanancia.semanas} semanas`, `${num(r.proyeccionGanancia.aumentoTotalKg)} kg`],
                    ["Músculo estimado", `${num(r.proyeccionGanancia.musculoTotalKg)} kg`],
                    ["Grasa estimada", `${num(r.proyeccionGanancia.grasaTotalKg)} kg`],
                  ].map(([k, v]) => (
                    <div key={k} className="flex items-baseline justify-between gap-3">
                      <dt className="text-tinta-suave">{k}</dt>
                      <dd className="cifra font-semibold">{v}</dd>
                    </div>
                  ))}
                </dl>
                <Apoyo>Relación {p.relacionGanancia} entre músculo y grasa ganados.</Apoyo>
              </>
            ) : (
              <Apoyo>Sin ajuste calórico no hay proyección que hacer.</Apoyo>
            )}
          </section>

          <section className="flex flex-col gap-2 border-l-2 border-l-peligro pl-4">
            <Etiqueta>Restricciones de la alumna</Etiqueta>
            {clinico?.restricciones ? <Apoyo>{clinico.restricciones}</Apoyo> : null}
            {clinico?.lesiones ? <Apoyo>{clinico.lesiones}</Apoyo> : null}
            {!clinico?.restricciones && !clinico?.lesiones ? (
              <Apoyo>Sin restricciones registradas en su historial.</Apoyo>
            ) : null}
          </section>

          <Regla />

          <FotosDeSusComidas alumnaUlid={exp.alumnaUlid} />

          <Regla />

          <RespuestasDelCuestionario alumnaUlid={exp.alumnaUlid} />

          <Regla />

          <CalendarioDeCobros alumnaUlid={exp.alumnaUlid} precioSugerido={null} />
        </aside>
      </div>
    </div>
  );
}

/** Lo que contestó al entrar. Vive junto al plan porque es donde se decide qué comer y qué
 *  entrenar: quien duerme cinco horas no lleva el mismo volumen que quien duerme ocho. */
function RespuestasDelCuestionario({ alumnaUlid }: { alumnaUlid: string }) {
  const carga = usarApi<RespuestaDeAlumnaApi[]>(
    (senal) => api.coach.respuestasDeAlumna(alumnaUlid, senal),
    [alumnaUlid],
  );
  const filas = carga.datos ?? [];
  if (carga.cargando || filas.length === 0) return null;

  return (
    <section className="flex flex-col gap-3">
      <Etiqueta>Su cuestionario</Etiqueta>
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
  const carga = usarApi<FotoDeComidaApi[]>(
    (senal) => api.coach.fotosDeComida(alumnaUlid, senal),
    [alumnaUlid],
  );
  const [comentando, setComentando] = useState<string | null>(null);
  const [texto, setTexto] = useState("");

  const fotos = carga.datos ?? [];
  if (carga.cargando || fotos.length === 0) return null;

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
        <Etiqueta>Sus comidas</Etiqueta>
        <Chip>{fotos.length}</Chip>
      </div>
      <Apoyo>Se borran solas a las 36 horas de que las manda.</Apoyo>

      <ul className="grid grid-cols-2 gap-2">
        {fotos.map((f) => (
          <li key={f.ulid} className="flex flex-col gap-1">
            <img
              src={urlDeFotoDeComida(f.ulid)}
              alt={f.tiempo ?? "Comida"}
              className="aspect-square w-full rounded-marco border border-linea object-cover"
            />
            <span className="text-micro text-tinta-media">{f.tiempo ?? "Sin titulo"}</span>
            {f.nota ? <span className="text-micro text-tinta-suave">{f.nota}</span> : null}
            {comentando === f.ulid ? (
              <div className="flex flex-col gap-1">
                <Entrada
                  value={texto}
                  onChange={(e) => setTexto(e.target.value)}
                  placeholder="Buena porcion."
                  aria-label="Comentario"
                  className="h-8 text-micro"
                />
                <Boton medida="chica" onClick={() => void guardar(f.ulid)}>
                  Guardar
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
                {f.comentario ?? "Comentar"}
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
