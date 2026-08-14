import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { App } from "./App";
import { cuandoCaduqueLaSesion } from "./lib/api";
import { cerrarSesion } from "./lib/sesion";
import "./index.css";

const raiz = document.getElementById("root");
if (!raiz) throw new Error("Falta #root en index.html");

// Un 401 en cualquier petición significa que la cookie ya no vale. Se borra la copia del
// actor y se recarga en el acceso: sin esto la interfaz sigue en pie con datos de una sesión
// muerta y todos los botones fallan sin decir por qué.
cuandoCaduqueLaSesion(() => {
  cerrarSesion();
  if (!window.location.pathname.startsWith("/acceso")) {
    window.location.replace("/acceso?caducada=1");
  }
});

createRoot(raiz).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
