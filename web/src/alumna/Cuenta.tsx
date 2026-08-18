/** Cuenta de la alumna: perfil, privacidad y seguridad.
 *
 *  La privacidad va aquí y no escondida: la ley exige que ejercer los derechos ARCO sea
 *  accesible, y quien no encuentra dónde descargar sus fotos no tiene ese derecho.
 */

import { useState } from "react";
import { Link } from "react-router-dom";

import { Dialogo } from "@/componentes/Dialogo";
import { Notificaciones } from "@/componentes/Notificaciones";
import { InterruptorDeTema } from "@/componentes/Tema";
import { BotonSalir, CambiarContrasena } from "@/componentes/Seguridad";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Chip,
  Entrada,
  Etiqueta,
  Portada,
  Regla,
  Titulo,
} from "@/componentes/primitivas";
import {
  ErrorApi,
  api,
  descargarPdf,
  type CuestionarioApi,
  type InicioAlumnaApi,
} from "@/lib/api";
import { usarApi } from "@/lib/usarApi";

const CONSENTIMIENTOS = [
  ["Términos y Condiciones", "2.0", false, "/legal/terminos"],
  ["Aviso de Privacidad", "2.0", false, "/legal/privacidad"],
  ["Datos de salud", "2.0", true, "/legal/privacidad"],
  ["Protocolo fotográfico", "2.0", true, "/legal/privacidad"],
] as const;

const DERECHOS = [
  ["Acceso", "Quiero ver todo lo que tienen de mí"],
  ["Rectificación", "Hay un dato incorrecto"],
  ["Cancelación", "Quiero que borren mis datos"],
  ["Oposición", "No quiero un uso concreto"],
] as const;

