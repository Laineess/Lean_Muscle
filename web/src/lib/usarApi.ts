/** Hook de carga para las pantallas.
 *
 *  Sin librería de estado: mientras cada pantalla haga **una sola petición**, un hook de
 *  treinta líneas cubre el caso y se entiende de una lectura.
 *
 *  Cancela la petición al desmontar, para que una respuesta tardía no escriba estado sobre
 *  una pantalla que ya no está, y suelta lo cargado en cuanto cambia de quién se está
 *  hablando: enseñar el expediente de una alumna bajo el nombre de otra es peor que enseñar
 *  un hueco.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { ErrorApi } from "@/lib/api";

export interface Carga<T> {
  datos: T | null;
  cargando: boolean;
  error: ErrorApi | null;
  recargar: () => void;
}

export function usarApi<T>(
  pedir: (senal: AbortSignal) => Promise<T>,
  dependencias: readonly unknown[] = [],
): Carga<T> {
  const [datos, setDatos] = useState<T | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<ErrorApi | null>(null);
  const [intento, setIntento] = useState(0);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  // Al cambiar de alumna hay que soltar lo anterior **antes** de pintar, no en un efecto:
  // un efecto corre después del render, y ese render ya enseñó los datos de la otra. Poner
  // estado durante el render es justo lo que React admite para derivar de las props.
  //
  // `recargar` no entra aquí a propósito: refresca lo mismo, y vaciarlo haría parpadear la
  // pantalla en cada guardado.
  const clave = JSON.stringify(dependencias);
  const claveAnterior = useRef(clave);
  if (claveAnterior.current !== clave) {
    claveAnterior.current = clave;
    setDatos(null);
    setError(null);
    setCargando(true);
  }

  useEffect(() => {
    const control = new AbortController();
    setCargando(true);
    setError(null);

    pedir(control.signal)
      .then((r) => {
        if (!control.signal.aborted) setDatos(r);
      })
      .catch((causa: unknown) => {
        if (control.signal.aborted) return;
        setError(causa instanceof ErrorApi ? causa : new ErrorApi(0, null, "Algo salió mal."));
      })
      .finally(() => {
        if (!control.signal.aborted) setCargando(false);
      });

    return () => control.abort();
    // `pedir` se recrea en cada render; las dependencias reales las declara quien llama.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencias, intento]);

  return { datos, cargando, error, recargar };
}

export interface CargaConRespaldo<T> {
  datos: T;
  cargando: boolean;
  /** El servidor no respondió: la pantalla está pintando datos de ejemplo. */
  sinServidor: boolean;
  mensaje: string | null;
  /** El código del error, cuando lo hay: sirve para distinguir un 403 con motivo. */
  codigo: string | null;
  recargar: () => void;
}

/** Igual que `usarApi`, pero nunca devuelve nulo.
 *
 *  Mientras la API se termina de cablear, cada pantalla tiene que poder revisarse sin
 *  levantar MySQL. El respaldo hace eso posible **y la pantalla lo dice**: mostrar datos de
 *  ejemplo en silencio sería peor que no mostrarlos, porque se toman decisiones sobre ellos.
 */
export function usarApiConRespaldo<T>(
  pedir: (senal: AbortSignal) => Promise<T>,
  respaldo: T,
  dependencias: readonly unknown[] = [],
): CargaConRespaldo<T> {
  const { datos, cargando, error, recargar } = usarApi(pedir, dependencias);
  return {
    datos: datos ?? respaldo,
    cargando: cargando && datos === null,
    sinServidor: error !== null,
    mensaje: error?.message ?? null,
    codigo: error?.codigo ?? null,
    recargar,
  };
}
