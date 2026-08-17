/** Lo que falla en silencio.
 *
 *  Las dos cifras que de verdad importan aquí son la cola de avisos y las fotografías por
 *  purgar, y las dos por el mismo motivo: **no producen ningún error cuando fallan**. Un
 *  correo que no salió no manda un correo diciendo que no salió, e incumplir el plazo de
 *  conservación no rompe nada — hasta que alguien lo pregunta.
 *
 *  La auditoría trae la acción, la cuenta y el momento. No trae el detalle ni el
 *  identificador de la entidad: con eso se responde «¿qué pasó en esta cuenta?» y sigue
 *  siendo imposible reconstruir a qué alumna corresponde cada movimiento.
 */

import { Cargando } from "@/componentes/Estado";
import {
  Apoyo,
  Aviso,
  Dato,
  Etiqueta,
  Portada,
  Regla,
  Titulo,
  Vacio,
} from "@/componentes/primitivas";
import { api, type MovimientoDeAuditoriaApi, type SaludApi } from "@/lib/api";
import { usarApi } from "@/lib/usarApi";

export function Salud() {
  const salud = usarApi<SaludApi>((senal) => api.plataforma.salud(senal));
  const auditoria = usarApi<MovimientoDeAuditoriaApi[]>((senal) =>
    api.plataforma.auditoria(60, senal),
  );

  if (salud.cargando) return <Cargando que="el estado del sistema" />;
  if (salud.error) {
    return (
      <Aviso tono="error" titulo="No se pudo consultar el estado">
        {salud.error.message}
      </Aviso>
    );
  }

  const d = salud.datos;
  if (!d) return <Vacio>Sin datos.</Vacio>;

  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta>Estado del sistema</Etiqueta>
        <Portada>Salud</Portada>
      </header>

      {d.avisosAgotados > 0 ? (
        <Aviso tono="error" titulo={`${d.avisosAgotados} avisos se rindieron`}>
          Fallaron cinco veces y ya no se reintentan. Revisa la configuración de correo:
          alguien no recibió su clave temporal o su recibo y no se enteró.
        </Aviso>
      ) : null}

      {d.fotosPorPurgar > 0 ? (
        <Aviso tono="atencion" titulo={`${d.fotosPorPurgar} fotografías pasaron su plazo`}>
          Deberían estar borradas. Comprueba que el trabajo de purga esté corriendo:
          <code className="ml-1">systemctl list-timers myfittplan-recordatorios</code>. El
          plazo de conservación está prometido por escrito en el Aviso de Privacidad.
        </Aviso>
      ) : null}

      <section className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-4">
        <Dato
          rotulo="Avisos en cola"
          valor={String(d.avisosPendientes)}
          nota={d.avisosAgotados > 0 ? `${d.avisosAgotados} agotados` : "ninguno agotado"}
        />
        <Dato
          rotulo="Fotos por purgar"
          valor={String(d.fotosPorPurgar)}
          nota={d.fotosPorPurgar === 0 ? "al día" : "revisar el trabajo"}
        />
        <Dato rotulo="Almacenamiento" valor={String(d.mbTotales)} unidad="MB" />
        <Dato rotulo="Sesiones vivas" valor={String(d.sesionesVivas)} />
        <Dato rotulo="Coaches activas" valor={String(d.coachesActivas)} nota="entraron este mes" />
        <Dato
          rotulo="Coaches inactivas"
          valor={String(d.coachesInactivas)}
          nota="30 días o más sin entrar"
        />
        <Dato rotulo="Dispositivos con push" valor={String(d.suscripcionesPush)} />
        <Dato
          rotulo="Último aviso enviado"
          valor={
            d.ultimoAvisoEnviado
              ? new Date(d.ultimoAvisoEnviado).toLocaleString("es-MX", {
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                })
              : "nunca"
          }
        />
      </section>

      <Regla />

      <section className="flex flex-col gap-4">
        <Titulo>Movimientos recientes</Titulo>
        <Apoyo className="medida">
          Qué se hizo y en qué cuenta. Sin el detalle ni el identificador de la entidad: este
          panel no puede reconstruir a qué alumna corresponde cada movimiento, y esa es
          justamente la línea que lo mantiene del lado correcto de la ley.
        </Apoyo>

        {auditoria.cargando ? (
          <Cargando que="la auditoría" />
        ) : (auditoria.datos ?? []).length === 0 ? (
          <Vacio>Todavía no hay movimientos registrados.</Vacio>
        ) : (
          <ul className="flex flex-col divide-y divide-linea border-y border-linea">
            {(auditoria.datos ?? []).map((m, i) => (
              <li
                key={`${m.cuando}-${i}`}
                className="grid grid-cols-[auto_1fr_auto] items-baseline gap-3 py-2"
              >
                <span className="cifra text-micro text-tinta-suave">
                  {new Date(m.cuando).toLocaleString("es-MX", {
                    day: "2-digit",
                    month: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
                <span className="text-menor">
                  {m.accion.replaceAll("_", " ")}{" "}
                  <span className="text-tinta-suave">· {m.entidad}</span>
                </span>
                <span className="text-micro text-tinta-media">{m.coach}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
