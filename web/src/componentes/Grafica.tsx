/** Gráfica de líneas en SVG, sin librería.
 *
 *  Una sola serie por gráfica: comparar peso contra cintura en el mismo eje obliga a dos
 *  escalas y a leer una leyenda. Es más honesto poner dos gráficas pequeñas una junto a otra.
 *
 *  La serie va en tinta, no en acento: el dorado marca, no dibuja datos.
 */

import { useId } from "react";

import { num } from "@/lib/formato";

export interface PuntoSerie {
  etiqueta: string;
  valor: number;
}

export function Grafica({
  puntos,
  unidad,
  decimales = 1,
  alto = 180,
}: {
  puntos: PuntoSerie[];
  unidad?: string;
  decimales?: number;
  alto?: number;
}) {
  const idGradiente = useId();
  if (puntos.length < 2) {
    return <p className="text-menor text-tinta-suave">Hacen falta al menos dos chequeos.</p>;
  }

  const W = 640;
  const H = alto;
  const ML = 44;
  const MR = 8;
  const MT = 12;
  const MB = 26;
  const ancho = W - ML - MR;
  const altoUtil = H - MT - MB;

  const valores = puntos.map((p) => p.valor);
  const crudoMin = Math.min(...valores);
  const crudoMax = Math.max(...valores);
  const margen = (crudoMax - crudoMin) * 0.2 || 1;
  const min = crudoMin - margen;
  const max = crudoMax + margen;

  const x = (i: number) => ML + (i * ancho) / (puntos.length - 1);
  const y = (v: number) => MT + altoUtil - ((v - min) / (max - min)) * altoUtil;

  const linea = puntos.map((p, i) => `${i ? "L" : "M"}${x(i)} ${y(p.valor)}`).join(" ");
  const area = `${linea} L${x(puntos.length - 1)} ${MT + altoUtil} L${ML} ${MT + altoUtil} Z`;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="h-auto w-full"
      role="img"
      aria-label={`Evolución de ${puntos.length} registros, de ${num(puntos[0]!.valor, decimales)} a ${num(puntos.at(-1)!.valor, decimales)} ${unidad ?? ""}`}
    >
      <defs>
        <linearGradient id={idGradiente} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--tinta)" stopOpacity="0.07" />
          <stop offset="100%" stopColor="var(--tinta)" stopOpacity="0" />
        </linearGradient>
      </defs>

      {[0, 1, 2].map((g) => {
        const gy = MT + (g * altoUtil) / 2;
        return (
          <g key={g}>
            <line
              x1={ML}
              y1={gy}
              x2={W - MR}
              y2={gy}
              stroke="var(--linea)"
              strokeWidth="1"
              strokeDasharray="2 5"
            />
            <text
              x={ML - 10}
              y={gy + 3}
              textAnchor="end"
              fontSize="10"
              fill="var(--tinta-suave)"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {num(max - ((max - min) * g) / 2, decimales)}
            </text>
          </g>
        );
      })}

      <path d={area} fill={`url(#${idGradiente})`} />
      <path d={linea} fill="none" stroke="var(--tinta)" strokeWidth="1.75" strokeLinejoin="round" />

      {puntos.map((p, i) => (
        <circle
          key={p.etiqueta}
          cx={x(i)}
          cy={y(p.valor)}
          r={i === puntos.length - 1 ? 4 : 3}
          fill={i === puntos.length - 1 ? "var(--acento)" : "var(--fondo)"}
          stroke="var(--tinta)"
          strokeWidth="1.75"
        />
      ))}

      {puntos.map((p, i) => (
        <text
          key={p.etiqueta}
          x={x(i)}
          y={H - 6}
          textAnchor="middle"
          fontSize="10"
          fill="var(--tinta-suave)"
        >
          {p.etiqueta}
        </text>
      ))}
    </svg>
  );
}
