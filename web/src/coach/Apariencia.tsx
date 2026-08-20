/** Apariencia: la marca de la coach y el tema de la interfaz.
 *
 *  El color de acento es el único token que cambia con la marca: negro y gris son la
 *  estructura, así que cambiarlo no descuadra ninguna pantalla.
 */

import { Contrast, Palette } from "lucide-react";
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
import { paletaDe } from "@/lib/color";
import { usarPaleta } from "@/lib/paleta";
import { coach } from "@/lib/datos";
import { iniciales } from "@/lib/formato";
import { ErrorApi, api, urlDeLogo, type MarcaApi } from "@/lib/api";
import { marcaCambiada } from "@/lib/marca";
import { actorGuardado, guardarActor } from "@/lib/sesion";
import { usarApi } from "@/lib/usarApi";

export function Apariencia() {
  const actor = actorGuardado();
  const carga = usarApi<MarcaApi>((senal) => api.coach.marca(senal));

  const [nombre, setNombre] = useState("");
  const [marca, setMarca] = useState("");
  const [acento, setAcento] = useState(actor?.colorAcento ?? coach.colorAcento);
  const [secundario, setSecundario] = useState(actor?.colorSecundario ?? "#c9a227");
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
    setSecundario(carga.datos.colorSecundario);
    setTieneLogo(carga.datos.tieneLogo);
  }, [carga.datos]);

  // Se aplica en vivo mientras elige: descubrir el resultado al guardar es peor que verlo.
  usarPaleta(acento, secundario);

  function probar(color: string) {
    setAcento(color);
    setGuardado(false);
  }

  function probarSecundario(color: string) {
    setSecundario(color);
    setGuardado(false);
  }

  async function guardarMarca() {
    setFallo(null);
    setOcupado(true);
    try {
      const nueva = await api.coach.guardarMarca({
        nombre,
        marca,
        colorAcento: acento,
        colorSecundario: secundario,
      });
      guardarActor({
        ...(actor ?? nueva),
        marca: nueva.marca,
        colorAcento: nueva.colorAcento,
        colorSecundario: nueva.colorSecundario,
      } as never);
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
          <Titulo icono={Palette}>Tu marca</Titulo>
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

        <div className="grid gap-5 sm:grid-cols-2">
          <SelectorDeColor
            id="aj-acento"
            etiqueta="Color de acento"
            ayuda="Filetes, bordes, iconos y estados activos."
            color={acento}
            onCambio={probar}
          />
          <SelectorDeColor
            id="aj-secundario"
            etiqueta="Color secundario"
            ayuda="Acompaña al acento. Sirve para separar dos bloques hermanos."
            color={secundario}
            onCambio={probarSecundario}
          />
        </div>

        <VistaPreviaDeColores acento={acento} secundario={secundario} />

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
          <Titulo icono={Contrast}>Claro y oscuro</Titulo>
          <Apoyo>Solo cambia cómo lo ves tú. Cada alumna elige el suyo.</Apoyo>
        </div>
        <InterruptorDeTema className="w-fit" />
      </section>
    </div>
  );
}


/* --------------------------------------------------------- Selector de color --- */

function SelectorDeColor({
  id,
  etiqueta,
  ayuda,
  color,
  onCambio,
}: {
  id: string;
  etiqueta: string;
  ayuda: string;
  color: string;
  onCambio: (v: string) => void;
}) {
  return (
    <Campo id={id} etiqueta={etiqueta} ayuda={ayuda}>
      <div className="flex items-center gap-3">
        <input
          id={id}
          type="color"
          value={color}
          onChange={(e) => onCambio(e.target.value)}
          className="h-11 w-14 shrink-0 cursor-pointer rounded-marco border border-linea bg-fondo p-1"
        />
        <Entrada
          value={color}
          onChange={(e) => onCambio(e.target.value)}
          className="font-mono"
          aria-label={`${etiqueta} en hexadecimal`}
        />
      </div>
    </Campo>
  );
}

/* ------------------------------------------------------------- Vista previa --- */

/** Sus dos colores en los dos temas, uno junto al otro.
 *
 *  Los cuadros no llevan su hex tal cual: llevan el que la interfaz va a usar de verdad,
 *  que puede ser más claro o más oscuro. Un verde oscuro sobre negro no se ve, y aquí se ve
 *  que el sistema lo aclara en vez de descubrirlo con la app puesta en oscuro.
 */
function VistaPreviaDeColores({ acento, secundario }: { acento: string; secundario: string }) {
  const temas = [
    { rotulo: "Claro", fondo: "#ffffff", tinta: "#0c0c0c", linea: "#e4e4e7" },
    { rotulo: "Oscuro", fondo: "#0c0c0c", tinta: "#fafafa", linea: "#27272a" },
  ];
  return (
    <div className="flex flex-col gap-2">
      <Etiqueta>Cómo se ven en cada tema</Etiqueta>
      <div className="grid gap-3 sm:grid-cols-2">
        {temas.map((t) => {
          const a = paletaDe(acento, t.fondo);
          const b = paletaDe(secundario, t.fondo);
          return (
            <div
              key={t.rotulo}
              className="flex flex-col gap-3 rounded-marco border p-4"
              style={{ background: t.fondo, borderColor: t.linea, color: t.tinta }}
            >
              <span className="text-micro font-semibold uppercase tracking-[0.12em] opacity-60">
                {t.rotulo}
              </span>
              {[
                { p: a, rotulo: "Acento" },
                { p: b, rotulo: "Secundario" },
              ].map(({ p, rotulo }) => (
                <div key={rotulo} className="flex flex-col gap-1">
                  <span
                    className="border-l-[3px] pl-3 text-menor"
                    style={{ borderColor: p.base }}
                  >
                    {rotulo} en filete
                  </span>
                  <span className="pl-3 text-menor font-semibold" style={{ color: p.texto }}>
                    {rotulo} en texto
                  </span>
                  <span
                    className="rounded-marco px-3 py-1 text-micro"
                    style={{ background: p.sutil, color: p.texto }}
                  >
                    Fondo teñido
                  </span>
                </div>
              ))}
            </div>
          );
        })}
      </div>
      <Apoyo>
        Elige el color que quieras: el sistema lo aclara u oscurece lo justo para que se lea
        en cada tema, sin cambiarle el tono.
      </Apoyo>
    </div>
  );
}
