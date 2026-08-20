/** Interruptor de notificaciones push.
 *
 *  El permiso se pide **aquí**, al tocar el botón, y no al cargar la app: un navegador que ve
 *  el diálogo sin contexto lo bloquea, y bloqueado no se puede volver a pedir. Se acabaría el
 *  canal para siempre en ese dispositivo, sin manera de recuperarlo desde la aplicación.
 */

import { Bell, BellOff } from "lucide-react";
import { useEffect, useState } from "react";

import { Apoyo, Aviso, Boton, Chip, Titulo } from "@/componentes/primitivas";
import { activar, desactivar, estado, type EstadoPush } from "@/lib/push";

export function Notificaciones({ para }: { para: "alumna" | "coach" }) {
  const [actual, setActual] = useState<EstadoPush | null>(null);
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let vivo = true;
    void estado().then((e) => vivo && setActual(e));
    return () => {
      vivo = false;
    };
  }, []);

  async function alternar() {
    setError(null);
    setTrabajando(true);
    try {
      setActual(actual === "activo" ? await desactivar() : await activar());
    } catch (causa: unknown) {
      setError(causa instanceof Error ? causa.message : "No se pudieron activar las notificaciones.");
    } finally {
      setTrabajando(false);
    }
  }

  const texto =
    para === "alumna"
      ? "Tu chequeo del mes, cuando tu coach revise, tus consultas y tus pagos."
      : "Chequeos por validar, consultas del día y comprobantes que llegan.";

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between gap-3">
        <Titulo>Notificaciones</Titulo>
        {actual === "activo" ? (
          <Chip tono="exito">Activas</Chip>
        ) : actual === "bloqueado" ? (
          <Chip tono="error">Bloqueadas</Chip>
        ) : (
          <Chip>Apagadas</Chip>
        )}
      </div>

      <Apoyo className="medida">{texto} Llegan al teléfono aunque la app esté cerrada.</Apoyo>

      {actual === "no-soportado" ? (
        <Aviso tono="info" titulo="Este navegador no las admite">
          En iPhone hay que agregar la app a la pantalla de inicio para que funcionen. Mientras
          tanto los avisos importantes siguen llegando por correo.
        </Aviso>
      ) : actual === "bloqueado" ? (
        <Aviso tono="atencion" titulo="Las bloqueaste en este navegador">
          Desde aquí ya no se pueden volver a pedir. Hay que permitirlas en los ajustes del
          navegador para este sitio y recargar.
        </Aviso>
      ) : (
        <div>
          <Boton
            tono={actual === "activo" ? "contorno" : "solido"}
            cargando={trabajando}
            disabled={trabajando || actual === null}
            onClick={() => void alternar()}
          >
            {trabajando ? null : actual === "activo" ? (
              <BellOff className="size-4" />
            ) : (
              <Bell className="size-4" />
            )}
            {actual === "activo" ? "Desactivar" : "Activar notificaciones"}
          </Boton>
        </div>
      )}

      {error ? <Aviso tono="error">{error}</Aviso> : null}
    </section>
  );
}
