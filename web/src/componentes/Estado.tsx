/** Estados de carga y de servidor caído, iguales en todas las pantallas.
 *
 *  Cuando la pantalla pinta datos de ejemplo **tiene que decirlo**. Enseñar números
 *  inventados en silencio es peor que no enseñar nada: la coach toma decisiones sobre ellos.
 */

import { Aviso, Vacio } from "@/componentes/primitivas";

export function Cargando({ que = "esto" }: { que?: string }) {
  return (
    <div role="status" aria-live="polite">
      <Vacio>Cargando {que}…</Vacio>
    </div>
  );
}

export function AvisoSinServidor({ mensaje }: { mensaje: string | null }) {
  return (
    <Aviso tono="atencion" titulo="Sin conexión con el servidor">
      {mensaje ?? "No se pudo contactar la API."} Estás viendo datos de ejemplo.
    </Aviso>
  );
}
