/** Renderiza el Markdown de los documentos legales.
 *
 *  Escrito a mano y no con una librería porque el subconjunto es conocido y nuestro: los
 *  documentos viven en `docs/` y usan encabezados, negritas, enlaces, listas, citas, tablas
 *  y filetes. Nada más. Una dependencia de 40 KB para eso no se paga sola.
 *
 *  El texto viene de nuestro repositorio, no de una usuaria, así que no hay HTML que
 *  sanear: lo que no se reconoce sale como texto plano, nunca interpretado.
 */

import { type ReactNode } from "react";

/** Negritas, cursivas, código y enlaces dentro de una línea. */
function enLinea(texto: string, llave: string): ReactNode[] {
  const trozos: ReactNode[] = [];
  // Un solo recorrido con alternativas: anidar reemplazos produce marcas a medio cerrar.
  const patron = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let ultimo = 0;
  let n = 0;

  for (const coincidencia of texto.matchAll(patron)) {
    const i = coincidencia.index;
    if (i > ultimo) trozos.push(texto.slice(ultimo, i));
    const t = coincidencia[0];
    const k = `${llave}-${n++}`;

    if (t.startsWith("**")) {
      trozos.push(
        <strong key={k} className="font-semibold">
          {t.slice(2, -2)}
        </strong>,
      );
    } else if (t.startsWith("`")) {
      trozos.push(
        <code key={k} className="rounded bg-fondo-sutil px-1 py-0.5 text-micro">
          {t.slice(1, -1)}
        </code>,
      );
    } else if (t.startsWith("[")) {
      const corte = t.indexOf("](");
      const rotulo = t.slice(1, corte);
      const destino = t.slice(corte + 2, -1);
      trozos.push(
        <a key={k} href={destino} className="underline underline-offset-2">
          {rotulo}
        </a>,
      );
    } else {
      trozos.push(<em key={k}>{t.slice(1, -1)}</em>);
    }
    ultimo = i + t.length;
  }

  if (ultimo < texto.length) trozos.push(texto.slice(ultimo));
  return trozos;
}

function celdas(fila: string): string[] {
  return fila
    .replace(/^\||\|$/g, "")
    .split("|")
    .map((c) => c.trim());
}

const ENCABEZADOS: Record<number, string> = {
  1: "text-portada font-semibold tracking-[-0.02em] mt-10 mb-2",
  2: "text-titulo font-semibold mt-8 mb-2",
  3: "text-guia font-semibold mt-6 mb-1",
  4: "text-cuerpo font-semibold mt-4 mb-1",
};

export function Markdown({ texto }: { texto: string }) {
  const lineas = texto.split("\n");
  const bloques: ReactNode[] = [];
  let i = 0;

  const parrafo: string[] = [];
  const cerrarParrafo = () => {
    if (!parrafo.length) return;
    const contenido = parrafo.join(" ");
    bloques.push(
      <p key={`p${bloques.length}`} className="mb-3 text-menor leading-relaxed">
        {enLinea(contenido, `p${bloques.length}`)}
      </p>,
    );
    parrafo.length = 0;
  };

  while (i < lineas.length) {
    const linea = lineas[i] ?? "";
    const limpia = linea.trim();

    if (!limpia) {
      cerrarParrafo();
      i += 1;
      continue;
    }

    // --- Filete ---
    if (/^-{3,}$/.test(limpia)) {
      cerrarParrafo();
      bloques.push(<hr key={`h${bloques.length}`} className="my-8 border-linea" />);
      i += 1;
      continue;
    }

    // --- Encabezado ---
    const encabezado = /^(#{1,4})\s+(.*)$/.exec(limpia);
    if (encabezado) {
      cerrarParrafo();
      const nivel = encabezado[1]!.length;
      const Etiqueta = `h${nivel}` as "h1";
      bloques.push(
        <Etiqueta key={`t${bloques.length}`} className={ENCABEZADOS[nivel]}>
          {enLinea(encabezado[2]!, `t${bloques.length}`)}
        </Etiqueta>,
      );
      i += 1;
      continue;
    }

    // --- Tabla: encabezado, separador y filas ---
    if (limpia.startsWith("|") && (lineas[i + 1] ?? "").trim().startsWith("|-")) {
      cerrarParrafo();
      const cabecera = celdas(limpia);
      const filas: string[][] = [];
      i += 2;
      while (i < lineas.length && (lineas[i] ?? "").trim().startsWith("|")) {
        filas.push(celdas((lineas[i] ?? "").trim()));
        i += 1;
      }
      bloques.push(
        // La tabla se desplaza dentro de su caja: en un teléfono, una de cuatro columnas
        // rompería el ancho de toda la página.
        <div key={`tb${bloques.length}`} className="mb-4 overflow-x-auto">
          <table className="w-full min-w-[32rem] border-collapse text-micro">
            <thead>
              <tr>
                {cabecera.map((c, j) => (
                  <th
                    key={j}
                    className="border-b border-linea-fuerte py-2 pr-3 text-left font-semibold"
                  >
                    {enLinea(c, `th${j}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filas.map((f, j) => (
                <tr key={j}>
                  {f.map((c, k) => (
                    <td key={k} className="border-b border-linea py-2 pr-3 align-top leading-relaxed">
                      {enLinea(c, `td${j}-${k}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    // --- Cita ---
    if (limpia.startsWith(">")) {
      cerrarParrafo();
      const dentro: string[] = [];
      while (i < lineas.length && (lineas[i] ?? "").trim().startsWith(">")) {
        dentro.push((lineas[i] ?? "").trim().replace(/^>\s?/, ""));
        i += 1;
      }
      bloques.push(
        <blockquote
          key={`c${bloques.length}`}
          className="mb-4 border-l-2 border-l-acento pl-4 text-menor leading-relaxed text-tinta-media"
        >
          {enLinea(dentro.join(" "), `c${bloques.length}`)}
        </blockquote>,
      );
      continue;
    }

    // --- Listas ---
    const vinieta = /^[-*]\s+(.*)$/.exec(limpia);
    const numerada = /^\d+\.\s+(.*)$/.exec(limpia);
    if (vinieta || numerada) {
      cerrarParrafo();
      const ordenada = numerada !== null;
      const puntos: string[] = [];
      while (i < lineas.length) {
        const actual = (lineas[i] ?? "").trim();
        const m = ordenada ? /^\d+\.\s+(.*)$/.exec(actual) : /^[-*]\s+(.*)$/.exec(actual);
        if (!m) break;
        puntos.push(m[1]!);
        i += 1;
      }
      const Lista = ordenada ? "ol" : "ul";
      bloques.push(
        <Lista
          key={`l${bloques.length}`}
          className={`mb-4 ml-5 flex list-outside flex-col gap-1.5 text-menor leading-relaxed ${
            ordenada ? "list-decimal" : "list-disc"
          }`}
        >
          {puntos.map((punto, j) => (
            <li key={j}>{enLinea(punto, `li${bloques.length}-${j}`)}</li>
          ))}
        </Lista>,
      );
      continue;
    }

    parrafo.push(limpia);
    i += 1;
  }

  cerrarParrafo();
  return <div className="medida">{bloques}</div>;
}