export function Cuenta() {
  const [arco, setArco] = useState<string | null>(null);
  const [baja, setBaja] = useState(false);
  const [detalle, setDetalle] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState<string | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const inicio = usarApi<InicioAlumnaApi>((s) => api.alumna.inicio(s)).datos;
  const cuestionario = usarApi<CuestionarioApi>((s) => api.alumna.cuestionario(s)).datos;

  const perfil = inicio?.perfil;
  const salud = cuestionario?.nucleo;

  /** La solicitud va al hilo de su coach: bajo la ley, la Responsable es ella. */
  async function pedir(asunto: string, texto: string) {
    setFallo(null);
    setEnviando(true);
    try {
      await api.alumna.escribir(`${asunto}\n\n${texto.trim() || "Sin detalle."}`);
      setEnviado(asunto);
      setDetalle("");
      setArco(null);
      setBaja(false);
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo enviar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta>Tu cuenta</Etiqueta>
        <Portada>{perfil?.nombre ?? "Tu cuenta"}</Portada>
      </header>

      {enviado ? (
        <Aviso tono="exito" titulo="Se la mandamos a tu coach">
          «{enviado}» quedó en tu hilo de mensajes, con fecha.
        </Aviso>
      ) : null}

      {/* ---- Tema ---- */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <Titulo>Apariencia</Titulo>
          <Apoyo>De fábrica sigue a tu teléfono. Si prefieres uno fijo, elígelo aquí.</Apoyo>
        </div>
        <InterruptorDeTema className="w-fit" />
      </section>

      <Regla />

      {/* ---- Contacto ---- */}
      <section className="flex max-w-md flex-col gap-4">
        <Titulo>Datos de contacto</Titulo>
        <Campo id="cu-correo" etiqueta="Correo">
          <Entrada id="cu-correo" type="email" value={perfil?.correo ?? ""} readOnly />
        </Campo>
        <Apoyo>Para cambiarlos, escríbele a tu coach: es ella quien los tiene.</Apoyo>
      </section>

      <Regla />

      <Notificaciones para="alumna" />

      <Regla />

      {/* ---- Rutina de chequeo ---- */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <Titulo>Tu rutina de chequeo</Titulo>
          <Apoyo>Se precargan cada mes. Cámbialas solo si de verdad cambió algo.</Apoyo>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <Campo id="cu-bascula" etiqueta="Báscula">
            <Entrada id="cu-bascula" value={perfil?.basculaRef ?? ""} readOnly />
          </Campo>
          <Campo id="cu-lugar" etiqueta="Lugar de las fotos">
            <Entrada id="cu-lugar" value={perfil?.lugarRef ?? ""} readOnly />
          </Campo>
          <Campo id="cu-hora" etiqueta="Hora">
            <Entrada id="cu-hora" value={perfil?.horaRef ?? ""} readOnly />
          </Campo>
        </div>
        <Apoyo>Se toman de tu último chequeo. Si cambió algo, dilo al hacer el siguiente.</Apoyo>
      </section>

      <Regla />

      {/* ---- Salud ---- */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Titulo>Tu historial de salud</Titulo>
          <Chip tono="espera">Dato sensible</Chip>
        </div>
        <Apoyo>
          Es lo que contestaste en tu cuestionario. De esto depende que tu plan sea seguro: si
          cambió algo, díselo a tu coach para que lo actualice.
        </Apoyo>
        <div className="grid gap-4 sm:grid-cols-2">
          {(
            [
              ["Lesiones", salud?.lesiones],
              ["Condiciones médicas", salud?.condiciones],
              ["Medicación", salud?.medicacion],
              ["Alergias y restricciones", salud?.restricciones],
            ] as const
          ).map(([rotulo, valor]) => (
            <Campo key={rotulo} id={`cu-${rotulo}`} etiqueta={rotulo}>
              <textarea
                id={`cu-${rotulo}`}
                value={valor ?? ""}
                readOnly
                rows={3}
                className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
              />
            </Campo>
          ))}
        </div>
      </section>

      <Regla />

      {/* ---- Privacidad ---- */}
      <section className="flex flex-col gap-5">
        <Titulo>Privacidad</Titulo>

        <div className="flex flex-col gap-2">
          <Etiqueta>Lo que aceptaste</Etiqueta>
          <ul className="flex flex-col divide-y divide-linea border-y border-linea">
            {CONSENTIMIENTOS.map(([titulo, version, sensible, ruta]) => (
              <li key={titulo} className="flex flex-wrap items-center gap-3 py-3">
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link to={ruta} className="text-menor font-medium underline underline-offset-2">
                      {titulo}
                    </Link>
                    {sensible ? <Chip tono="espera">Sensible</Chip> : null}
                  </div>
                  <Apoyo>Versión {version}</Apoyo>
                </div>
                {(cuestionario?.consentimientosPendientes ?? []).length > 0 ? (
                  <Chip tono="espera">Pendiente</Chip>
                ) : (
                  <Chip tono="exito">Aceptado</Chip>
                )}
              </li>
            ))}
          </ul>
          <Apoyo>
            Guardamos la fecha, la hora y el hash del texto exacto que aceptaste. Para revocar
            uno, escríbele a tu coach: revocar el protocolo fotográfico impide que genere o
            ajuste tu plan.
          </Apoyo>
        </div>

        <div className="grid gap-6 sm:grid-cols-2">
          <div className="flex flex-col gap-3">
            <Etiqueta>Tus fotos</Etiqueta>
            <Apoyo>
              Se guardan cifradas, del cuello para abajo, y se borran solas a los 4 meses. Te
              avisamos 15 días antes de cada purga.
            </Apoyo>
            <div>
              <Boton
                tono="contorno"
                medida="chica"
                onClick={() => void descargarPdf("/documentos/evolucion", "mi-evolucion.pdf")}
              >
                Descargar mi expediente
              </Boton>
            </div>
            <Apoyo>
              El PDF lleva tus medidas y tu peso. Las fotos se ven en Evolución: no salen de la
              plataforma, que es lo que permite borrarlas a los 4 meses.
            </Apoyo>
          </div>

          <div className="flex flex-col gap-3">
            <Etiqueta>Tus derechos ARCO</Etiqueta>
            <Apoyo>Tienes respuesta en 20 días hábiles y ejecución en 15 más.</Apoyo>
            <div className="flex flex-wrap gap-2">
              {DERECHOS.map(([derecho]) => (
                <Boton key={derecho} tono="contorno" medida="chica" onClick={() => setArco(derecho)}>
                  {derecho}
                </Boton>
              ))}
            </div>
          </div>
        </div>
      </section>

      <Regla />

      <CambiarContrasena />

      <Regla />

      {/* ---- Baja ---- */}
      <section className="flex flex-col gap-4 border-l-2 border-l-peligro pl-4">
        <Titulo>Darme de baja</Titulo>
        <Apoyo>
          Se borra todo: fotos, medidas e historial clínico. Descarga antes lo que quieras
          conservar, porque después no se puede recuperar.
        </Apoyo>
        <div className="flex flex-wrap gap-2">
          <Boton tono="peligro" onClick={() => setBaja(true)}>
            Quiero darme de baja
          </Boton>
          <BotonSalir />
        </div>
      </section>

      {/* ---- Diálogos ---- */}
      {arco ? (
        <Dialogo
          abierto
          onCambio={(v) => !v && setArco(null)}
          etiqueta={`Derecho de ${arco}`}
          titulo="Cuéntanos qué necesitas"
          pie={
            <>
              <Boton tono="contorno" medida="chica" onClick={() => setArco(null)}>
                Cancelar
              </Boton>
              <Boton
                medida="chica"
                disabled={enviando}
                onClick={() => void pedir(`Derecho de ${arco}`, detalle)}
              >
                {enviando ? "Enviando…" : "Enviar solicitud"}
              </Boton>
            </>
          }
        >
          <Campo id="arco-detalle" etiqueta="Detalle">
            <textarea
              id="arco-detalle"
              rows={3}
              value={detalle}
              onChange={(e) => setDetalle(e.target.value)}
              className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
              placeholder="Explica brevemente tu solicitud"
            />
          </Campo>
          <Apoyo>
            Se manda al hilo de tu coach, que es quien responde por tus datos. Queda con fecha
            y tienes respuesta en 20 días hábiles.
          </Apoyo>
          {fallo ? <Aviso tono="error">{fallo}</Aviso> : null}
        </Dialogo>
      ) : null}

      {baja ? (
        <Dialogo
          abierto
          onCambio={(v) => !v && setBaja(false)}
          etiqueta="Baja definitiva"
          titulo="Esto no se puede deshacer"
          pie={
            <>
              <Boton tono="contorno" medida="chica" onClick={() => setBaja(false)}>
                Mejor no
              </Boton>
              <Boton
                tono="peligro"
                medida="chica"
                disabled={enviando}
                onClick={() => void pedir("Solicitud de baja definitiva", detalle)}
              >
                {enviando ? "Enviando…" : "Pedir mi baja"}
              </Boton>
            </>
          }
        >
          <Apoyo>
            Se borran tus fotos, tus medidas, tu peso y tu historial clínico. Solo se conserva
            el registro de movimientos, con tu identificador anonimizado, por obligación legal.
          </Apoyo>
          <Aviso tono="error">
            Si quieres conservar algo, descárgalo antes de pedirla.
          </Aviso>
          <Apoyo>La solicitud le llega a tu coach, que la procesa y te confirma.</Apoyo>
          {fallo ? <Aviso tono="error">{fallo}</Aviso> : null}
        </Dialogo>
      ) : null}
    </div>
  );
}
