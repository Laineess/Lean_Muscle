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
import { correoRecordado, guardarActor, recordarCorreo } from "@/lib/sesion";

//: Cuentas que crea `app.semilla`. Solo se usan en desarrollo.
const CLAVE_DEMO = "Demo1234!";
const CUENTAS_DEMO: [string, string][] = [
  ["Alumna", "andrea.saenz@ejemplo.mx"],
  ["Coach", "mariana@leanmuscle.mx"],
  ["Superadmin", "admin@myprogressplan.com"],
];

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
    navegar(
      actor.rol === "coach" ? "/coach" : actor.rol === "admin_plataforma" ? "/plataforma" : "/inicio",
      { replace: true },
    );
  }

  /** Entra con una cuenta de la semilla. **Hace login de verdad.**
   *
   *  Antes falseaba el actor en `sessionStorage` sin pedir cookie, y con la API en pie eso
   *  dejaba una sesión que el servidor no reconocía: la primera petición devolvía 401 y
   *  echaba de vuelta al acceso. Solo se compila en desarrollo.
   */
  async function entrarDemostracion(cuenta: string) {
    setError(null);
    setEnviando(true);
    try {
      abrir(await api.acceso.entrar(cuenta, CLAVE_DEMO, false));
    } catch (causa) {
      setError(
        causa instanceof ErrorApi
          ? `${causa.message} ¿Sembraste la base con \`app.semilla\`?`
          : "No se pudo entrar con la cuenta de ejemplo.",
      );
    } finally {
      setEnviando(false);
    }
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

      {/* Se llega aquí con `?caducada=1` cuando una petición devolvió 401. Decirlo evita que
          parezca que la contraseña dejó de servir. */}
      {new URLSearchParams(window.location.search).has("caducada") ? (
        <Aviso tono="atencion" titulo="Tu sesión expiró">
          Vuelve a entrar. Es por seguridad: las sesiones no duran para siempre.
        </Aviso>
      ) : null}

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

      {/* Solo en desarrollo: `import.meta.env.DEV` es falso al compilar, así que este bloque
          ni siquiera llega al paquete que se despliega. */}
      {import.meta.env.DEV ? (
        <div className="flex flex-col gap-3">
          <Regla />
          <Etiqueta>Cuentas de la semilla</Etiqueta>
          <Apoyo>Entra con un toque. Solo aparece en desarrollo.</Apoyo>
          <div className="flex flex-wrap gap-2">
            {CUENTAS_DEMO.map(([rotulo, cuenta]) => (
              <Boton
                key={cuenta}
                tono="contorno"
                medida="chica"
                disabled={enviando}
                onClick={() => void entrarDemostracion(cuenta)}
              >
                {rotulo}
              </Boton>
            ))}
          </div>
        </div>
      ) : null}

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
