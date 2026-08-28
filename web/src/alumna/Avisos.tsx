/** Los avisos que le manda su coach. Abrirlos los marca leídos y con eso se borran. */

import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

import { CargandoPantalla } from "@/componentes/Estado";
import { Apoyo, Boton, Etiqueta, Portada, Vacio } from "@/componentes/primitivas";
import { api, type AvisoDeAlumnaApi } from "@/lib/api";
import { fecha } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
import { actorGuardado } from "@/lib/sesion";
import { usarApi } from "@/lib/usarApi";

export function Avisos() {
  const { t } = useIdioma();
  const carga = usarApi<AvisoDeAlumnaApi[]>((s) => api.alumna.avisos(s), []);
  const marca = actorGuardado()?.marca ?? t("tu coach");
  const avisos = carga.datos ?? [];

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <Boton asChild tono="discreto" medida="icono" aria-label={t("Regresar")}>
            <Link to="/inicio">
              <ArrowLeft className="size-4" />
            </Link>
          </Boton>
          <Etiqueta>{t("Avisos")}</Etiqueta>
        </div>
        <Portada>{t("Lo que te manda {marca}", { marca })}</Portada>
        <Apoyo className="medida">
          {t("Del más reciente al más antiguo. No se guardan: una vez leídos desaparecen.")}
        </Apoyo>
      </header>

      {carga.cargando ? (
        <CargandoPantalla que={t("tus avisos")} filas={4} portada={false} />
      ) : avisos.length === 0 ? (
        <Vacio>{t("Todavía no tienes avisos.")}</Vacio>
      ) : (
        <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
          {avisos.map((a) => (
            <li key={a.ulid} className="flex flex-col gap-1.5 py-5">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <span className="text-menor font-semibold">{a.titulo}</span>
                <span className="text-micro text-tinta-suave">{fecha(a.recibidoEn)}</span>
              </div>
              <p className="medida text-cuerpo leading-relaxed text-balance">{a.cuerpo}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
