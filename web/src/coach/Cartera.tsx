/** Cartera de alumnas: una por fila, con lo que decide si hay que abrirla.
 *
 *  La vía rápida es el buscador global (⌘K). En teléfono se apila; no hay tabla que
 *  desplazar en horizontal.
 */

import { useState } from "react";
import { Link } from "react-router-dom";

import { AvisoSinServidor, CargandoPantalla } from "@/componentes/Estado";
import { DarDeBaja } from "@/coach/DarDeBaja";
import { FormAlumna, FormClaveTemporal } from "@/coach/FormAlumna";
import { LigaDeRegistro } from "@/coach/LigaDeRegistro";
import {
  Apoyo,
  Boton,
  Chip,
  Entrada,
  Etiqueta,
  Portada,
  Regla,
  Vacio,
} from "@/componentes/primitivas";
import { api, type FilaCarteraApi } from "@/lib/api";
import { cartera as carteraEjemplo, coach } from "@/lib/datos";
import { delta, fecha, num } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
import { usarApiConRespaldo } from "@/lib/usarApi";
import { ROTULO_ESTADO, type EstadoChequeo } from "@/lib/tipos";

const TONO_ESTADO: Record<EstadoChequeo, "neutro" | "espera" | "exito" | "error"> = {
  borrador: "neutro",
  pendiente_evaluacion: "espera",
  validado: "exito",
  rechazado_calidad: "error",
  descartado: "neutro",
};

export function Cartera() {
  const { t } = useIdioma();
  const [filtro, setFiltro] = useState("");
  const [editando, setEditando] = useState<FilaCarteraApi | null>(null);
  const [dandoDeAlta, setDandoDeAlta] = useState(false);
  const [recuperando, setRecuperando] = useState<FilaCarteraApi | null>(null);
  const [dandoDeBaja, setDandoDeBaja] = useState<FilaCarteraApi | null>(null);
  const { datos: alumnas, cargando, sinServidor, mensaje, recargar } = usarApiConRespaldo<FilaCarteraApi[]>(
    (senal) => api.coach.alumnas(senal),
    carteraEjemplo,
  );

  if (cargando) return <CargandoPantalla que={t("tus alumnas")} filas={6} />;

  const visibles = alumnas.filter((a) =>
    `${a.nombre} ${a.plan ?? ""}`
      .toLowerCase()
      .includes(filtro.trim().toLowerCase()),
  );

  return (
    <div className="flex flex-col gap-10">
      {sinServidor ? <AvisoSinServidor mensaje={mensaje} /> : null}

      <header className="flex flex-col gap-3">
        <Etiqueta>
          {t("{n} alumnas · límite {m}", { n: alumnas.length, m: coach.limiteAlumnas })}
        </Etiqueta>
        <Portada>{t("Mis pacientes")}</Portada>
      </header>

      <LigaDeRegistro />

      <Regla />

      <div className="flex flex-wrap items-center gap-3">
        <Entrada
          type="search"
          placeholder={t("Filtrar por nombre…")}
          value={filtro}
          onChange={(e) => setFiltro(e.target.value)}
          className="max-w-xs"
          aria-label={t("Filtrar alumnas")}
        />
        <Apoyo className="hidden lg:block">{t("O pulsa ⌘K para buscar en todo.")}</Apoyo>
        <Boton className="ml-auto" onClick={() => setDandoDeAlta(true)}>
          {t("Dar de alta")}
        </Boton>
      </div>

      {visibles.length === 0 ? (
        <Vacio>{t("Ninguna alumna con ese nombre.")}</Vacio>
      ) : (
        <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
          {visibles.map((a) => {
            const d = a.pesoKg !== null && a.pesoPrevio !== null ? delta(a.pesoKg, a.pesoPrevio, "kg") : null;
            return (
              <li key={a.ulid} className="flex flex-col gap-3 py-5 sm:flex-row sm:items-center sm:gap-6">
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-guia font-medium">{a.nombre}</span>
                    {a.estado === "pausa" ? <Chip>{t("En pausa")}</Chip> : null}
                    {a.pago === "pendiente" ? <Chip tono="espera">{t("Pago pendiente")}</Chip> : null}
                  </div>
                  <Apoyo>
                    {t("Ciclo {ciclo}", { ciclo: a.ciclo })}
                    {a.plan
                      ? ` · ${a.plan}`
                      : ""}
                    {a.ultimoAcceso
                      ? ` · ${t("último acceso {fecha}", {
                          fecha: fecha(a.ultimoAcceso, { day: "numeric", month: "short" }),
                        })}`
                      : ""}
                  </Apoyo>
                </div>

                <div className="flex items-center gap-6">
                  <div className="flex min-w-20 flex-col">
                    <span className="text-micro uppercase tracking-[0.08em] text-tinta-suave">{t("Peso")}</span>
                    <span className="cifra text-cuerpo font-semibold">
                      {a.pesoKg !== null ? `${num(a.pesoKg)} kg` : "—"}
                    </span>
                    {d ? <span className="cifra text-micro text-tinta-media">{d.texto}</span> : null}
                  </div>

                  <div className="min-w-28">
                    {a.chequeoEstado ? (
                      <Chip tono={TONO_ESTADO[a.chequeoEstado as EstadoChequeo]}>
                        {t(ROTULO_ESTADO[a.chequeoEstado as EstadoChequeo])}
                      </Chip>
                    ) : (
                      <span className="text-menor text-tinta-suave">{t("Sin chequeo")}</span>
                    )}
                  </div>

                  <div className="ml-auto flex shrink-0 items-center gap-1">
                    <Boton tono="discreto" medida="chica" onClick={() => setEditando(a)}>
                      {t("Editar")}
                    </Boton>
                    <Boton tono="discreto" medida="chica" onClick={() => setRecuperando(a)}>
                      {t("Clave")}
                    </Boton>
                    <Boton
                      tono="discreto"
                      medida="chica"
                      className="text-peligro"
                      onClick={() => setDandoDeBaja(a)}
                    >
                      {t("Baja")}
                    </Boton>
                    <Boton asChild tono="discreto" medida="chica">
                      <Link to={`/coach/mensajes/${a.ulid}`}>{t("Mensajes")}</Link>
                    </Boton>
                    {/* Lleva a lo que toca hacer con ella, no a un expediente genérico. */}
                    <Boton asChild tono="contorno" medida="chica">
                      <Link
                        to={
                          a.chequeoEstado === "pendiente_evaluacion"
                            ? `/coach/validar/${a.ulid}`
                            : `/coach/plan/${a.ulid}`
                        }
                      >
                        {a.chequeoEstado === "pendiente_evaluacion" ? t("Revisar") : t("Plan")}
                      </Link>
                    </Boton>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {dandoDeAlta || editando ? (
        <FormAlumna
          alumna={editando}
          onCerrar={() => {
            setDandoDeAlta(false);
            setEditando(null);
          }}
          onGuardada={recargar}
        />
      ) : null}

      {recuperando ? (
        <FormClaveTemporal alumna={recuperando} onCerrar={() => setRecuperando(null)} />
      ) : null}

      {dandoDeBaja ? (
        <DarDeBaja
          alumna={dandoDeBaja}
          onCerrar={() => setDandoDeBaja(null)}
          onHecho={() => {
            setDandoDeBaja(null);
            recargar();
          }}
        />
      ) : null}
    </div>
  );
}
