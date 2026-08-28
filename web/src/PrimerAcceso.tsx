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

import { BotonSalir } from "@/componentes/Seguridad";
import { CambiarContrasena } from "@/componentes/Seguridad";
import { Apoyo, Aviso, Etiqueta, Portada } from "@/componentes/primitivas";
import { useIdioma } from "@/lib/idioma";
import { actorGuardado } from "@/lib/sesion";

export function PrimerAcceso() {
  const actor = actorGuardado();
  const { t } = useIdioma();
  if (!actor) return <Navigate to="/acceso" replace />;
  // Quien ya la cambió no tiene nada que hacer aquí.
  if (!actor.debeCambiarContrasena) return <Navigate to="/" replace />;

  return (
    <div className="mx-auto flex min-h-full max-w-lg flex-col justify-center gap-8 px-6 py-12">
      <header className="flex flex-col gap-3">
        <Etiqueta>{actor.marca}</Etiqueta>
        <Portada>{t("Ponle tu contraseña")}</Portada>
        <Apoyo>
          {t(
            "Entraste con la que te dieron de alta, y esa la conoce alguien más. Cámbiala ahora y lo demás se abre.",
          )}
        </Apoyo>
      </header>

      <Aviso tono="atencion" titulo={t("Es la única pantalla disponible hasta que la cambies")}>
        {t(
          "No es una recomendación: mientras no lo hagas, el servidor no abre tu expediente ni tu plan.",
        )}
      </Aviso>

      <CambiarContrasena />

      {/* Sin esto, quien entra en la cuenta equivocada se queda encerrado: es la única
          pantalla que abre el servidor, y no había forma de volver al acceso. */}
      <div className="flex justify-center border-t border-linea pt-6">
        <BotonSalir />
      </div>
    </div>
  );
}
