/** Dar de baja a una alumna. No se puede deshacer, y la pantalla lo trata así.
 *
 *  Tres cosas antes del botón: lo que debe, lo que se va a borrar y cuándo. Y para
 *  confirmar hay que teclear su nombre, que es lo único que evita darle de baja a otra por
 *  tocar la fila de al lado.
 */

import { Loader2 } from "lucide-react";
import { useState } from "react";

import { Dialogo } from "@/componentes/Dialogo";
import { Apoyo, Aviso, Boton, Campo, Entrada } from "@/componentes/primitivas";
import { ErrorApi, api, type AvisoDeBajaApi, type FilaCarteraApi } from "@/lib/api";
import { fecha, num } from "@/lib/formato";
import { usarApi } from "@/lib/usarApi";

export function DarDeBaja({
  alumna,
  onCerrar,
  onHecho,
}: {
  alumna: FilaCarteraApi;
  onCerrar: () => void;
  onHecho: () => void;
}) {
  const carga = usarApi<AvisoDeBajaApi>(
    (s) => api.coach.revisarBaja(alumna.ulid, s),
    [alumna.ulid],
  );
  const [escrito, setEscrito] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);

  const aviso = carga.datos;

  async function confirmar() {
    setFallo(null);
    setOcupado(true);
    try {
      await api.coach.darDeBaja(alumna.ulid, escrito.trim());
      onHecho();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo dar de baja.");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta="No se puede deshacer"
      titulo={`Dar de baja a ${alumna.nombre}`}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton
            tono="peligro"
            medida="chica"
            disabled={ocupado || !escrito.trim() || carga.cargando}
            onClick={() => void confirmar()}
          >
            {ocupado ? <Loader2 className="size-3.5 animate-spin" /> : null}
            Dar de baja
          </Boton>
        </>
      }
    >
      {carga.cargando ? <Apoyo>Un momento…</Apoyo> : null}
      {carga.error ? <Aviso tono="error">{carga.error.message}</Aviso> : null}

      {aviso ? (
        <>
          {aviso.cobrosVencidos > 0 ? (
            <Aviso tono="atencion" titulo={`Te debe $${num(aviso.adeudo)}`}>
              Son {aviso.cobrosVencidos}{" "}
              {aviso.cobrosVencidos === 1 ? "cobro vencido" : "cobros vencidos"}. Darla de
              baja no los cobra ni los cancela: decídelo tú antes de seguir.
            </Aviso>
          ) : null}

          <Apoyo>
            Sale de tu cartera hoy y deja de tener servicio. Conserva {""}
            <strong className="font-medium">quince días de solo lectura</strong> para
            descargar lo suyo, y le mandamos su expediente en PDF.
          </Apoyo>

          <Aviso tono="error" titulo={`El ${fecha(aviso.borrariaEl)} se borra todo`}>
            {aviso.chequeos > 0
              ? `Sus ${aviso.chequeos} chequeos con sus fotos y medidas, `
              : ""}
            su historial clínico, sus respuestas, sus mensajes y su cuenta con su correo. Lo
            único que se queda es el dinero, sin su nombre, para que tu contabilidad cuadre.
          </Aviso>

          <Campo
            id="ba-nombre"
            etiqueta="Escribe su nombre para confirmar"
            ayuda={`Tal como aparece: ${aviso.nombre}`}
          >
            <Entrada
              id="ba-nombre"
              value={escrito}
              onChange={(e) => setEscrito(e.target.value)}
              placeholder={aviso.nombre}
              autoComplete="off"
            />
          </Campo>
        </>
      ) : null}

      {fallo ? <Aviso tono="error">{fallo}</Aviso> : null}
    </Dialogo>
  );
}
