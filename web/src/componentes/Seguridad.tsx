/** Cambio de contraseña, compartido por los dos frentes.
 *
 *  Cambiar la contraseña **cierra todas las sesiones**, incluida la actual. Si alguien más
 *  había entrado, dejar su cookie viva haría inútil el cambio. Por eso al terminar se
 *  devuelve al acceso: no es un fallo, es la mitad del valor de este flujo.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Apoyo, Aviso, Boton, Campo, Entrada, Etiqueta, Titulo } from "@/componentes/primitivas";
import { ErrorApi, api } from "@/lib/api";
import { cerrarSesion } from "@/lib/sesion";

const LONGITUD_MINIMA = 8;

/** Cualquier cosa que no sea letra, número ni espacio. Se define por exclusión, igual que
 *  el servidor: una lista cerrada de símbolos empuja a que todos terminen en el mismo. */
const ESPECIAL = /[^A-Za-z0-9\s]/;

export function CambiarContrasena() {
  const navegar = useNavigate();
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [repetida, setRepetida] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  // Las mismas reglas que aplica el servidor. Se comprueban aquí para avisar mientras
  // escribe, no para autorizar: quien decide es `validar_contrasena`.
  const problema = !actual
    ? "Escribe tu contraseña actual."
    : nueva.length < LONGITUD_MINIMA
      ? `La nueva necesita al menos ${LONGITUD_MINIMA} caracteres.`
      : !/\d/.test(nueva)
        ? "Necesita al menos un número."
        : !ESPECIAL.test(nueva)
          ? "Necesita al menos un carácter especial, por ejemplo ! ? # o $."
          : nueva !== repetida
            ? "Las dos nuevas no coinciden."
            : nueva === actual
              ? "La nueva tiene que ser distinta de la actual."
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
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo cambiar.");
      setEnviando(false);
    }
  }

  return (
    <section className="flex max-w-md flex-col gap-5">
      <div className="flex flex-col gap-1">
        <Etiqueta>Seguridad</Etiqueta>
        <Titulo>Cambiar mi contraseña</Titulo>
      </div>

      <Campo id="c-actual" etiqueta="Contraseña actual">
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
        etiqueta="Nueva contraseña"
        ayuda={`Al menos ${LONGITUD_MINIMA} caracteres, con letras y números.`}
      >
        <Entrada
          id="c-nueva"
          type="password"
          autoComplete="new-password"
          value={nueva}
          onChange={(e) => setNueva(e.target.value)}
        />
      </Campo>

      <Campo id="c-repetida" etiqueta="Repítela">
        <Entrada
          id="c-repetida"
          type="password"
          autoComplete="new-password"
          value={repetida}
          onChange={(e) => setRepetida(e.target.value)}
        />
      </Campo>

      {error ? <Aviso tono="error">{error}</Aviso> : null}

      <Aviso tono="info" titulo="Se cerrarán todas tus sesiones">
        También la de este dispositivo. Es a propósito: si alguien más había entrado, cambiar
        la contraseña sin cerrar su sesión no lo sacaría. Tendrás que volver a entrar.
      </Aviso>

      <div>
        <Boton disabled={enviando || problema !== null} onClick={() => void guardar()}>
          {enviando ? "Cambiando…" : "Cambiar contraseña"}
        </Boton>
      </div>

      <Apoyo>Te llegará un correo avisando del cambio, por si no fuiste tú.</Apoyo>
    </section>
  );
}

export function BotonSalir({ className }: { className?: string }) {
  const navegar = useNavigate();
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
      Cerrar sesión
    </Boton>
  );
}
