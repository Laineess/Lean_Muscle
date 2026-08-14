/** Cuenta de la alumna: perfil, privacidad y seguridad.
 *
 *  La privacidad va aquí y no escondida en un menú: la ley exige que los medios para
 *  ejercer derechos ARCO y limitar el uso de los datos sean accesibles, y una alumna que no
 *  encuentra dónde descargar sus fotos no tiene realmente ese derecho.
 */

import { useState } from "react";

import { Dialogo } from "@/componentes/Dialogo";
import { Notificaciones } from "@/componentes/Notificaciones";
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
import { alumna, historialClinico } from "@/lib/datos";
import { fecha } from "@/lib/formato";

const CONSENTIMIENTOS = [
  ["Términos y Condiciones", "2.0", false],
  ["Aviso de Privacidad", "2.0", false],
  ["Datos de salud", "2.0", true],
  ["Protocolo fotográfico", "2.0", true],
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

  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta>Tu cuenta</Etiqueta>
        <Portada>{alumna.nombre}</Portada>
      </header>

      {/* ---- Contacto ---- */}
      <section className="flex max-w-md flex-col gap-4">
        <Titulo>Datos de contacto</Titulo>
        <Campo id="cu-correo" etiqueta="Correo">
          <Entrada id="cu-correo" type="email" defaultValue={alumna.email} />
        </Campo>
        <Campo id="cu-wa" etiqueta="WhatsApp">
          <Entrada id="cu-wa" type="tel" defaultValue={alumna.whatsapp} />
        </Campo>
        <div>
          <Boton tono="contorno">Guardar</Boton>
        </div>
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
            <Entrada id="cu-bascula" defaultValue={alumna.basculaRef} />
          </Campo>
          <Campo id="cu-lugar" etiqueta="Lugar de las fotos">
            <Entrada id="cu-lugar" defaultValue={alumna.lugarRef} />
          </Campo>
          <Campo id="cu-hora" etiqueta="Hora">
            <Entrada id="cu-hora" defaultValue={alumna.horaRef} />
          </Campo>
        </div>
        <div>
          <Boton tono="contorno">Guardar</Boton>
        </div>
      </section>

      <Regla />

      {/* ---- Salud ---- */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Titulo>Tu historial de salud</Titulo>
          <Chip tono="espera">Dato sensible</Chip>
        </div>
        <Apoyo>
          Vigente desde el {fecha(historialClinico.vigenteDesde)}. Al editarlo se guarda una
          versión nueva —no se borra la anterior— y tu coach recibe aviso. De esto depende que
          tu plan sea seguro.
        </Apoyo>
        <div className="grid gap-4 sm:grid-cols-2">
          {(
            [
              ["Lesiones", historialClinico.lesiones],
              ["Condiciones médicas", historialClinico.condiciones],
              ["Medicación", historialClinico.medicacion],
              ["Alergias y restricciones", historialClinico.restricciones],
            ] as const
          ).map(([rotulo, valor]) => (
            <Campo key={rotulo} id={`cu-${rotulo}`} etiqueta={rotulo}>
              <textarea
                id={`cu-${rotulo}`}
                defaultValue={valor}
                rows={3}
                className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
              />
            </Campo>
          ))}
        </div>
        <div>
          <Boton>Guardar versión nueva</Boton>
        </div>
      </section>

      <Regla />

      {/* ---- Privacidad ---- */}
      <section className="flex flex-col gap-5">
        <Titulo>Privacidad</Titulo>

        <div className="flex flex-col gap-2">
          <Etiqueta>Lo que aceptaste</Etiqueta>
          <ul className="flex flex-col divide-y divide-linea border-y border-linea">
            {CONSENTIMIENTOS.map(([titulo, version, sensible]) => (
              <li key={titulo} className="flex flex-wrap items-center gap-3 py-3">
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-menor font-medium">{titulo}</span>
                    {sensible ? <Chip tono="espera">Sensible</Chip> : null}
                  </div>
                  <Apoyo>Versión {version} · aceptado el 2 de mayo de 2026</Apoyo>
                </div>
                <Boton tono="discreto" medida="chica">
                  Revocar
                </Boton>
              </li>
            ))}
          </ul>
          <Apoyo>
            Guardamos la fecha, la hora y el hash del texto exacto que aceptaste. Revocar el
            protocolo fotográfico impide que tu coach genere o ajuste tu plan.
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
              <Boton tono="contorno" medida="chica">
                Descargar todas mis fotos
              </Boton>
            </div>
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
              <Boton medida="chica" onClick={() => setArco(null)}>
                Enviar solicitud
              </Boton>
            </>
          }
        >
          <Campo id="arco-detalle" etiqueta="Detalle">
            <textarea
              id="arco-detalle"
              rows={3}
              className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
              placeholder="Explica brevemente tu solicitud"
            />
          </Campo>
          <Apoyo>Se registra con fecha. Tienes respuesta en 20 días hábiles.</Apoyo>
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
              <Boton tono="peligro" medida="chica" onClick={() => setBaja(false)}>
                Darme de baja
              </Boton>
            </>
          }
        >
          <Apoyo>
            Se borran tus fotos, tus medidas, tu peso y tu historial clínico. Solo se conserva
            el registro de movimientos, con tu identificador anonimizado, por obligación legal.
          </Apoyo>
          <Aviso tono="error">
            Si quieres conservar algo, descárgalo antes de confirmar.
          </Aviso>
        </Dialogo>
      ) : null}
    </div>
  );
}
