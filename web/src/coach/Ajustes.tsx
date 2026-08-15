/** Ajustes de la cuenta: zona horaria, avisos y seguridad.
 *
 *  Lo que no es ni marca, ni precios, ni contenido para sus alumnas. Cada una de esas vive
 *  en su propia pantalla desde el menú del avatar: una sola página con todo dentro obligaba
 *  a bajar buscando el bloque correcto.
 */

import { Notificaciones } from "@/componentes/Notificaciones";
import { BotonSalir, CambiarContrasena } from "@/componentes/Seguridad";
import {
  Apoyo,
  Aviso,
  Campo,
  Casilla,
  Etiqueta,
  Portada,
  Regla,
  Selector,
  Titulo,
} from "@/componentes/primitivas";
import { coach } from "@/lib/datos";

const AVISOS = [
  ["Recordatorio de chequeo", "Día 1 de cada mes a todas tus alumnas activas"],
  ["Alerta de inactividad", "Cuando una alumna lleva 3 días naturales sin entrar"],
  ["Renovaciones próximas", "Aviso 3 días antes de que termine cada ciclo"],
  ["Purga de fotos", "Aviso a la alumna 15 días antes, con enlace de descarga"],
  ["Recordatorio de consulta", "Un día antes de cada cita agendada"],
] as const;

export function Ajustes() {
  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta>
          Plan {coach.plan} · hasta {coach.limiteAlumnas} alumnas
        </Etiqueta>
        <Portada>Ajustes</Portada>
      </header>

      {/* ---- Zona horaria ---- */}
      <section className="flex max-w-md flex-col gap-4">
        <Titulo>Tu zona horaria</Titulo>
        <Campo
          id="aj-zona"
          etiqueta="Zona"
          ayuda="La de cada alumna se guarda aparte: su día calendario se evalúa con la suya."
        >
          <Selector id="aj-zona" defaultValue="America/Mexico_City">
            <option value="America/Mexico_City">Ciudad de México (GMT−6)</option>
            <option value="America/Tijuana">Tijuana (GMT−8)</option>
            <option value="America/Cancun">Cancún (GMT−5)</option>
          </Selector>
        </Campo>
      </section>

      <Regla />

      {/* ---- Avisos ---- */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <Titulo>Avisos automáticos</Titulo>
          <Apoyo>
            Salen por notificación dentro de la plataforma. El correo se reserva para lo que no
            puede perderse: acceso, dinero y privacidad.
          </Apoyo>
        </div>
        <div className="flex flex-col gap-2">
          {AVISOS.map(([titulo, detalle]) => (
            <Casilla key={titulo} id={`av-${titulo}`} titulo={titulo} defaultChecked>
              {detalle}
            </Casilla>
          ))}
        </div>
      </section>

      <Regla />

      <Notificaciones para="coach" />

      <Regla />

      <CambiarContrasena />

      <Regla />

      <section className="flex flex-col gap-4">
        <Titulo>Sesión</Titulo>
        <Aviso tono="info">
          Cerrar sesión revoca el token en el servidor, no solo en este navegador.
        </Aviso>
        <div>
          <BotonSalir />
        </div>
      </section>
    </div>
  );
}
