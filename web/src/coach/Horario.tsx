/** Horario de consultas: los ratos en que la coach atiende y con cuánto aire.
 *
 *  De aquí salen los huecos que ve la alumna. Se guarda entero de una vez: el servidor
 *  reemplaza el horario completo, así que la pantalla carga lo que hay antes de tocarlo.
 */

import { Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { CargandoPantalla } from "@/componentes/Estado";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Entrada,
  Etiqueta,
  Portada,
  Regla,
  Titulo,
} from "@/componentes/primitivas";
import { ErrorApi, api, type HorarioDeCoachApi, type TramoDeHorarioApi } from "@/lib/api";
import { usarApi } from "@/lib/usarApi";

/** Lunes es 0, igual que en el servidor. */
const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

const HABILES = [0, 1, 2, 3, 4];

/** Los mismos topes que el servidor: pasarse aquí solo cambia un 422 por un aviso. */
const TOPES = {
  duracionConsultaMin: [15, 240],
  margenConsultaMin: [0, 120],
  antelacionHoras: [0, 720],
  horizonteSemanas: [1, 26],
} as const;

const MAXIMO_DE_TRAMOS = 60;

const TRAMO_NUEVO = { desde: "09:00", hasta: "13:00" };

function minutos(hhmm: string): number {
  const [h, m] = hhmm.split(":");
  return Number(h) * 60 + Number(m);
}

function hora(hhmm: string): string {
  return hhmm.slice(0, 5);
}

/** Cuántas consultas caben en un tramo. Es la misma cuenta que hace el servidor. */
function cuantasCaben(tramo: TramoDeHorarioApi, duracion: number, margen: number): number {
  const largo = minutos(tramo.hasta) - minutos(tramo.desde);
  if (largo < duracion) return 0;
  return Math.floor((largo - duracion) / (duracion + margen)) + 1;
}

function seEmpalman(a: TramoDeHorarioApi, b: TramoDeHorarioApi): boolean {
  return minutos(a.desde) < minutos(b.hasta) && minutos(b.desde) < minutos(a.hasta);
}

/** Lo que impide guardar, dicho para quien lo va a leer. */
function revisar(tramos: TramoDeHorarioApi[]): string | null {
  if (tramos.length > MAXIMO_DE_TRAMOS) {
    return `No puedes tener más de ${MAXIMO_DE_TRAMOS} tramos.`;
  }

  for (const t of tramos) {
    if (minutos(t.desde) >= minutos(t.hasta)) {
      return `${DIAS[t.diaSemana]}: la hora de fin tiene que ir después de la de inicio.`;
    }
  }
  for (let i = 0; i < tramos.length; i++) {
    for (let j = i + 1; j < tramos.length; j++) {
      const a = tramos[i]!;
      const b = tramos[j]!;
      if (a.diaSemana === b.diaSemana && seEmpalman(a, b)) {
        return `${DIAS[a.diaSemana]}: tienes dos tramos encimados.`;
      }
    }
  }
  return null;
}

