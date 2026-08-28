/** Dar de baja a una alumna. No se puede deshacer, y la pantalla lo trata así.
 *
 *  Tres cosas antes del botón: lo que debe, lo que se va a borrar y cuándo. Y para
 *  confirmar hay que teclear su nombre, que es lo único que evita darle de baja a otra por
 *  tocar la fila de al lado.
 */

import {  } from "lucide-react";
import { useState } from "react";

import { Dialogo } from "@/componentes/Dialogo";
import { Apoyo, Aviso, Boton, Campo, Entrada } from "@/componentes/primitivas";
import { ErrorApi, api, type AvisoDeBajaApi, type FilaCarteraApi } from "@/lib/api";
import { fecha, num } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
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
  const { t } = useIdioma();
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
      setFallo(causa instanceof ErrorApi ? causa.message : t("No se pudo dar de baja."));
    } finally {
      setOcupado(false);
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta={t("No se puede deshacer")}
      titulo={t("Dar de baja a {nombre}", { nombre: alumna.nombre })}
      pie={
        <>
          <Boton tono="contorno" medida="chica" onClick={onCerrar}>
            {t("Cancelar")}
          </Boton>
          <Boton
            tono="peligro"
            medida="chica"
            cargando={ocupado}
            disabled={ocupado || !escrito.trim() || carga.cargando}
            onClick={() => void confirmar()}
          >
            {t("Dar de baja")}
          </Boton>
        </>
      }
    >
      {carga.cargando ? <Apoyo>{t("Un momento…")}</Apoyo> : null}
      {carga.error ? <Aviso tono="error">{carga.error.message}</Aviso> : null}

      {aviso ? (
        <>
          {aviso.cobrosVencidos > 0 ? (
            <Aviso tono="atencion" titulo={t("Te debe {monto}", { monto: `$${num(aviso.adeudo)}` })}>
              {aviso.cobrosVencidos === 1
                ? t("Son {n} cobro vencido. Darla de baja no los cobra ni los cancela: decídelo tú antes de seguir.", {
                    n: 1,
                  })
                : t("Son {n} cobros vencidos. Darla de baja no los cobra ni los cancela: decídelo tú antes de seguir.", {
                    n: aviso.cobrosVencidos,
                  })}
            </Aviso>
          ) : null}

          <Apoyo>
            {t("Sale de tu cartera hoy y deja de tener servicio. Conserva")}{" "}
            <strong className="font-medium">{t("quince días de solo lectura")}</strong>{" "}
            {t("para descargar lo suyo, y le mandamos su expediente en PDF.")}
          </Apoyo>

          <Aviso tono="error" titulo={t("El {fecha} se borra todo", { fecha: fecha(aviso.borrariaEl) })}>
            {aviso.chequeos > 0 ? (
              <>
                {t("Sus {n} chequeos con sus fotos y medidas,", { n: aviso.chequeos })}{" "}
              </>
            ) : null}
            {t(
              "su historial clínico, sus respuestas, sus mensajes y su cuenta con su correo. Lo único que se queda es el dinero, sin su nombre, para que tu contabilidad cuadre.",
            )}
          </Aviso>

          <Campo
            id="ba-nombre"
            etiqueta={t("Escribe su nombre para confirmar")}
            ayuda={t("Tal como aparece: {nombre}", { nombre: aviso.nombre })}
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
