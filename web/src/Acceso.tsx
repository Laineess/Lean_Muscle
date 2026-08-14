/** Pantalla de acceso.
 *
 *  «Recordar mis datos» **no guarda la contraseña**. Guarda el correo para no reescribirlo
 *  y le pide al servidor una sesión de larga duración; el token vive en una cookie HttpOnly
 *  que JavaScript no puede leer. Guardar contraseñas en el navegador es lo que convierte el
 *  robo de un teléfono en el robo de un expediente clínico.
 *
 *  En el MVP no hay recuperación automática: la coach genera una clave temporal desde su
 *  panel tras verificar identidad. Es una decisión tomada, y la pantalla lo explica en vez
 *  de dejar a la alumna atorada.
 */

import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { Apoyo, Aviso, Boton, Campo, Casilla, Entrada, Etiqueta, Portada, Regla } from "@/componentes/primitivas";
import { ErrorApi, api, type ActorPublico } from "@/lib/api";
import { correoRecordado, guardarActor, recordarCorreo, type Rol } from "@/lib/sesion";

const ACENTO_POR_DEFECTO = "#c9a227";

export function Acceso() {
  const navegar = useNavigate();
  const guardado = correoRecordado();

  const [correo, setCorreo] = useState(guardado);
  const [clave, setClave] = useState("");
  const [recordar, setRecordar] = useState(Boolean(guardado));
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  function abrir(actor: ActorPublico) {
    recordarCorreo(correo, recordar);
    guardarActor(actor);
    navegar(actor.rol === "coach" ? "/coach" : "/inicio", { replace: true });
  }

  /** Entrada directa sin servidor, para revisar las pantallas. Desaparece con la API en pie. */
  function entrarDemostracion(rol: Rol) {
    abrir({
      rol,
      nombre: rol === "coach" ? "Mariana Cervantes" : "Andrea Sáenz",
      correo: correo || "demo@myprogressplan.com",
      colorAcento: ACENTO_POR_DEFECTO,
      marca: "LeanMuscle",
    });
  }

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!correo.trim() || !clave) {
      setError("Faltan tu correo o tu contraseña.");
      return;
    }

    setError(null);
    setEnviando(true);
    try {
      abrir(await api.acceso.entrar(correo.trim(), clave, recordar));
    } catch (causa) {
      // El servidor ya redacta el mensaje para la usuaria; aquí no se inventa texto.
      setError(
        causa instanceof ErrorApi ? causa.message : "Algo salió mal. Vuelve a intentarlo.",
      );
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-full w-full max-w-sm flex-col justify-center gap-10 px-5 py-16">
      <header className="flex flex-col gap-3">
        <Etiqueta>MyProgressPlan</Etiqueta>
        <Portada>Entra a tu cuenta</Portada>
        <Apoyo>Con el correo que le diste a tu coach.</Apoyo>
      </header>

      <form onSubmit={enviar} className="flex flex-col gap-5">
        <Campo id="correo" etiqueta="Correo">
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

        <Campo id="clave" etiqueta="Contraseña" {...(error ? { error } : {})}>
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
          titulo="Recordar mis datos"
          checked={recordar}
          onChange={(e) => setRecordar(e.target.checked)}
        >
          Guardamos tu correo y mantenemos la sesión abierta 30 días en este dispositivo. Tu
          contraseña nunca se guarda aquí.
        </Casilla>

        <Boton type="submit" medida="grande" ancho="completo" disabled={enviando}>
          {enviando ? "Entrando…" : "Entrar"}
        </Boton>
      </form>

      <Aviso tono="info" titulo="¿Olvidaste tu contraseña?">
        En esta versión no hay recuperación automática. Escríbele a tu coach y ella te genera
        una clave temporal desde su panel, después de verificar que eres tú.
      </Aviso>

      {/* Bloque de demostración: desaparece cuando exista `/api/auth/login`. */}
      <div className="flex flex-col gap-3">
        <Regla />
        <Etiqueta>Para revisar sin servidor</Etiqueta>
        <Apoyo>
          Si la API no está corriendo, entra directo a cualquiera de los dos frentes con datos
          de ejemplo. Con el servidor en pie, usa el formulario de arriba.
        </Apoyo>
        <div className="flex flex-wrap gap-2">
          <Boton tono="contorno" medida="chica" onClick={() => entrarDemostracion("alumna")}>
            Ver como alumna
          </Boton>
          <Boton tono="contorno" medida="chica" onClick={() => entrarDemostracion("coach")}>
            Ver como coach
          </Boton>
        </div>
      </div>

      <p className="text-micro text-tinta-suave">
        Al entrar aceptas los Términos y el{" "}
        <a href="/privacidad" className="underline underline-offset-2">
          Aviso de Privacidad
        </a>
        .
      </p>
    </main>
  );
}
