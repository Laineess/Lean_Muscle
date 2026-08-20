/** Estados de carga y de servidor caído, iguales en todas las pantallas.
 *
 *  Cuando la pantalla pinta datos de ejemplo **tiene que decirlo**. Enseñar números
 *  inventados en silencio es peor que no enseñar nada: la coach toma decisiones sobre ellos.
 *
 *  Un esqueleto tiene que parecerse a lo que va a llegar. Si el hueco no coincide con el
 *  dato, la pantalla pega un salto al terminar de cargar y se siente peor que un texto
 *  quieto. Por eso los esqueletos de aquí copian las medidas de las primitivas.
 *
 *  Lo que se ve y lo que se anuncia van por caminos distintos: el esqueleto es `aria-hidden`
 *  y el aviso hablado viaja en un `role="status"`. Un lector de pantalla no debería tener
 *  que describir cajas grises.
 */

import { CloudOff, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

import { Aviso, Etiqueta, Vacio } from "@/componentes/primitivas";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------ Esqueletos --- */

/** Bloque gris con un brillo que lo recorre. Las medidas se pasan en `className`. */
export function Esqueleto({ className }: { className?: string }) {
  return <div aria-hidden className={cn("esqueleto h-4 w-full", className)} />;
}

/** Varias líneas de texto. La última sale corta, como termina cualquier párrafo. */
export function EsqueletoTexto({ lineas = 3, className }: { lineas?: number; className?: string }) {
  return (
    <div aria-hidden className={cn("flex flex-col gap-2.5", className)}>
      {Array.from({ length: lineas }, (_, i) => (
        <Esqueleto key={i} className={i === lineas - 1 ? "w-2/3" : "w-full"} />
      ))}
    </div>
  );
}

/** El hueco de un `Dato`: rótulo en versalitas y una cifra grande debajo. */
export function EsqueletoDato({ grande }: { grande?: boolean }) {
  return (
    <div aria-hidden className="flex flex-col gap-2">
      <Esqueleto className="h-3 w-20" />
      <Esqueleto className={grande ? "h-12 w-32" : "h-9 w-24"} />
    </div>
  );
}

/** El hueco de una `Tarjeta`, con su mismo borde y su mismo respiro. */
export function EsqueletoTarjeta({ lineas = 2 }: { lineas?: number }) {
  return (
    <div aria-hidden className="rounded-marco border border-linea bg-fondo-elevado p-5 sm:p-6">
      <div className="flex flex-col gap-4">
        <Esqueleto className="h-5 w-40" />
        <EsqueletoTexto lineas={lineas} />
      </div>
    </div>
  );
}

/** El hueco de una lista de filas separadas por línea. */
export function EsqueletoLista({ filas = 4 }: { filas?: number }) {
  return (
    <ul aria-hidden className="flex flex-col divide-y divide-linea border-y border-linea">
      {Array.from({ length: filas }, (_, i) => (
        <li key={i} className="flex items-center justify-between gap-4 py-4">
          <div className="flex min-w-0 flex-1 flex-col gap-2">
            <Esqueleto className="h-4 w-1/3" />
            <Esqueleto className="h-3 w-1/2" />
          </div>
          <Esqueleto className="h-4 w-16 shrink-0" />
        </li>
      ))}
    </ul>
  );
}

/** El hueco de una rejilla de cifras, como la de un panel. Las columnas van en un mapa
 *  y no interpoladas: Tailwind lee las clases del texto, y una armada al vuelo no existe. */
const COLUMNAS: Record<number, string> = {
  2: "sm:grid-cols-2",
  3: "sm:grid-cols-3",
  4: "sm:grid-cols-4",
};

export function EsqueletoCifras({
  cuantas = 3,
  columnas,
}: {
  cuantas?: number;
  /** `| undefined` explícito: con `exactOptionalPropertyTypes` una prop opcional no lo
      acepta a menos que se declare, y aquí se reenvía tal cual desde arriba. */
  columnas?: number | undefined;
}) {
  return (
    <div
      aria-hidden
      className={cn("grid grid-cols-2 gap-x-6 gap-y-10", COLUMNAS[columnas ?? cuantas] ?? "sm:grid-cols-3")}
    >
      {Array.from({ length: cuantas }, (_, i) => (
        <EsqueletoDato key={i} />
      ))}
    </div>
  );
}

/** El hueco de una cabecera de pantalla: rótulo chico y portada grande. */
export function EsqueletoPortada() {
  return (
    <div aria-hidden className="flex flex-col gap-3">
      <Esqueleto className="h-3 w-40" />
      <Esqueleto className="h-9 w-64 max-w-full" />
    </div>
  );
}

/* --------------------------------------------------------------- Espera --- */

/** Rueda de espera. Va dentro de un botón o junto a un texto, nunca sola. */
export function Rueda({ className }: { className?: string }) {
  return <Loader2 aria-hidden className={cn("size-4 shrink-0 animate-gira", className)} />;
}

/* -------------------------------------------------------------- Cargando --- */

export function Cargando({
  que = "esto",
  /** El hueco que se dibuja mientras tanto. Si la pantalla sabe qué forma va a tener
   *  lo que viene, pasarlo aquí evita el salto al llegar los datos. */
  esqueleto,
}: {
  que?: string;
  esqueleto?: ReactNode;
}) {
  return (
    <div role="status" aria-live="polite" className="animate-aparece">
      <span className="sr-only">Cargando {que}…</span>
      {esqueleto ?? (
        <Vacio>
          <span className="inline-flex items-center gap-2">
            <Rueda className="text-acento" />
            Cargando {que}…
          </span>
        </Vacio>
      )}
    </div>
  );
}

/** La pantalla entera mientras carga: la cabecera ya ocupa su sitio, y debajo el hueco de
 *  lo que venga. Es lo que usan casi todas; las de forma rara pasan su propio esqueleto.
 *
 *  El rótulo dice «Cargando» con la rueda al lado en vez de dejar el hueco mudo: una
 *  pantalla de cajas grises sin una palabra parece rota, no ocupada. */
export function CargandoPantalla({
  que,
  cifras,
  columnas,
  filas = 4,
  texto,
  portada = true,
}: {
  que: string;
  /** Cuántas cifras van arriba, si la pantalla abre con una rejilla de datos. */
  cifras?: number;
  columnas?: number;
  /** Filas de lista. En cero, no dibuja lista. */
  filas?: number;
  /** Líneas de párrafo en vez de lista, para un documento o una conversación. */
  texto?: number;
  /** En falso no dibuja cabecera. Va así cuando la pantalla ya pintó su título arriba, o
   *  cuando esto vive dentro de un diálogo: un título falso bajo el de verdad se lee
   *  como que la pantalla se duplicó. */
  portada?: boolean;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn("flex flex-col animate-aparece", portada ? "gap-12" : "gap-6")}
    >
      <span className="sr-only">Cargando {que}…</span>
      {portada ? (
        <div className="flex flex-col gap-3">
          <Etiqueta>
            <span className="inline-flex items-center gap-2">
              <Rueda className="size-3 text-acento" />
              Cargando
            </span>
          </Etiqueta>
          <Esqueleto className="h-9 w-64 max-w-full" />
        </div>
      ) : null}
      {cifras ? <EsqueletoCifras cuantas={cifras} columnas={columnas} /> : null}
      {texto ? <EsqueletoTexto lineas={texto} className="medida" /> : null}
      {filas > 0 ? <EsqueletoLista filas={filas} /> : null}
    </div>
  );
}

/* ------------------------------------------------------------- Sin señal --- */

export function AvisoSinServidor({ mensaje }: { mensaje: string | null }) {
  return (
    <Aviso tono="atencion" titulo="Sin conexión con el servidor" icono={CloudOff}>
      {mensaje ?? "No se pudo contactar la API."} Estás viendo datos de ejemplo.
    </Aviso>
  );
}
