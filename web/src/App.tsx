import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { Acceso } from "@/Acceso";
import { Chequeo } from "@/alumna/Chequeo";
import { Cuenta } from "@/alumna/Cuenta";
import { Evolucion } from "@/alumna/Evolucion";
import { Inicio } from "@/alumna/Inicio";
import { MarcoAlumna } from "@/alumna/Marco";
import { Mensajes } from "@/alumna/Mensajes";
import { MiPlan } from "@/alumna/MiPlan";
import { Agenda } from "@/coach/Agenda";
import { Ajustes } from "@/coach/Ajustes";
import { Conversacion } from "@/coach/Conversacion";
import { Finanzas } from "@/coach/Finanzas";
import { Cartera } from "@/coach/Cartera";
import { Constructor } from "@/coach/Constructor";
import { MarcoCoach } from "@/coach/Marco";
import { Panel } from "@/coach/Panel";
import { Validacion } from "@/coach/Validacion";
import { api } from "@/lib/api";
import { registrarTrabajador } from "@/lib/push";
import { Coaches } from "@/plataforma/Coaches";
import { Facturacion } from "@/plataforma/Facturacion";
import { MarcoPlataforma } from "@/plataforma/Marco";
import { Salud } from "@/plataforma/Salud";
import { actorGuardado, guardarActor, rolActual, type Rol } from "@/lib/sesion";

/** Guarda de ruta.
 *
 *  Es comodidad de navegación, no seguridad: quien manda es el servidor, que resuelve el
 *  rol desde la cookie de sesión y responde 403 si no corresponde. Un guard de cliente se
 *  salta editando memoria del navegador.
 */
function Exige({ rol, children }: { rol: Rol; children: React.ReactNode }) {
  const { pathname } = useLocation();
  const actual = rolActual();

  if (actual === null) return <Navigate to="/acceso" replace state={{ desde: pathname }} />;
  if (actual !== rol) return <Navigate to={INICIO_DE[actual]} replace />;
  return <>{children}</>;
}

/** A dónde va cada rol al entrar. */
const INICIO_DE: Record<NonNullable<Rol>, string> = {
  coach: "/coach",
  alumna: "/inicio",
  admin_plataforma: "/plataforma",
};

function Entrada() {
  const actual = rolActual();
  return <Navigate to={actual ? INICIO_DE[actual] : "/acceso"} replace />;
}

export function App() {
  const actor = actorGuardado();

  // El acento de la Coach reemplaza al dorado de MyProgressPlan en toda la interfaz de sus
  // alumnas. Negro y gris son la estructura y no se tocan: solo cambia esta variable.
  useEffect(() => {
    if (actor?.colorAcento) {
      document.documentElement.style.setProperty("--acento", actor.colorAcento);
    }
  }, [actor?.colorAcento]);

  // El service worker se registra al arrancar; el **permiso** de notificaciones no se pide
  // aquí sino cuando la usuaria toca el interruptor. Un navegador que ve el diálogo de
  // permisos sin contexto lo bloquea, y bloqueado no se puede volver a pedir: se acabaría el
  // canal para siempre en ese dispositivo.
  useEffect(() => {
    void registrarTrabajador();
  }, []);

  // `sessionStorage` es una caché para pintar la barra sin esperar a la red, no la verdad.
  // Sin comprobarla, una cookie caducada dejaba la interfaz en pie con todas las peticiones
  // devolviendo 401. Un 401 aquí lo recoge el manejador global y manda al acceso.
  useEffect(() => {
    if (!actor) return;
    api.acceso
      .yo()
      .then(guardarActor)
      .catch(() => {
        /* el 401 ya lo trata el manejador global; otros errores no deben cerrar sesión */
      });
    // Solo al arrancar: en cada navegación sería una petición de más por pantalla.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Routes>
      <Route path="/" element={<Entrada />} />
      <Route path="/acceso" element={<Acceso />} />

      <Route
        element={
          <Exige rol="alumna">
            <MarcoAlumna />
          </Exige>
        }
      >
        <Route path="/inicio" element={<Inicio />} />
        <Route path="/plan" element={<MiPlan />} />
        <Route path="/evolucion" element={<Evolucion />} />
        <Route path="/mensajes" element={<Mensajes />} />
        <Route path="/cuenta" element={<Cuenta />} />
      </Route>

      {/* El chequeo va fuera del marco de pestañas: es un flujo a pantalla completa y
          cualquier cosa que distraiga de terminarlo sobra. */}
      <Route
        path="/chequeo"
        element={
          <Exige rol="alumna">
            <Chequeo />
          </Exige>
        }
      />

      <Route
        element={
          <Exige rol="coach">
            <MarcoCoach />
          </Exige>
        }
      >
        <Route path="/coach" element={<Panel />} />
        <Route path="/coach/alumnas" element={<Cartera />} />
        <Route path="/coach/agenda" element={<Agenda />} />
        <Route path="/coach/finanzas" element={<Finanzas />} />
        <Route path="/coach/ajustes" element={<Ajustes />} />
        <Route path="/coach/mensajes/:alumnaUlid" element={<Conversacion />} />
        <Route path="/coach/validar/:alumnaUlid" element={<Validacion />} />
        <Route path="/coach/plan/:alumnaUlid" element={<Constructor />} />
      </Route>

      <Route
        element={
          <Exige rol="admin_plataforma">
            <MarcoPlataforma />
          </Exige>
        }
      >
        <Route path="/plataforma" element={<Coaches />} />
        <Route path="/plataforma/facturacion" element={<Facturacion />} />
        <Route path="/plataforma/salud" element={<Salud />} />
      </Route>

      <Route path="*" element={<Entrada />} />
    </Routes>
  );
}
