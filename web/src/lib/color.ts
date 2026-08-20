/** Del color que elige la coach a los tokens que usa la interfaz.
 *
 *  Ella escoge uno y aquí salen los tres que hacen falta: el de marcar, el que puede llevar
 *  texto y el del fondo teñido. Y salen distintos en claro y en oscuro, porque un color no
 *  se comporta igual sobre blanco que sobre negro: el verde `#0E3B2B` de LeanMuscle da
 *  12.5:1 sobre blanco y 1.56:1 sobre negro, donde ya no se ve.
 *
 *  Los umbrales son los de WCAG: 4.5:1 para texto y 3:1 para bordes, iconos y controles.
 *  Se ajusta la luminosidad y se deja el tono en paz — su color sigue siendo el suyo, solo
 *  más claro o más oscuro de lo que se necesite para verlo.
 */

/* -------------------------------------------------------------- Conversión --- */

interface Rgb {
  r: number;
  g: number;
  b: number;
}

interface Hsl {
  h: number;
  s: number;
  l: number;
}

/** Acepta `#rgb` y `#rrggbb`. Lo que no entienda vuelve como negro, que es visible sobre
 *  cualquier fondo claro y nunca deja la interfaz sin color. */
export function aRgb(hex: string): Rgb {
  const limpio = hex.trim().replace("#", "");
  const largo =
    limpio.length === 3
      ? limpio
          .split("")
          .map((c) => c + c)
          .join("")
      : limpio;
  if (!/^[0-9a-fA-F]{6}$/.test(largo)) return { r: 0, g: 0, b: 0 };
  return {
    r: parseInt(largo.slice(0, 2), 16),
    g: parseInt(largo.slice(2, 4), 16),
    b: parseInt(largo.slice(4, 6), 16),
  };
}

function aHex({ r, g, b }: Rgb): string {
  const dos = (n: number) =>
    Math.round(Math.min(255, Math.max(0, n)))
      .toString(16)
      .padStart(2, "0");
  return `#${dos(r)}${dos(g)}${dos(b)}`;
}

function aHsl({ r, g, b }: Rgb): Hsl {
  const rn = r / 255;
  const gn = g / 255;
  const bn = b / 255;
  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const l = (max + min) / 2;
  if (max === min) return { h: 0, s: 0, l };

  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h: number;
  if (max === rn) h = ((gn - bn) / d + (gn < bn ? 6 : 0)) / 6;
  else if (max === gn) h = ((bn - rn) / d + 2) / 6;
  else h = ((rn - gn) / d + 4) / 6;
  return { h, s, l };
}

function deHsl({ h, s, l }: Hsl): Rgb {
  if (s === 0) {
    const v = l * 255;
    return { r: v, g: v, b: v };
  }
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const canal = (t: number) => {
    let x = t;
    if (x < 0) x += 1;
    if (x > 1) x -= 1;
    if (x < 1 / 6) return p + (q - p) * 6 * x;
    if (x < 1 / 2) return q;
    if (x < 2 / 3) return p + (q - p) * (2 / 3 - x) * 6;
    return p;
  };
  return { r: canal(h + 1 / 3) * 255, g: canal(h) * 255, b: canal(h - 1 / 3) * 255 };
}

/* --------------------------------------------------------------- Contraste --- */

function luminancia({ r, g, b }: Rgb): number {
  const lineal = (c: number) => {
    const n = c / 255;
    return n <= 0.03928 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lineal(r) + 0.7152 * lineal(g) + 0.0722 * lineal(b);
}

/** Razón de contraste WCAG. Va de 1 (idénticos) a 21 (negro contra blanco). */
export function contraste(a: string, b: string): number {
  const la = luminancia(aRgb(a));
  const lb = luminancia(aRgb(b));
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

/* ---------------------------------------------------------------- Ajustes --- */

/** Mueve la luminosidad hasta alcanzar el contraste pedido, conservando tono y saturación.
 *
 *  Se aleja del fondo: sobre uno oscuro aclara, sobre uno claro oscurece. Si ni el blanco
 *  ni el negro puros llegan al objetivo —no pasa con los fondos reales— devuelve lo más
 *  cerca que se pudo, que siempre es mejor que el color de partida.
 */
export function legibleSobre(color: string, fondo: string, objetivo: number): string {
  if (contraste(color, fondo) >= objetivo) return color;

  const hsl = aHsl(aRgb(color));
  const aclarar = luminancia(aRgb(fondo)) < 0.5;
  let mejor = color;
  let mejorContraste = contraste(color, fondo);

  // Pasos de 1 % de luminosidad: cien intentos cubren toda la escala y el bucle termina
  // siempre, que es lo que no garantiza una búsqueda por bisección con umbrales imposibles.
  for (let paso = 1; paso <= 100; paso += 1) {
    const l = aclarar ? hsl.l + paso / 100 : hsl.l - paso / 100;
    if (l < 0 || l > 1) break;
    const candidato = aHex(deHsl({ ...hsl, l }));
    const razon = contraste(candidato, fondo);
    if (razon > mejorContraste) {
      mejor = candidato;
      mejorContraste = razon;
    }
    if (razon >= objetivo) return candidato;
  }
  return mejor;
}

/** El color diluido sobre el fondo. `proporcion` es cuánto color queda: 0.08 es un tinte. */
export function mezclar(color: string, fondo: string, proporcion: number): string {
  const c = aRgb(color);
  const f = aRgb(fondo);
  const p = Math.min(1, Math.max(0, proporcion));
  return aHex({
    r: c.r * p + f.r * (1 - p),
    g: c.g * p + f.g * (1 - p),
    b: c.b * p + f.b * (1 - p),
  });
}

/* ----------------------------------------------------------------- Paleta --- */

/** Mínimo de WCAG para texto. */
export const CONTRASTE_TEXTO = 4.5;

/** Mínimo de WCAG para bordes, iconos y controles: no se leen letra a letra. */
export const CONTRASTE_MARCA = 3;

export interface Paleta {
  /** Filetes, bordes, iconos, estados activos. */
  base: string;
  /** La versión que sí puede llevar palabras. */
  texto: string;
  /** Fondo teñido, para bloques enteros. */
  sutil: string;
  /** El color tal como lo eligió ella, sin ajustar. Para el selector. */
  elegido: string;
}

/** Los tres tonos que hacen falta, ya legibles sobre el fondo del tema.
 *
 *  El sutil se mezcla y no se aclara: un fondo teñido tiene que quedarse cerca del papel,
 *  y aclarar un color saturado da un pastel que compite con el texto que lleva encima.
 */
export function paletaDe(elegido: string, fondo: string): Paleta {
  return {
    elegido,
    base: legibleSobre(elegido, fondo, CONTRASTE_MARCA),
    texto: legibleSobre(elegido, fondo, CONTRASTE_TEXTO),
    sutil: mezclar(elegido, fondo, 0.1),
  };
}
