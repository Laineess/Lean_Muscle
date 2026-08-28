/** Cuenta de la alumna: perfil, privacidad y seguridad.
 *
 *  La privacidad va aquí y no escondida: la ley exige que ejercer los derechos ARCO sea
 *  accesible, y quien no encuentra dónde descargar sus fotos no tiene ese derecho.
 */

import { AtSign, ClipboardList, Download, HeartPulse, Palette, ShieldCheck } from "lucide-react";
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
  type SolicitudArcoApi,
} from "@/lib/api";
import { fecha } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
import { usarApi } from "@/lib/usarApi";

const CONSENTIMIENTOS = [
  ["Términos y Condiciones", "2.0", false, "/legal/terminos"],
  ["Aviso de Privacidad", "2.0", false, "/legal/privacidad"],
  ["Datos de salud", "2.0", true, "/legal/privacidad"],
  ["Protocolo fotográfico", "2.0", true, "/legal/privacidad"],
] as const;

const DERECHOS = [
  ["Acceso", "Quiero ver todo lo que tienen de mí", "A"],
  ["Rectificación", "Hay un dato incorrecto", "R"],
  ["Cancelación", "Quiero que borren mis datos", "C"],
  ["Oposición", "No quiero un uso concreto", "O"],
] as const;

export function Cuenta() {
  const { t } = useIdioma();
  const [arco, setArco] = useState<string | null>(null);
  const [baja, setBaja] = useState(false);
  const [detalle, setDetalle] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState<string | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const inicio = usarApi<InicioAlumnaApi>((s) => api.alumna.inicio(s)).datos;
  const cuestionario = usarApi<CuestionarioApi>((s) => api.alumna.cuestionario(s)).datos;
  const solicitudes = usarApi<SolicitudArcoApi[]>((s) => api.alumna.arco(s), []);

  const perfil = inicio?.perfil;
  const salud = cuestionario?.nucleo;

  /** Queda registrada con su plazo. La Responsable es la coach, no la plataforma. */
  async function pedir(derecho: string, texto: string) {
    setFallo(null);
    setEnviando(true);
    try {
      await api.alumna.ejercerDerecho(derecho, texto);
      setEnviado(DERECHOS.find(([, , d]) => d === derecho)?.[0] ?? "Solicitud");
      setDetalle("");
      setArco(null);
      setBaja(false);
      solicitudes.recargar();
    } catch (causa) {
      setFallo(causa instanceof ErrorApi ? causa.message : "No se pudo enviar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-3">
        <Etiqueta>{t("Tu cuenta")}</Etiqueta>
        <Portada>{perfil?.nombre ?? t("Tu cuenta")}</Portada>
      </header>

      {enviado ? (
        <Aviso tono="exito" titulo={t("Solicitud registrada")}>
          {t("«{rotulo}» quedó con fecha. Tu coach tiene 20 días hábiles para contestarte.", {
            rotulo: t(enviado ?? ""),
          })}
        </Aviso>
      ) : null}

      {/* ---- Tema ---- */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <Titulo icono={Palette}>{t("Apariencia")}</Titulo>
          <Apoyo>{t("De fábrica sigue a tu teléfono. Si prefieres uno fijo, elígelo aquí.")}</Apoyo>
        </div>
        <InterruptorDeTema className="w-fit" />
      </section>

      <Regla />

      {/* ---- Contacto ---- */}
      <section className="flex max-w-md flex-col gap-4">
        <Titulo icono={AtSign}>{t("Datos de contacto")}</Titulo>
        <Campo id="cu-correo" etiqueta={t("Correo")}>
          <Entrada id="cu-correo" type="email" value={perfil?.correo ?? ""} readOnly />
        </Campo>
        <Apoyo>{t("Para cambiarlos, escríbele a tu coach: es ella quien los tiene.")}</Apoyo>
      </section>

      <Regla />

      <Notificaciones para="alumna" />

      <Regla />

      {/* ---- Rutina de chequeo ---- */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <Titulo icono={ClipboardList}>{t("Tu rutina de chequeo")}</Titulo>
          <Apoyo>{t("Se precargan cada mes. Cámbialas solo si de verdad cambió algo.")}</Apoyo>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <Campo id="cu-bascula" etiqueta={t("Báscula")}>
            <Entrada id="cu-bascula" value={perfil?.basculaRef ?? ""} readOnly />
          </Campo>
          <Campo id="cu-lugar" etiqueta={t("Lugar de las fotos")}>
            <Entrada id="cu-lugar" value={perfil?.lugarRef ?? ""} readOnly />
          </Campo>
          <Campo id="cu-hora" etiqueta={t("Hora")}>
            <Entrada id="cu-hora" value={perfil?.horaRef ?? ""} readOnly />
          </Campo>
        </div>
        <Apoyo>{t("Se toman de tu último chequeo. Si cambió algo, dilo al hacer el siguiente.")}</Apoyo>
      </section>

      <Regla />

      {/* ---- Salud ---- */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Titulo icono={HeartPulse}>{t("Tu historial de salud")}</Titulo>
          <Chip tono="espera">{t("Dato sensible")}</Chip>
        </div>
        <Apoyo>{t("Es lo que contestaste en tu cuestionario. De esto depende que tu plan sea seguro: si cambió algo, díselo a tu coach para que lo actualice.")}</Apoyo>
        <div className="grid gap-4 sm:grid-cols-2">
          {(
            [
              ["Lesiones", salud?.lesiones],
              ["Condiciones médicas", salud?.condiciones],
              ["Medicación", salud?.medicacion],
              ["Alergias y restricciones", salud?.restricciones],
            ] as const
          ).map(([rotulo, valor]) => (
            <Campo key={rotulo} id={`cu-${rotulo}`} etiqueta={t(rotulo)}>
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
        <Titulo icono={ShieldCheck}>{t("Privacidad")}</Titulo>

        <div className="flex flex-col gap-2">
          <Etiqueta>{t("Lo que aceptaste")}</Etiqueta>
          <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
            {CONSENTIMIENTOS.map(([titulo, version, sensible, ruta]) => (
              <li key={titulo} className="flex flex-wrap items-center gap-3 py-3">
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link to={ruta} className="text-menor font-medium underline underline-offset-2">
                      {t(titulo)}
                    </Link>
                    {sensible ? <Chip tono="espera">{t("Sensible")}</Chip> : null}
                  </div>
                  <Apoyo>{t("Versión {version}", { version })}</Apoyo>
                </div>
                {(cuestionario?.consentimientosPendientes ?? []).length > 0 ? (
                  <Chip tono="espera">{t("Pendiente")}</Chip>
                ) : (
                  <Chip tono="exito">{t("Aceptado")}</Chip>
                )}
              </li>
            ))}
          </ul>
          <Apoyo>{t("Guardamos la fecha, la hora y el hash del texto exacto que aceptaste. Para revocar uno, escríbele a tu coach: revocar el protocolo fotográfico impide que genere o ajuste tu plan.")}</Apoyo>
        </div>

        <div className="grid gap-6 sm:grid-cols-2">
          <div className="flex flex-col gap-3">
            <Etiqueta>{t("Tus fotos")}</Etiqueta>
            <Apoyo>{t("Se guardan cifradas y del cuello para abajo. A los 4 meses se borran, menos tu primera y tu última de cada ángulo, que se quedan para tu comparativa.")}</Apoyo>
            <div className="flex flex-wrap gap-2">
              <Boton asChild tono="contorno" medida="chica">
                <a href="/api/documentos/expediente" download>
                  <Download className="size-3.5" /> {t("Descargar todo")}
                </a>
              </Boton>
              <Boton
                tono="discreto"
                medida="chica"
                onClick={() => void descargarPdf("/documentos/evolucion", "mi-evolucion.pdf")}
              >
                {t("Solo el historial")}
              </Boton>
            </div>
            <Apoyo>{t("«Descargar todo» trae tus fotos y tu historial en un ZIP. El historial suelto es un PDF con tus medidas y tu peso.")}</Apoyo>
          </div>

          <div className="flex flex-col gap-3">
            <Etiqueta>{t("Tus derechos ARCO")}</Etiqueta>
            <Apoyo>{t("Tienes respuesta en 20 días hábiles y ejecución en 15 más.")}</Apoyo>
            <SolicitudesArco filas={solicitudes.datos ?? []} />
            <div className="flex flex-wrap gap-2">
              {DERECHOS.map(([derecho, , clave]) => (
                <Boton key={derecho} tono="contorno" medida="chica" onClick={() => setArco(clave)}>
                  {t(derecho)}
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
        <Titulo>{t("Darme de baja")}</Titulo>
        <Apoyo>{t("Se borra todo: fotos, medidas e historial clínico. Descarga antes lo que quieras conservar, porque después no se puede recuperar.")}</Apoyo>
        <div className="flex flex-wrap gap-2">
          <Boton tono="peligro" onClick={() => setBaja(true)}>
            {t("Quiero darme de baja")}
          </Boton>
          <BotonSalir />
        </div>
      </section>

      {/* ---- Diálogos ---- */}
      {arco ? (
        <Dialogo
          abierto
          onCambio={(v) => !v && setArco(null)}
          etiqueta={t("Derecho de {codigo}", { codigo: arco })}
          titulo={t("Cuéntanos qué necesitas")}
          pie={
            <>
              <Boton tono="contorno" medida="chica" onClick={() => setArco(null)}>
                {t("Cancelar")}
              </Boton>
              <Boton
                medida="chica"
                disabled={enviando}
                onClick={() => void pedir(`Derecho de ${arco}`, detalle)}
              >
                {enviando ? t("Enviando…") : t("Enviar solicitud")}
              </Boton>
            </>
          }
        >
          <Campo id="arco-detalle" etiqueta={t("Detalle")}>
            <textarea
              id="arco-detalle"
              rows={3}
              value={detalle}
              onChange={(e) => setDetalle(e.target.value)}
              className="w-full rounded-marco border border-linea bg-fondo px-3 py-2 text-cuerpo leading-relaxed focus:border-tinta focus:outline-none"
              placeholder={t("Explica brevemente tu solicitud")}
            />
          </Campo>
          <Apoyo>{t("Le llega a tu coach, que es quien responde por tus datos. Queda con fecha y tienes respuesta en 20 días hábiles.")}</Apoyo>
          {fallo ? <Aviso tono="error">{t(fallo)}</Aviso> : null}
        </Dialogo>
      ) : null}

      {baja ? (
        <Dialogo
          abierto
          onCambio={(v) => !v && setBaja(false)}
          etiqueta={t("Baja definitiva")}
          titulo={t("Esto no se puede deshacer")}
          pie={
            <>
              <Boton tono="contorno" medida="chica" onClick={() => setBaja(false)}>
                {t("Mejor no")}
              </Boton>
              <Boton
                tono="peligro"
                medida="chica"
                disabled={enviando}
                onClick={() => void pedir("C", detalle || "Baja definitiva de la cuenta.")}
              >
                {enviando ? t("Enviando…") : t("Pedir mi baja")}
              </Boton>
            </>
          }
        >
          <Apoyo>{t("Se borran tus fotos, tus medidas, tu peso y tu historial clínico. Solo se conserva el registro de movimientos, con tu identificador anonimizado, por obligación legal.")}</Apoyo>
          <Aviso tono="error">{t("Si quieres conservar algo, descárgalo antes de pedirla.")}</Aviso>
          <Apoyo>{t("La solicitud le llega a tu coach, que la procesa y te confirma.")}</Apoyo>
          {fallo ? <Aviso tono="error">{t(fallo)}</Aviso> : null}
        </Dialogo>
      ) : null}
    </div>
  );
}

const ROTULO_ARCO: Record<SolicitudArcoApi["estado"], string> = {
  recibida: "Esperando respuesta",
  respondida: "Contestada, en ejecución",
  resuelta: "Resuelta",
};

/** Lo que ha pedido y en qué va. Vacío no se enseña: no hay nada que decir. */
function SolicitudesArco({ filas }: { filas: SolicitudArcoApi[] }) {
  const { t } = useIdioma();
  if (filas.length === 0) return null;

  return (
    <ul className="escalona flex flex-col divide-y divide-linea border-y border-linea">
      {filas.map((s) => (
        <li key={s.ulid} className="flex flex-wrap items-baseline justify-between gap-2 py-2.5">
          <span className="flex min-w-0 flex-col gap-0.5">
            <span className="text-menor font-medium">{s.rotulo}</span>
            <span className="text-micro text-tinta-suave">
              {t(ROTULO_ARCO[s.estado])}
              {s.venceEl ? t(" · antes del {fecha}", { fecha: fecha(s.venceEl) }) : ""}
            </span>
          </span>
          {s.estado === "resuelta" ? (
            <Chip tono="exito">{t("Lista")}</Chip>
          ) : (s.diasRestantes ?? 0) < 0 ? (
            <Chip tono="error">{t("Fuera de plazo")}</Chip>
          ) : (
            <Chip tono="espera">{t("{dias} días", { dias: s.diasRestantes ?? 0 })}</Chip>
          )}
        </li>
      ))}
    </ul>
  );
}
