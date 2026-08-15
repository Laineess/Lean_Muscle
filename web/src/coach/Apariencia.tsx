/** Apariencia: la marca de la coach y el tema de la interfaz.
 *
 *  Las dos cosas responden a la misma pregunta —cómo se ve esto— aunque una la ven sus
 *  alumnas y la otra solo ella. El color de acento es el único token que cambia con la
 *  marca: negro y gris son la estructura y no se tocan, así que cambiarlo no descuadra
 *  ninguna pantalla.
 */

import { useEffect, useRef, useState } from "react";

import { InterruptorDeTema } from "@/componentes/Tema";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Entrada,
  Etiqueta,
  Portada,
  Regla,
  Titulo,
} from "@/componentes/primitivas";
import { coach } from "@/lib/datos";
import { iniciales } from "@/lib/formato";
import { ErrorApi, api, urlDeLogo, type MarcaApi } from "@/lib/api";
import { marcaCambiada } from "@/lib/marca";
import { actorGuardado, guardarActor } from "@/lib/sesion";
import { usarApi } from "@/lib/usarApi";
import { cn } from "@/lib/utils";

export function Apariencia() {
  const actor = actorGuardado();
  const carga = usarApi<MarcaApi>((senal) => api.coach.marca(senal));

  const [nombre, setNombre] = useState("");
  const [marca, setMarca] = useState("");
  const [acento, setAcento] = useState(actor?.colorAcento ?? coach.colorAcento);
  const [tieneLogo, setTieneLogo] = useState(false);
  const [versionLogo, setVersionLogo] = useState(0);
  const [guardado, setGuardado] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const entradaLogo = useRef<HTMLInputElement>(null);

  // Los campos se rellenan cuando llega la marca del servidor, no antes: escribirlos con la
  // copia de `sessionStorage` haría que un guardado pisara lo que hubiera en la base.
  useEffect(() => {
    if (!carga.datos) return;
    setNombre(carga.datos.nombre);
    setMarca(carga.datos.marca);
    setAcento(carga.datos.colorAcento);
    setTieneLogo(carga.datos.tieneLogo);
    document.documentElement.style.setProperty("--acento", carga.datos.colorAcento);
  }, [carga.datos]);

  /** Se aplica en vivo: cambiar un color a ciegas y descubrir el resultado al guardar es
   *  peor experiencia que verlo mientras se elige. */
  function probar(color: string) {
    setAcento(color);
    document.documentElement.style.setProperty("--acento", color);
    setGuardado(false);
  }

  async function guardarMarca() {
    setFallo(null);
    setOcupado(true);
    try {
      const nueva = await api.coach.guardarMarca({ nombre, marca, colorAcento: acento });
      guardarActor({ ...(actor ?? nueva), marca: nueva.marca, colorAcento: nueva.colorAcento } as never);
      setGuardado(true);
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo guardar la marca.");
    } finally {
      setOcupado(false);
    }
  }

  async function subirLogo(archivo: File) {
    setFallo(null);
    setOcupado(true);
    try {
      await api.coach.subirLogo(archivo);
      setTieneLogo(true);
      // Cambia la versión para que el navegador no siga sirviendo el logo anterior, y se
      // avisa a la barra superior, que vive fuera de esta pantalla y no se enteraría.
      setVersionLogo((v) => v + 1);
      marcaCambiada();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo subir el logo.");
    } finally {
      setOcupado(false);
      if (entradaLogo.current) entradaLogo.current.value = "";
    }
  }

  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta>Cómo se ve tu plataforma</Etiqueta>
        <Portada>Apariencia</Portada>
      </header>

      {/* ---- Marca ---- */}
      <section className="flex flex-col gap-5">
        <div className="flex flex-col gap-1">
          <Titulo>Tu marca</Titulo>
          <Apoyo>Tus alumnas ven tu logo y tu color dentro de la plataforma.</Apoyo>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          {tieneLogo ? (
            <img
              src={urlDeLogo(versionLogo)}
              alt="Tu logo"
              className="size-14 rounded-marco border border-linea object-cover"
            />
          ) : (
            <span className="grid size-14 place-items-center rounded-marco border border-linea-fuerte text-menor font-bold">
              {iniciales(marca || actor?.marca || coach.marca)}
            </span>
          )}
          <input
            ref={entradaLogo}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const archivo = e.target.files?.[0];
              if (archivo) void subirLogo(archivo);
            }}
          />
          <Boton
            tono="contorno"
            medida="chica"
            disabled={ocupado}
            onClick={() => entradaLogo.current?.click()}
          >
            {tieneLogo ? "Cambiar logo" : "Subir logo"}
          </Boton>
          <Apoyo>Se recorta al centro en un cuadrado. Sin logo se usan tus iniciales.</Apoyo>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="aj-nombre" etiqueta="Tu nombre">
            <Entrada id="aj-nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} />
          </Campo>
          <Campo
            id="aj-marca"
            etiqueta="Nombre de tu marca"
            ayuda="Es lo que ven tus alumnas. Puede no ser tu nombre."
          >
            <Entrada id="aj-marca" value={marca} onChange={(e) => setMarca(e.target.value)} />
          </Campo>
        </div>

        <Campo
          id="aj-acento"
          etiqueta="Color de acento"
          ayuda="Se usa en filetes, bordes y estados activos. Nunca en texto largo: el contraste no alcanza."
        >
          <div className="flex items-center gap-3">
            <input
              id="aj-acento"
              type="color"
              value={acento}
              onChange={(e) => probar(e.target.value)}
              className="h-11 w-14 cursor-pointer rounded-marco border border-linea bg-fondo p-1"
            />
            <Entrada
              value={acento}
              onChange={(e) => probar(e.target.value)}
              className="max-w-32 font-mono"
              aria-label="Color en hexadecimal"
            />
            <span className={cn("h-11 flex-1 rounded-marco border border-linea")}>
              <span className="block h-full border-l-2 border-l-acento pl-3 text-menor leading-[2.75rem] text-tinta-media">
                Así se ve un filete con tu color
              </span>
            </span>
          </div>
        </Campo>

        <div>
          <Boton disabled={ocupado || !nombre.trim() || !marca.trim()} onClick={() => void guardarMarca()}>
            Guardar marca
          </Boton>
          {guardado ? <Apoyo className="mt-2">Marca actualizada.</Apoyo> : null}
          {fallo ? (
            <Aviso tono="error" className="mt-3">
              {fallo}
            </Aviso>
          ) : null}
        </div>
      </section>

      <Regla />

      {/* ---- Tema ---- */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <Titulo>Claro y oscuro</Titulo>
          <Apoyo>Solo cambia cómo lo ves tú. Cada alumna elige el suyo.</Apoyo>
        </div>
        <InterruptorDeTema className="w-fit" />
      </section>
    </div>
  );
}
