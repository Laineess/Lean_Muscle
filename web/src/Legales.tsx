/** Aviso de Privacidad y Términos y Condiciones.
 *
 *  Fuera del guardia de sesión: la ley exige que el aviso sea accesible **antes** de
 *  entregar ningún dato, y un documento que solo se ve tras entrar no cumple eso.
 */

import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { CargandoPantalla } from "@/componentes/Estado";
import { Markdown } from "@/componentes/Markdown";
import { Apoyo, Aviso, Boton, Etiqueta } from "@/componentes/primitivas";
import { api, type DocumentoLegalApi } from "@/lib/api";
import { useIdioma } from "@/lib/idioma";
import { actorGuardado } from "@/lib/sesion";
import { usarApi } from "@/lib/usarApi";

export function Legales() {
  const { documento = "privacidad" } = useParams();
  const marca = actorGuardado()?.marca;
  const { t } = useIdioma();

  const carga = usarApi<DocumentoLegalApi>(
    (senal) => api.legales.documento(documento, marca ?? null, senal),
    [documento, marca],
  );

  if (carga.cargando) return <CargandoPantalla que={t("el documento")} texto={8} filas={0} />;
  if (carga.error || !carga.datos) {
    return (
      <main className="mx-auto w-full max-w-3xl px-5 py-12 sm:px-6">
        <Aviso tono="error" titulo={t("No se pudo abrir el documento")}>
          {carga.error?.message ?? t("Inténtalo otra vez.")}
        </Aviso>
      </main>
    );
  }

  const d = carga.datos;

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-5 py-10 sm:px-6">
      <Boton asChild tono="discreto" medida="chica" className="w-fit">
        <Link to={actorGuardado() ? "/cuenta" : "/acceso"}>
          <ArrowLeft className="size-4" /> {t("Volver")}
        </Link>
      </Boton>

      <header className="flex flex-col gap-2">
        <Etiqueta>
          {t("Versión {version} · {actualizado}", {
            version: d.version,
            actualizado: d.actualizado,
          })}
        </Etiqueta>
      </header>

      {/* Un aviso de privacidad con huecos no cumple la LFPDPPP. Se dice aquí en lugar de
          aparentar que el documento está terminado. */}
      {d.marcadores.length > 0 ? (
        <Aviso tono="atencion" titulo={t("Este documento todavía no está completo")}>
          {t("Faltan por rellenar: {marcadores}. Está pendiente de revisión por abogado y no debe considerarse definitivo.", {
            marcadores: d.marcadores.join(", ").toLowerCase().replaceAll("_", " "),
          })}
        </Aviso>
      ) : null}

      <article>
        <Markdown texto={d.contenido} />
      </article>

      <Apoyo>
        {t("¿Dudas sobre tus datos? Escribe a")}{" "}
        <a href="mailto:privacidad@myfittplan.com" className="underline underline-offset-2">
          privacidad@myfittplan.com
        </a>
        .
      </Apoyo>
    </main>
  );
}