export function Horario() {
  const carga = usarApi<HorarioDeCoachApi>((s) => api.coach.horario(s));

  const [tramos, setTramos] = useState<TramoDeHorarioApi[]>([]);
  const [numeros, setNumeros] = useState({
    duracionConsultaMin: 60,
    margenConsultaMin: 15,
    antelacionHoras: 24,
    horizonteSemanas: 8,
  });
  const [zona, setZona] = useState("America/Mexico_City");
  const [ocupado, setOcupado] = useState(false);
  const [guardado, setGuardado] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);

  useEffect(() => {
    if (!carga.datos) return;
    setTramos(carga.datos.tramos);
    setNumeros({
      duracionConsultaMin: carga.datos.duracionConsultaMin,
      margenConsultaMin: carga.datos.margenConsultaMin,
      antelacionHoras: carga.datos.antelacionHoras,
      horizonteSemanas: carga.datos.horizonteSemanas,
    });
    setZona(carga.datos.zonaHoraria);
  }, [carga.datos]);

  const problema = revisar(tramos);
  const porSemana = tramos.reduce(
    (suma, t) => suma + cuantasCaben(t, numeros.duracionConsultaMin, numeros.margenConsultaMin),
    0,
  );

  function cambiar(indice: number, campo: "desde" | "hasta", valor: string) {
    setGuardado(false);
    setTramos((xs) => xs.map((t, i) => (i === indice ? { ...t, [campo]: hora(valor) } : t)));
  }

  function agregar(dia: number) {
    setGuardado(false);
    setTramos((xs) => [...xs, { diaSemana: dia, ...TRAMO_NUEVO }]);
  }

  function quitar(indice: number) {
    setGuardado(false);
    setTramos((xs) => xs.filter((_, i) => i !== indice));
  }

  /** Casi todas atienden lo mismo de lunes a viernes; teclearlo cinco veces sobra. */
  function copiarAHabiles(dia: number) {
    setGuardado(false);
    setTramos((xs) => {
      const modelo = xs.filter((t) => t.diaSemana === dia);
      const resto = xs.filter((t) => !HABILES.includes(t.diaSemana));
      return [...resto, ...HABILES.flatMap((d) => modelo.map((t) => ({ ...t, diaSemana: d })))];
    });
  }

  function numero(clave: keyof typeof numeros, valor: string) {
    setGuardado(false);
    setNumeros((n) => ({ ...n, [clave]: Number(valor) }));
  }

  async function guardar() {
    if (problema) {
      setFallo(problema);
      return;
    }
    setFallo(null);
    setOcupado(true);
    try {
      // La zona va tal como se cargó: se cambia en Ajustes, y un PUT escribe todo el horario.
      const nuevo = await api.coach.guardarHorario({ tramos, ...numeros, zonaHoraria: zona });
      setTramos(nuevo.tramos);
      setGuardado(true);
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo guardar el horario.");
    } finally {
      setOcupado(false);
    }
  }

  if (carga.cargando) return <CargandoPantalla que="tu horario" filas={5} />;

  // Sin haber leído lo guardado no se guarda: el PUT reemplaza el horario entero y lo
  // dejaría vacío.
  if (carga.error) {
    return (
      <div className="flex flex-col gap-4">
        <Portada>Horario de consultas</Portada>
        <Aviso tono="error">{carga.error.message}</Aviso>
        <div>
          <Boton tono="contorno" onClick={carga.recargar}>
            Volver a intentar
          </Boton>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta>Cuándo pueden reservarte</Etiqueta>
        <Portada>Horario de consultas</Portada>
        <Apoyo>
          Las horas van en tu hora local ({zona.replace("_", " ")}). Cada alumna las ve
          convertidas a la suya.
        </Apoyo>
      </header>

      {tramos.length === 0 ? (
        <Aviso tono="atencion" titulo="Todavía no publicas horarios">
          Mientras esto esté vacío, tus alumnas no pueden reservar consulta contigo.
        </Aviso>
      ) : null}

      <section className="flex flex-col gap-6">
        {DIAS.map((rotulo, dia) => {
          const delDia = tramos
            .map((t, indice) => ({ t, indice }))
            .filter(({ t }) => t.diaSemana === dia);

          return (
            <div key={rotulo} className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <Titulo>{rotulo}</Titulo>
                <div className="flex items-center gap-2">
                  {delDia.length > 0 && HABILES.includes(dia) ? (
                    <Boton tono="discreto" medida="chica" onClick={() => copiarAHabiles(dia)}>
                      Copiar a lunes–viernes
                    </Boton>
                  ) : null}
                  <Boton tono="contorno" medida="chica" onClick={() => agregar(dia)}>
                    <Plus className="size-3.5" /> Tramo
                  </Boton>
                </div>
              </div>

              {delDia.length === 0 ? (
                <Apoyo>No atiendes este día.</Apoyo>
              ) : (
                <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
                  {delDia.map(({ t, indice }) => {
                    const caben = cuantasCaben(
                      t,
                      numeros.duracionConsultaMin,
                      numeros.margenConsultaMin,
                    );
                    return (
                      <li key={indice} className="flex flex-wrap items-center gap-3 py-3">
                        <Entrada
                          type="time"
                          aria-label={`${rotulo}: desde`}
                          value={t.desde}
                          onChange={(e) => cambiar(indice, "desde", e.target.value)}
                          className="w-32"
                        />
                        <span className="text-menor text-tinta-suave">a</span>
                        <Entrada
                          type="time"
                          aria-label={`${rotulo}: hasta`}
                          value={t.hasta}
                          onChange={(e) => cambiar(indice, "hasta", e.target.value)}
                          className="w-32"
                        />
                        <span className="text-micro text-tinta-suave">
                          {caben === 0
                            ? "no cabe ninguna consulta"
                            : caben === 1
                              ? "1 consulta"
                              : `${caben} consultas`}
                        </span>
                        <Boton
                          tono="discreto"
                          medida="icono"
                          aria-label={`Quitar tramo de ${rotulo}`}
                          className="ml-auto"
                          onClick={() => quitar(indice)}
                        >
                          <Trash2 className="size-3.5" />
                        </Boton>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </section>

      <Regla />

      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <Titulo>Cómo se trocea</Titulo>
          <Apoyo>
            Cada consulta dura lo que digas aquí, y entre una y otra queda el respiro que elijas.
          </Apoyo>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="ho-duracion" etiqueta="Dura cada consulta" sufijo="min">
            <Entrada
              id="ho-duracion"
              type="number"
              min={TOPES.duracionConsultaMin[0]}
              max={TOPES.duracionConsultaMin[1]}
              step="5"
              value={numeros.duracionConsultaMin}
              onChange={(e) => numero("duracionConsultaMin", e.target.value)}
              className="rounded-r-none"
            />
          </Campo>
          <Campo id="ho-margen" etiqueta="Respiro entre consultas" sufijo="min">
            <Entrada
              id="ho-margen"
              type="number"
              min={TOPES.margenConsultaMin[0]}
              max={TOPES.margenConsultaMin[1]}
              step="5"
              value={numeros.margenConsultaMin}
              onChange={(e) => numero("margenConsultaMin", e.target.value)}
              className="rounded-r-none"
            />
          </Campo>
          <Campo
            id="ho-antelacion"
            etiqueta="Con cuánta antelación"
            sufijo="h"
            ayuda="Nadie puede reservarte con menos aviso que esto."
          >
            <Entrada
              id="ho-antelacion"
              type="number"
              min={TOPES.antelacionHoras[0]}
              max={TOPES.antelacionHoras[1]}
              value={numeros.antelacionHoras}
              onChange={(e) => numero("antelacionHoras", e.target.value)}
              className="rounded-r-none"
            />
          </Campo>
          <Campo
            id="ho-horizonte"
            etiqueta="Hasta cuándo se ve"
            sufijo="semanas"
            ayuda="Más allá de esto no aparece nada libre."
          >
            <Entrada
              id="ho-horizonte"
              type="number"
              min={TOPES.horizonteSemanas[0]}
              max={TOPES.horizonteSemanas[1]}
              value={numeros.horizonteSemanas}
              onChange={(e) => numero("horizonteSemanas", e.target.value)}
              className="rounded-r-none"
            />
          </Campo>
        </div>

        <Etiqueta>
          {porSemana === 0
            ? "Con este horario no ofreces ninguna consulta"
            : `Ofreces ${porSemana} consultas por semana`}
        </Etiqueta>
      </section>

      {problema ? <Aviso tono="atencion">{problema}</Aviso> : null}
      {fallo ? <Aviso tono="error">{fallo}</Aviso> : null}
      {guardado ? <Aviso tono="exito">Horario guardado.</Aviso> : null}

      <div>
        <Boton
          medida="grande"
          disabled={ocupado || problema !== null}
          onClick={() => void guardar()}
        >
          Guardar horario
        </Boton>
      </div>
    </div>
  );
}
