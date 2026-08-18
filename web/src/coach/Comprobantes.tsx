/** Bandeja de comprobantes por revisar.
 *
 *  Cada fila enseña lo que se esperaba cobrar junto a lo que leyó el OCR. El OCR no valida
 *  nada: un comprobante es una captura editable y la coach confirma contra su banco.
 */

import { AlertTriangle, Check, Loader2, X } from "lucide-react";
import { useState } from "react";

import { Dialogo } from "@/componentes/Dialogo";
import { Apoyo, Aviso, Boton, Campo, Chip, Etiqueta, Titulo } from "@/componentes/primitivas";
import {
  ErrorApi,
  api,
  urlDeComprobante,
  type ComprobantePorRevisarApi,
} from "@/lib/api";
import { fecha, num } from "@/lib/formato";
import { usarApi } from "@/lib/usarApi";

export function Comprobantes({ onCambio }: { onCambio: () => void }) {
  const carga = usarApi<ComprobantePorRevisarApi[]>((senal) => api.coach.comprobantes(senal));
  const [abierto, setAbierto] = useState<ComprobantePorRevisarApi | null>(null);

  const filas = carga.datos ?? [];
  if (carga.cargando || filas.length === 0) return null;

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <Titulo>Comprobantes por revisar</Titulo>
        <Chip tono="espera">{filas.length}</Chip>
      </div>
      <Apoyo>
        Confirma cada uno contra tu estado de cuenta. Al validarlo se registra el ingreso y el
        cobro deja de contar como adeudo.
      </Apoyo>

      <ul className="flex flex-col divide-y divide-linea border-y border-linea">
        {filas.map((c) => (
          <li key={c.cobroUlid} className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3">
            <span className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="flex flex-wrap items-center gap-2">
                <span className="text-menor font-medium">{c.alumna}</span>
                {c.montoNoCuadra ? (
                  <Chip tono="error">
                    <AlertTriangle className="mr-1 inline size-3" />
                    leyó ${num(c.montoLeido)}
                  </Chip>
                ) : null}
              </span>
              <span className="text-micro text-tinta-suave">
                {c.concepto} · {fecha(c.fechaCobro)}
                {c.banco ? ` · ${c.banco}` : ""}
                {c.referencia ? ` · ref ${c.referencia}` : ""}
              </span>
            </span>
            <span className="cifra font-semibold">${num(c.montoEsperado)}</span>
            <Boton medida="chica" onClick={() => setAbierto(c)}>
              Revisar
            </Boton>
          </li>
        ))}
      </ul>

      {abierto ? (
        <RevisarComprobante
          comprobante={abierto}
          onCerrar={() => setAbierto(null)}
          onResuelto={() => {
            setAbierto(null);
            carga.recargar();
            onCambio();
          }}
        />
      ) : null}
    </section>
  );
}

function RevisarComprobante({
  comprobante,
  onCerrar,
  onResuelto,
}: {
  comprobante: ComprobantePorRevisarApi;
  onCerrar: () => void;
  onResuelto: () => void;
}) {
  const [motivo, setMotivo] = useState("");
  const [rechazando, setRechazando] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function resolver(accion: "validar" | "rechazar") {
    setError(null);
    setOcupado(true);
    try {
      if (accion === "validar") await api.coach.validarComprobante(comprobante.cobroUlid);
      else await api.coach.rechazarComprobante(comprobante.cobroUlid, motivo.trim());
      onResuelto();
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : "No se pudo guardar.");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <Dialogo
      abierto
      onCambio={(v) => !v && onCerrar()}
      etiqueta="Comprobante"
      titulo={comprobante.alumna}
      descripcion={`${comprobante.concepto} · $${num(comprobante.montoEsperado)}`}
      pie={
        rechazando ? (
          <>
            <Boton tono="contorno" medida="chica" onClick={() => setRechazando(false)}>
              Volver
            </Boton>
            <Boton
              tono="peligro"
              medida="chica"
              disabled={ocupado || !motivo.trim()}
              onClick={() => void resolver("rechazar")}
            >
              Rechazar y avisar
            </Boton>
          </>
        ) : (
          <>
            <Boton tono="peligro" medida="chica" onClick={() => setRechazando(true)}>
              <X className="size-3.5" /> Rechazar
            </Boton>
            <Boton medida="chica" disabled={ocupado} onClick={() => void resolver("validar")}>
              {ocupado ? <Loader2 className="size-3.5 animate-spin" /> : <Check className="size-3.5" />}
              Validar pago
            </Boton>
          </>
        )
      }
    >
      {comprobante.montoNoCuadra ? (
        <Aviso tono="atencion" titulo="El importe leído no coincide">
          Esperabas ${num(comprobante.montoEsperado)} y la captura dice $
          {num(comprobante.montoLeido)}. Compruébalo contra tu estado de cuenta antes de
          validar.
        </Aviso>
      ) : null}

      {/* La imagen manda sobre lo que leyó el OCR: es lo único que la coach puede contrastar
          con su banco. */}
      <img
        src={urlDeComprobante(comprobante.cobroUlid)}
        alt={`Comprobante de ${comprobante.alumna}`}
        className="max-h-96 w-full rounded-marco border border-linea object-contain"
      />

      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-menor">
        {(
          [
            ["Esperado", `$${num(comprobante.montoEsperado)}`],
            ["Leído", comprobante.montoLeido !== null ? `$${num(comprobante.montoLeido)}` : "—"],
            ["Fecha leída", comprobante.fechaLeida ? fecha(comprobante.fechaLeida) : "—"],
            ["Banco", comprobante.banco ?? "—"],
            ["Referencia", comprobante.referencia ?? "—"],
            ["Confianza", `${Math.round(comprobante.confianza * 100)} %`],
          ] as const
        ).map(([rotulo, valor]) => (
          <div key={rotulo} className="flex items-baseline justify-between gap-2">
            <dt className="text-tinta-suave">{rotulo}</dt>
            <dd className="cifra font-medium">{valor}</dd>
          </div>
        ))}
      </dl>

      {rechazando ? (
        <Campo id="cp-motivo" etiqueta="¿Por qué lo rechazas?">
          <textarea
            id="cp-motivo"
            rows={3}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            placeholder="La captura está cortada y no se ve la referencia."
            className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
          />
        </Campo>
      ) : (
        <Apoyo>
          Validar registra el ingreso, salda el cobro y le avisa. Rechazar le devuelve el
          motivo tal como lo escribas.
        </Apoyo>
      )}

      {error ? <Aviso tono="error">{error}</Aviso> : null}
      <Etiqueta>El OCR solo sugiere: lo que vale es tu estado de cuenta.</Etiqueta>
    </Dialogo>
  );
}
