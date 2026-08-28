/** Lo que la plataforma le cobra a sus coaches.
 *
 *  No se confunde con las finanzas de la coach, que son otra pantalla y otra tabla: aquí el
 *  ingreso es la suscripción que ella paga, no lo que le pagan sus alumnas.
 *
 *  Sin pasarela: los cobros se registran a mano tras recibir la transferencia. El día que se
 *  conecte un cobro automático, estas mismas cifras son las que tendría que sincronizar.
 */

import { Clock, TrendingUp, Wallet } from "lucide-react";
import { CargandoPantalla } from "@/componentes/Estado";
import { Grafica } from "@/componentes/Grafica";
import { Apoyo, Aviso, Chip, Dato, Etiqueta, Portada, Regla, Titulo, Vacio } from "@/componentes/primitivas";
import { api, type FacturacionApi, type FilaDeCoachApi } from "@/lib/api";
import { fecha, num } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
import { usarApi } from "@/lib/usarApi";

export function Facturacion() {
  const resumen = usarApi<FacturacionApi>((senal) => api.plataforma.facturacion(12, senal));
  const coaches = usarApi<FilaDeCoachApi[]>((senal) => api.plataforma.coaches(senal));
  const { t } = useIdioma();

  if (resumen.cargando || coaches.cargando)
    return <CargandoPantalla que={t("la facturación")} cifras={4} filas={5} />;
  if (resumen.error) {
    return (
      <Aviso tono="error" titulo={t("No se pudo cargar la facturación")}>
        {resumen.error.message}
      </Aviso>
    );
  }

  const d = resumen.datos;
  if (!d) return <Vacio>{t("Todavía no hay nada que facturar.")}</Vacio>;

  const hoy = new Date().toISOString().slice(0, 10);
  const morosas = (coaches.datos ?? []).filter(
    (c) =>
      c.suscripcion &&
      (c.suscripcion.estado === "vencida" ||
        (c.suscripcion.vigenteHasta !== null && c.suscripcion.vigenteHasta < hoy)),
  );

  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta icono={Wallet}>{t("Suscripciones de coaches")}</Etiqueta>
        <Portada>{t("Facturación")}</Portada>
      </header>

      <section className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-4">
        <Dato rotulo={t("Cobrado este año")} valor={`$${num(d.cobradoEnElAno)}`} grande />
        <Dato
          rotulo={t("Esperado al mes")}
          valor={`$${num(d.facturacionMensualEsperada)}`}
          nota={t("suma de suscripciones activas")}
        />
        <Dato rotulo={t("Al corriente")} valor={String(d.coachesAlCorriente)} />
        <Dato
          rotulo={t("Vencidas")}
          valor={String(d.coachesVencidas)}
          nota={d.coachesEnCortesia > 0 ? t("{n} en cortesía", { n: d.coachesEnCortesia }) : undefined}
        />
      </section>

      <Regla />

      <section className="flex flex-col gap-4">
        <Titulo icono={TrendingUp}>{t("Cobrado por mes")}</Titulo>
        {d.porMes.length >= 2 ? (
          <Grafica
            puntos={d.porMes.map((m) => ({ etiqueta: m.mes.slice(5), valor: m.ingresos }))}
            unidad="$"
            decimales={0}
          />
        ) : (
          <Vacio>{t("Con un mes de cobros todavía no hay línea que dibujar.")}</Vacio>
        )}
      </section>

      <Regla />

      <section className="flex flex-col gap-4">
        <Titulo icono={Clock}>{t("Por cobrar")}</Titulo>
        {morosas.length === 0 ? (
          <Apoyo>{t("Nadie debe nada. Es la única cifra de esta pantalla que conviene que sea cero.")}</Apoyo>
        ) : (
          <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
            {morosas.map((c) => (
              <li key={c.ulid} className="flex flex-wrap items-baseline justify-between gap-3 py-3">
                <span className="flex items-baseline gap-3">
                  <span className="text-menor font-medium">{c.nombre}</span>
                  <Chip tono="error">
                    {c.suscripcion?.vigenteHasta
                      ? t("venció el {fecha}", { fecha: fecha(c.suscripcion.vigenteHasta) })
                      : t("sin periodo pagado")}
                  </Chip>
                </span>
                <span className="cifra font-semibold">${num(c.suscripcion?.precio ?? 0)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
