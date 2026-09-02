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
import { useIdioma } from "@/lib/idioma";

export function Apariencia() {
  const { t } = useIdioma();
  const actor = actorGuardado();
  const carga = usarApi<MarcaApi>((senal) => api.coach.marca(senal));

  const [nombre, setNombre] = useState("");
  const [marca, setMarca] = useState("");
  const [acento, setAcento] = useState(actor?.colorAcento ?? coach.colorAcento);
  const [secundario, setSecundario] = useState(actor?.colorSecundario ?? "#c9a227");
  const [tieneLogo, setTieneLogo] = useState(false);
  const [versionLogo, setVersionLogo] = useState(0);
  const [datosBancarios, setDatosBancarios] = useState("");
  const [guardado, setGuardado] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const entradaLogo = useRef<HTMLInputElement>(null);

  usarPaleta(acento, secundario);

  // Los campos se rellenan cuando llega la marca del servidor, no antes: escribirlos con la
  // copia de `sessionStorage` haría que un guardado pisara lo que hubiera en la base.
  useEffect(() => {
    if (!carga.datos) return;
    setNombre(carga.datos.nombre);
    setMarca(carga.datos.marca);
    setAcento(carga.datos.colorAcento);
    setSecundario(carga.datos.colorSecundario);
    setTieneLogo(carga.datos.tieneLogo);
    setDatosBancarios(carga.datos.datosBancarios ?? "");
  }, [carga.datos]);

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
        datosBancarios,
      });
      guardarActor({
        ...(actor ?? nueva),
        marca: nueva.marca,
        colorAcento: nueva.colorAcento,
        colorSecundario: nueva.colorSecundario,
      } as never);
      setGuardado(true);
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : t("No se pudo guardar la marca."));
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
      setFallo(causa instanceof ErrorApi ? causa.message : t("No se pudo subir el logo."));
    } finally {
      setOcupado(false);
      if (entradaLogo.current) entradaLogo.current.value = "";
    }
  }

  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta>{t("Cómo se ve tu plataforma")}</Etiqueta>
        <Portada>{t("Apariencia")}</Portada>
      </header>

      {/* ---- Marca ---- */}
      <section className="flex flex-col gap-5">
        <div className="flex flex-col gap-1">
          <Titulo icono={Palette}>{t("Tu marca")}</Titulo>
          <Apoyo>{t("Tus alumnas ven tu logo y tu color dentro de la plataforma.")}</Apoyo>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          {tieneLogo ? (
            <img
              src={urlDeLogo(versionLogo)}
              alt={t("Tu logo")}
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
            {tieneLogo ? t("Cambiar logo") : t("Subir logo")}
          </Boton>
          <Apoyo>{t("Se recorta al centro en un cuadrado. Sin logo se usan tus iniciales.")}</Apoyo>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Campo id="aj-nombre" etiqueta={t("Tu nombre")}>
            <Entrada id="aj-nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} />
          </Campo>
          <Campo
            id="aj-marca"
            etiqueta={t("Nombre de tu marca")}
            ayuda={t("Es lo que ven tus alumnas. Puede no ser tu nombre.")}
          >
            <Entrada id="aj-marca" value={marca} onChange={(e) => setMarca(e.target.value)} />
          </Campo>
        </div>

        <Campo
          id="aj-bancario"
          etiqueta={t("Dónde te pagan")}
          ayuda={t("Cuenta, CLABE, referencia… Lo que tus alumnas necesitan para pagarte. Se les muestra al agendar y al subir su comprobante.")}
        >
          <textarea
            id="aj-bancario"
            rows={5}
            value={datosBancarios}
            onChange={(e) => setDatosBancarios(e.target.value)}
            placeholder={t("Banco · Titular · Cuenta o CLABE · Referencia")}
            className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed placeholder:text-tinta-suave focus:border-tinta focus:outline-none"
          />
        </Campo>

        <div className="grid gap-5 sm:grid-cols-2">
          <SelectorDeColor
            id="aj-acento"
            etiqueta={t("Color de acento")}
            ayuda={t("Filetes, bordes, iconos y estados activos.")}
            color={acento}
            onCambio={probar}
          />
          <SelectorDeColor
            id="aj-secundario"
            etiqueta={t("Color secundario")}
            ayuda={t("Acompaña al acento. Sirve para separar dos bloques hermanos.")}
            color={secundario}
            onCambio={probarSecundario}
          />
        </div>

        <VistaPreviaDeColores acento={acento} secundario={secundario} />

        <div>
          <Boton disabled={ocupado || !nombre.trim() || !marca.trim()} onClick={() => void guardarMarca()}>
            {t("Guardar marca")}
          </Boton>
          {guardado ? <Apoyo className="mt-2">{t("Marca actualizada.")}</Apoyo> : null}
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
          <Titulo icono={Contrast}>{t("Claro y oscuro")}</Titulo>
          <Apoyo>{t("Solo cambia cómo lo ves tú. Cada alumna elige el suyo.")}</Apoyo>
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
  const { t } = useIdioma();
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
          aria-label={t("{etiqueta} en hexadecimal", { etiqueta })}
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
  const { t } = useIdioma();
  const temas = [
    { rotulo: "Claro", fondo: "#ffffff", tinta: "#0c0c0c", linea: "#e4e4e7" },
    { rotulo: "Oscuro", fondo: "#0c0c0c", tinta: "#fafafa", linea: "#27272a" },
  ];
  return (
    <div className="flex flex-col gap-2">
      <Etiqueta>{t("Cómo se ven en cada tema")}</Etiqueta>
      <div className="grid gap-3 sm:grid-cols-2">
        {temas.map((tema) => {
          const a = paletaDe(acento, tema.fondo);
          const b = paletaDe(secundario, tema.fondo);
          return (
            <div
              key={tema.rotulo}
              className="flex flex-col gap-3 rounded-marco border p-4"
              style={{ background: tema.fondo, borderColor: tema.linea, color: tema.tinta }}
            >
              <span className="text-micro font-semibold uppercase tracking-[0.12em] opacity-60">
                {t(tema.rotulo)}
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
                    {t(rotulo)} {t("en filete")}
                  </span>
                  <span className="pl-3 text-menor font-semibold" style={{ color: p.texto }}>
                    {t(rotulo)} {t("en texto")}
                  </span>
                  <span
                    className="rounded-marco px-3 py-1 text-micro"
                    style={{ background: p.sutil, color: p.texto }}
                  >
                    {t("Fondo teñido")}
                  </span>
                </div>
              ))}
            </div>
          );
        })}
      </div>
      <Apoyo>
        {t("Elige el color que quieras: el sistema lo aclara u oscurece lo justo para que se lea en cada tema, sin cambiarle el tono.")}
      </Apoyo>
    </div>
  );
}
