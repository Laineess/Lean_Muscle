/** Primer acceso: poner una contraseña propia antes de cualquier otra cosa.
 *
 *  Toda cuenta nace con la misma contraseña, que la coach dicta. Eso alcanza para entrar una
 *  vez y nada más: mientras no se cambie, el servidor cierra el resto de la aplicación y
 *  esta pantalla es lo único que se puede abrir.
 *
 *  La guarda de verdad vive en el servidor (`app/rutas/sesion.py`). Esta pantalla no
 *  protege nada: solo explica por qué no se puede seguir.
 */

import { Navigate } from "react-router-dom";

import { CambiarContrasena } from "@/componentes/Seguridad";
import { Apoyo, Aviso, Etiqueta, Portada } from "@/componentes/primitivas";
import { actorGuardado } from "@/lib/sesion";

export function PrimerAcceso() {
  const actor = actorGuardado();
  if (!actor) return <Navigate to="/acceso" replace />;
  // Quien ya la cambió no tiene nada que hacer aquí.
  if (!actor.debeCambiarContrasena) return <Navigate to="/" replace />;

  return (
    <div className="mx-auto flex min-h-full max-w-lg flex-col justify-center gap-8 px-6 py-12">
      <header className="flex flex-col gap-3">
        <Etiqueta>{actor.marca}</Etiqueta>
        <Portada>Ponle tu contraseña</Portada>
        <Apoyo>
          Entraste con la que te dieron de alta, y esa la conoce alguien más. Cámbiala ahora
          y lo demás se abre.
        </Apoyo>
      </header>

      <Aviso tono="atencion" titulo="Es la única pantalla disponible hasta que la cambies">
        No es una recomendación: mientras no lo hagas, el servidor no abre tu expediente ni
        tu plan.
      </Aviso>

      <CambiarContrasena />
    </div>
  );
}
