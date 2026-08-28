/** Cambio de contraseña, compartido por los dos frentes.
 *
 *  Cambiar la contraseña **cierra todas las sesiones**, incluida la actual. Si alguien más
 *  había entrado, dejar su cookie viva haría inútil el cambio. Por eso al terminar se
 *  devuelve al acceso: no es un fallo, es la mitad del valor de este flujo.
 */

import { KeyRound } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Apoyo, Aviso, Boton, Campo, Entrada, Etiqueta, Titulo } from "@/componentes/primitivas";
import { ErrorApi, api } from "@/lib/api";
import { useIdioma } from "@/lib/idioma";
import { cerrarSesion } from "@/lib/sesion";

const LONGITUD_MINIMA = 8;

/** Cualquier cosa que no sea letra, número ni espacio. Se define por exclusión, igual que
 *  el servidor: una lista cerrada de símbolos empuja a que todos terminen en el mismo. */
const ESPECIAL = /[^A-Za-z0-9\s]/;

export function CambiarContrasena() {
  const navegar = useNavigate();
  const { t } = useIdioma();
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [repetida, setRepetida] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  // Las mismas reglas que aplica el servidor. Se comprueban aquí para avisar mientras
  // escribe, no para autorizar: quien decide es `validar_contrasena`.
  const problema = !actual
    ? t("Escribe tu contraseña actual.")
    : nueva.length < LONGITUD_MINIMA
      ? t("La nueva necesita al menos {n} caracteres.", { n: LONGITUD_MINIMA })
      : !/\d/.test(nueva)
        ? t("Necesita al menos un número.")
        : !ESPECIAL.test(nueva)
          ? t("Necesita al menos un carácter especial, por ejemplo ! ? # o $.")
          : nueva !== repetida
            ? t("Las dos nuevas no coinciden.")
            : nueva === actual
              ? t("La nueva tiene que ser distinta de la actual.")
              : null;

  async function guardar() {
    if (problema) {
      setError(problema);
      return;
    }
    setError(null);
    setEnviando(true);
    try {
      await api.acceso.cambiarContrasena(actual, nueva);
      cerrarSesion();
      void navegar("/acceso", { replace: true });
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : t("No se pudo cambiar."));
      setEnviando(false);
    }
  }

  return (
    <section className="flex max-w-md flex-col gap-5">
      <div className="flex flex-col gap-1">
        <Etiqueta>{t("Seguridad")}</Etiqueta>
        <Titulo icono={KeyRound}>{t("Cambiar mi contraseña")}</Titulo>
      </div>

      <Campo id="c-actual" etiqueta={t("Contraseña actual")}>
        <Entrada
          id="c-actual"
          type="password"
          autoComplete="current-password"
          value={actual}
          onChange={(e) => setActual(e.target.value)}
        />
      </Campo>

      <Campo
        id="c-nueva"
        etiqueta={t("Nueva contraseña")}
        ayuda={t("Al menos {n} caracteres, debe incluir números y 1 caracter especial.", {
          n: LONGITUD_MINIMA,
        })}
      >
        <Entrada
          id="c-nueva"
          type="password"
          autoComplete="new-password"
          value={nueva}
          onChange={(e) => setNueva(e.target.value)}
        />
      </Campo>

      <Campo id="c-repetida" etiqueta={t("Repítela")}>
        <Entrada
          id="c-repetida"
          type="password"
          autoComplete="new-password"
          value={repetida}
          onChange={(e) => setRepetida(e.target.value)}
        />
      </Campo>

      {error ? <Aviso tono="error">{error}</Aviso> : null}

      <Aviso tono="info" titulo={t("Se cerrarán todas tus sesiones")}>
        {t(
          "También la de este dispositivo. Es a propósito: si alguien más había entrado, cambiar la contraseña sin cerrar su sesión no lo sacaría. Tendrás que volver a entrar.",
        )}
      </Aviso>

      <div>
        <Boton disabled={enviando || problema !== null} onClick={() => void guardar()}>
          {enviando ? t("Cambiando…") : t("Cambiar contraseña")}
        </Boton>
      </div>

      <Apoyo>{t("Te llegará un correo avisando del cambio, por si no fuiste tú.")}</Apoyo>
    </section>
  );
}

export function BotonSalir({ className }: { className?: string }) {
  const navegar = useNavigate();
  const { t } = useIdioma();
  return (
    <Boton
      tono="contorno"
      className={className}
      onClick={() => {
        // Se revoca en el servidor y se limpia el navegador. Borrar solo la cookie dejaría
        // el token vivo para quien lo hubiera copiado.
        void api.acceso.salir().catch(() => undefined);
        cerrarSesion();
        void navegar("/acceso", { replace: true });
      }}
    >
      {t("Cerrar sesión")}
    </Boton>
  );
}
