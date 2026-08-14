/** Formato de fechas y números.
 *
 *  Todo se guarda en UTC y se convierte al presentar. La regla de «mismo día calendario»
 *  del chequeo se evalúa en la zona horaria de la alumna, no en la del servidor ni en la
 *  de su coach: una alumna en Tijuana no debe perder su chequeo por la medianoche de Mérida.
 */

const LOCALE = "es-MX";

export function fecha(iso: string, opciones?: Intl.DateTimeFormatOptions): string {
  const d = new Date(iso.length === 10 ? `${iso}T12:00:00` : iso);
  return d.toLocaleDateString(LOCALE, opciones ?? { day: "numeric", month: "long", year: "numeric" });
}

export function fechaCorta(iso: string): string {
  return fecha(iso, { day: "numeric", month: "short" });
}

export function diaSemana(iso: string): string {
  return fecha(iso, { weekday: "long", day: "numeric", month: "long" });
}

export function num(valor: number | null | undefined, decimales = 1): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "—";
  return valor.toLocaleString(LOCALE, {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  });
}

export function pesos(valor: number): string {
  return valor.toLocaleString(LOCALE, { style: "currency", currency: "MXN" });
}

export function porcentaje(fraccion: number, decimales = 1): string {
  return `${num(fraccion * 100, decimales)} %`;
}

export function iniciales(nombre: string): string {
  return nombre
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p.charAt(0).toUpperCase())
    .join("");
}

export type Direccion = "baja" | "sube" | "igual";

export interface Delta {
  texto: string;
  direccion: Direccion;
  valor: number;
}

/** Diferencia con signo tipográfico correcto (− U+2212, no guion). */
export function delta(actual: number, previo: number | null | undefined, unidad = ""): Delta | null {
  if (previo === null || previo === undefined) return null;
  const d = actual - previo;
  const signo = d > 0 ? "+" : d < 0 ? "−" : "±";
  const sufijo = unidad ? ` ${unidad}` : "";
  return {
    texto: `${signo}${num(Math.abs(d))}${sufijo}`,
    direccion: d < 0 ? "baja" : d > 0 ? "sube" : "igual",
    valor: d,
  };
}

export function edadEn(nacimientoIso: string, referenciaIso: string): number {
  const n = new Date(`${nacimientoIso}T12:00:00`);
  const r = new Date(`${referenciaIso}T12:00:00`);
  const cumplio =
    r.getMonth() > n.getMonth() || (r.getMonth() === n.getMonth() && r.getDate() >= n.getDate());
  return r.getFullYear() - n.getFullYear() - (cumplio ? 0 : 1);
}
