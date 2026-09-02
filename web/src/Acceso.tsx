/** Pantalla de acceso.
 *
 *  «Recordar mis datos» guarda el correo, nunca la contraseña: el token vive en una cookie
 *  HttpOnly. La recuperación no es automática; la coach emite la clave desde su panel.
 */

import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Apoyo, Aviso, Boton, Campo, Casilla, Entrada, Etiqueta, Portada } from "@/componentes/primitivas";
import { ErrorApi, api, type ActorPublico } from "@/lib/api";
import { useIdioma } from "@/lib/idioma";
import { cerrarSesion, correoRecordado, guardarActor, recordarCorreo } from "@/lib/sesion";
import { guardarRegistro } from "./Registro";

export function Acceso() {
  const navegar = useNavigate();
  const guardado = correoRecordado();
  const { t } = useIdioma();

  const [correo, setCorreo] = useState(guardado);
  const [clave, setClave] = useState("");
  const [recordar, setRecordar] = useState(Boolean(guardado));
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function abrir(actor: ActorPublico) {
    recordarCorreo(correo, recordar);
    guardarActor(actor);
    if (actor.rol !== "alumna") {
      void navegar(actor.rol === "coach" ? "/coach" : "/plataforma", { replace: true });
      return;
    }

    try {
      const solicitud = await api.alumna.solicitud();
      if (solicitud.esSolicitud && solicitud.paso === "correo" && actor.slugLiga) {
        guardarRegistro(actor.slugLiga, actor.correo);
        void navegar(`/r/${encodeURIComponent(actor.slugLiga)}`, { replace: true });
      } else {
        void navegar(solicitud.esSolicitud ? "/solicitud" : "/inicio", { replace: true });
      }
    } catch {
      void navegar("/inicio", { replace: true });
    }
  }

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!correo.trim() || !clave) {
      setError(t("Faltan tu correo o tu contraseña."));
      return;
    }

    setError(null);
    setEnviando(true);
    cerrarSesion();
    try {
      await abrir(await api.acceso.entrar(correo.trim(), clave, recordar));
    } catch (causa) {
      // El servidor ya redacta el mensaje para la usuaria; aquí no se inventa texto.
      setError(
        causa instanceof ErrorApi ? causa.message : t("Algo salió mal. Vuelve a intentarlo."),
      );
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="relative isolate min-h-full overflow-hidden">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-1/2 z-[-1] h-[min(110vh,64rem)] w-[min(82vw,30rem)] -translate-x-1/2 -translate-y-1/2 rounded-[3rem] bg-white/70 blur-3xl dark:bg-white/20"
      />

      <main className="relative mx-auto flex min-h-full w-full max-w-md flex-col justify-center gap-10 px-5 py-16">
        <header className="flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <img
              src="/icono-192.png"
              alt=""
              aria-hidden="true"
              className="size-8 shrink-0 rounded-marco border border-linea object-cover"
            />
            <Etiqueta>MYFITTPLAN</Etiqueta>
          </div>
          <Portada>{t("Entra a tu cuenta")}</Portada>
          <Apoyo>{t("Con el correo que le diste a tu coach.")}</Apoyo>
        </header>

      {/* Se llega aquí con `?caducada=1` cuando una petición devolvió 401. Decirlo evita que
          parezca que la contraseña dejó de servir. */}
      {new URLSearchParams(window.location.search).has("caducada") ? (
        <Aviso tono="atencion" titulo={t("Tu sesión expiró")}>
          {t("Vuelve a entrar. Es por seguridad: las sesiones no duran para siempre.")}
        </Aviso>
      ) : null}

      <form onSubmit={enviar} className="flex flex-col gap-5">
        <Campo id="correo" etiqueta={t("Correo")}>
          <Entrada
            id="correo"
            type="email"
            autoComplete="username"
            inputMode="email"
            value={correo}
            onChange={(e) => setCorreo(e.target.value)}
            placeholder="tu@correo.com"
          />
        </Campo>

        <Campo id="clave" etiqueta={t("Contraseña")} {...(error ? { error } : {})}>
          <Entrada
            id="clave"
            type="password"
            autoComplete="current-password"
            value={clave}
            onChange={(e) => setClave(e.target.value)}
            placeholder="••••••••"
          />
        </Campo>

        <Casilla
          id="recordar"
          titulo={t("Recordar mis datos")}
          checked={recordar}
          onChange={(e) => setRecordar(e.target.checked)}
        >
          {recordar ? (
            <>
              {t(
                "Guardamos tu correo y mantenemos la sesión abierta 30 días en este dispositivo. Tu contraseña nunca se guarda aquí.",
              )}
            </>
          ) : null}
        </Casilla>

        <Boton type="submit" medida="grande" ancho="completo" disabled={enviando}>
          {enviando ? t("Entrando…") : t("Entrar")}
        </Boton>
      </form>

      <Aviso tono="info" titulo={t("¿Olvidaste tu contraseña?")}>
        {t(
          "En esta versión no hay recuperación automática. Escríbele a tu coach y ella te genera una clave temporal desde su panel, después de verificar que eres tú.",
        )}
      </Aviso>

      <p className="text-micro text-tinta-suave">
        {t("Al entrar aceptas los")}{" "}
        <Link to="/legal/terminos" className="underline underline-offset-2">
          {t("Términos y Condiciones")}
        </Link>{" "}
        {t("y el")}{" "}
        <Link to="/legal/privacidad" className="underline underline-offset-2">
          {t("Aviso de Privacidad")}
        </Link>
        .
      </p>
      </main>
    </div>
  );
}
