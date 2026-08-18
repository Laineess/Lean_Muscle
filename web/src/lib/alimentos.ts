/** Escalado de alimentos: kcal y macros a partir de la porción del catálogo. */

import { type AlimentoApi, type AlimentoCatalogoApi } from "@/lib/api";
import { num } from "@/lib/formato";

/** Valores del catálogo referidos a `porcion` unidades. Lo que permite reescalar. */
export interface BaseDeAlimento {
  porcion: number;
  kcal: number;
  p: number;
  c: number;
  g: number;
}

export interface AlimentoEnPlan extends AlimentoApi {
  cantidad: number;
  unidad: string;
  base: BaseDeAlimento;
}

const decimal = (n: number) => Math.round(n * 10) / 10;

export const baseDeCatalogo = (a: AlimentoCatalogoApi): BaseDeAlimento => ({
  porcion: a.porcion,
  kcal: a.kcal,
  p: a.proteina,
  c: a.carbo,
  g: a.grasa,
});

/** Único punto donde se hace la regla de tres. */
export function escalar(
  nombre: string,
  base: BaseDeAlimento,
  cantidad: number,
  unidad: string,
): AlimentoEnPlan {
  const factor = base.porcion > 0 ? cantidad / base.porcion : 0;
  return {
    nombre,
    porcion: `${num(cantidad, Number.isInteger(cantidad) ? 0 : 1)} ${unidad}`,
    kcal: Math.round(base.kcal * factor),
    p: decimal(base.p * factor),
    c: decimal(base.c * factor),
    g: decimal(base.g * factor),
    cantidad,
    unidad,
    base,
  };
}

/** Los planes viejos guardaban solo el resultado; se toma esa porción como referencia para
 *  que la cantidad vuelva a ser editable sin buscar el alimento otra vez. */
export function normalizarAlimento(a: AlimentoApi): AlimentoEnPlan {
  if (a.cantidad !== undefined && a.unidad !== undefined && a.base !== undefined) {
    return { ...a, cantidad: a.cantidad, unidad: a.unidad, base: a.base };
  }
  const cantidad = Number.parseFloat(a.porcion) || 1;
  const unidad = a.porcion.replace(/^[\d.,\s]+/, "").trim() || "porción";
  return {
    ...a,
    cantidad,
    unidad,
    base: { porcion: cantidad, kcal: a.kcal, p: a.p, c: a.c, g: a.g },
  };
}

export interface EjercicioEnPlan {
  nombre: string;
  series: number;
  reps: string;
  carga: string;
  nota: string;
}
