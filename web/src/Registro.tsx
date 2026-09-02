/** Registro abierto: la liga propia de cada coach, `/r/{slug}`.
 *
 *  Dos pasos y ninguno de adorno. En el primero entrega lo mínimo para existir —nombre,
 *  correo, fecha de nacimiento— y acepta los términos y el aviso de privacidad, que es
 *  justo donde toca aceptarlos: aquí es donde entrega esos datos. En el segundo prueba que
 *  el correo es suyo, y a partir de ahí el recorrido sigue con sesión.
 */

import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { CargandoPantalla } from "@/componentes/Estado";
import {
  Apoyo,
  Aviso,
  Boton,
  Campo,
  Casilla,
  Entrada,
  Etiqueta,
  Portada,
  Regla,
  Vacio,
} from "@/componentes/primitivas";
import { ErrorApi, api, urlDeLogoDeLiga, type LigaDeRegistroApi } from "@/lib/api";
import { num } from "@/lib/formato";
import { useIdioma } from "@/lib/idioma";
import { actorGuardado, cerrarSesion, guardarActor } from "@/lib/sesion";
import { usarApi } from "@/lib/usarApi";

const VACIO = {
  nombre: "",
  correo: "",
  contrasena: "",
  fechaNacimiento: "",
  whatsapp: "",
};

const LLAVE_REGISTRO = "mfp.registro_pendiente";

function registroGuardado(slug: string): { slug: string; correo: string; verificado: boolean } | null {
  try {
    const valor = JSON.parse(localStorage.getItem(LLAVE_REGISTRO) ?? "null") as {
      slug?: string;
      correo?: string;
      verificado?: boolean;
    } | null;
    return valor?.slug === slug && valor.correo
      ? { slug, correo: valor.correo, verificado: valor.verificado === true }
      : null;
  } catch {
    return null;
  }
}

export function guardarRegistro(slug: string, correo: string, verificado = false): void {
  localStorage.setItem(LLAVE_REGISTRO, JSON.stringify({ slug, correo, verificado }));
}

function olvidarRegistro(): void {
  localStorage.removeItem(LLAVE_REGISTRO);
}

export function Registro() {
  const { slug = "" } = useParams();
  const carga = usarApi<LigaDeRegistroApi>((s) => api.registro.liga(slug, s), [slug]);
  const [correoEnviado, setCorreoEnviado] = useState<string | null>(null);
  const [codigoDeCortesia, setCodigoDeCortesia] = useState<string | null>(null);
  const [errorReanudacion, setErrorReanudacion] = useState<string | null>(null);
  const navegar = useNavigate();
  const { t } = useIdioma();

  useEffect(() => {
    const pendiente = registroGuardado(slug);
    const actor = actorGuardado();
    if (pendiente?.verificado && actor?.rol === "alumna" && actor.correo === pendiente.correo) {
      api.alumna.solicitud().then(() => navegar("/solicitud", { replace: true })).catch(() => undefined);
      return;
    }
    if (actor) cerrarSesion();
    if (!pendiente) return;

    api.registro
      .reenviar(slug, pendiente.correo)
      .then((hecho) => {
        setCorreoEnviado(hecho.correo);
        setCodigoDeCortesia(hecho.codigo);
      })
      .catch((causa) => {
        if (causa instanceof ErrorApi && causa.estado === 404) {
          olvidarRegistro();
          setErrorReanudacion(null);
          return;
        }
        setErrorReanudacion(
          causa instanceof ErrorApi ? causa.message : t("No se pudo reanudar tu registro."),
        );
      });
  }, [navegar, slug, t]);

  if (carga.cargando)
    return <CargandoPantalla que={t("la página de tu coach")} texto={3} filas={0} />;

  if (carga.error) {
    return (
      <main className="mx-auto flex min-h-full w-full max-w-sm flex-col justify-center gap-6 px-5 py-16">
        <Portada>{t("Esta liga no existe")}</Portada>
        <Apoyo>{t("Revisa la dirección que te compartieron, o pídesela otra vez a tu coach.")}</Apoyo>
      </main>
    );
  }

  const liga = carga.datos!;

  return (
    <main className="mx-auto flex min-h-full w-full max-w-sm flex-col justify-center gap-8 px-5 py-16">
      <header className="flex flex-col items-start gap-3">
        {liga.tieneLogo ? (
          <img
            src={urlDeLogoDeLiga(slug)}
            alt=""
            className="size-10 rounded-marco border border-linea object-cover"
          />
        ) : null}
        <Etiqueta>{liga.marca}</Etiqueta>
        <Portada>
          {correoEnviado ? t("Revisa tu correo") : t("Empieza con {coach}", { coach: liga.coach })}
        </Portada>
      </header>

      {!liga.abierta ? (
        <Vacio>{liga.motivo ?? t("Esta liga no está disponible ahora mismo.")}</Vacio>
      ) : errorReanudacion ? (
        <Aviso tono="error">{errorReanudacion}</Aviso>
      ) : correoEnviado ? (
        <PasoDelCodigo
          slug={slug}
          correo={correoEnviado}
          codigoDeCortesia={codigoDeCortesia}
          onCodigo={(codigo) => setCodigoDeCortesia(codigo)}
          onVolver={() => {
            setCorreoEnviado(null);
            setCodigoDeCortesia(null);
          }}
        />
      ) : (
        <PasoDeAlta
          slug={slug}
          liga={liga}
          onEnviado={(correo, codigo) => {
            guardarRegistro(slug, correo);
            setCorreoEnviado(correo);
            setCodigoDeCortesia(codigo);
          }}
        />
      )}

      <Regla />

      <Apoyo>
        {t("¿Ya tienes cuenta?")}{" "}
        <Link to="/acceso" className="underline underline-offset-2">
          {t("Entra por aquí")}
        </Link>
        .
      </Apoyo>
    </main>
  );
}

/* ------------------------------------------------------------ Paso 1 --- */

function PasoDeAlta({
  slug,
  liga,
  onEnviado,
}: {
  slug: string;
  liga: LigaDeRegistroApi;
  onEnviado: (correo: string, codigo: string | null) => void;
}) {
  const [borrador, setBorrador] = useState(VACIO);
  const [terminos, setTerminos] = useState(false);
  const [privacidad, setPrivacidad] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const { t } = useIdioma();

  const listo =
    borrador.nombre.trim() &&
    borrador.correo.trim() &&
    borrador.contrasena &&
    borrador.fechaNacimiento &&
    terminos &&
    privacidad;

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const hecho = await api.registro.registrarse(slug, {
        nombre: borrador.nombre.trim(),
        correo: borrador.correo.trim(),
        contrasena: borrador.contrasena,
        fechaNacimiento: borrador.fechaNacimiento,
        whatsapp: borrador.whatsapp.trim() || null,
        aceptaTerminos: terminos,
        aceptaPrivacidad: privacidad,
      });
      onEnviado(hecho.correo, hecho.codigo);
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : t("No se pudo completar el registro."));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="flex flex-col gap-5" onSubmit={(e) => void enviar(e)}>
      {liga.precioInscripcion !== null ? (
        <Aviso tono="info" titulo={t("Inscripción: ${monto}", { monto: num(liga.precioInscripcion) })}>
          {t("Se paga al final, cuando ya sepas a qué hora es tu primera consulta.")}
        </Aviso>
      ) : null}

      <Campo id="rg-nombre" etiqueta={t("Tu nombre")}>
        <Entrada
          id="rg-nombre"
          autoComplete="name"
          value={borrador.nombre}
          onChange={(e) => setBorrador((b) => ({ ...b, nombre: e.target.value }))}
        />
      </Campo>

      <Campo id="rg-correo" etiqueta={t("Tu correo")} ayuda={t("Ahí te mandamos un código de 6 dígitos.")}>
        <Entrada
          id="rg-correo"
          type="email"
          autoComplete="email"
          value={borrador.correo}
          onChange={(e) => setBorrador((b) => ({ ...b, correo: e.target.value }))}
        />
      </Campo>

      <Campo
        id="rg-clave"
        etiqueta={t("Tu contraseña")}
        ayuda={t("Ocho caracteres, un número y un símbolo. Nadie más la conoce.")}
      >
        <Entrada
          id="rg-clave"
          type="password"
          autoComplete="new-password"
          value={borrador.contrasena}
          onChange={(e) => setBorrador((b) => ({ ...b, contrasena: e.target.value }))}
        />
      </Campo>

      <Campo
        id="rg-nacimiento"
        etiqueta={t("Fecha de nacimiento")}
        ayuda={t("La plataforma es solo para mayores de edad.")}
      >
        <Entrada
          id="rg-nacimiento"
          type="date"
          value={borrador.fechaNacimiento}
          onChange={(e) => setBorrador((b) => ({ ...b, fechaNacimiento: e.target.value }))}
        />
      </Campo>

      <Campo id="rg-whats" etiqueta={t("WhatsApp (opcional)")}>
        <Entrada
          id="rg-whats"
          inputMode="tel"
          value={borrador.whatsapp}
          onChange={(e) => setBorrador((b) => ({ ...b, whatsapp: e.target.value }))}
        />
      </Campo>

      {/* Nunca vienen premarcadas: es requisito legal, no estético. */}
      <Casilla
        id="rg-terminos"
        titulo={t("Acepto los Términos y Condiciones")}
        checked={terminos}
        onChange={(e) => setTerminos(e.target.checked)}
      >
        <Link to="/legal/terminos" target="_blank" className="underline underline-offset-2">
          {t("Leerlos antes de aceptar")}
        </Link>
      </Casilla>

      <Casilla
        id="rg-privacidad"
        titulo={t("Acepto el Aviso de Privacidad")}
        checked={privacidad}
        onChange={(e) => setPrivacidad(e.target.checked)}
      >
        <Link to="/legal/privacidad" target="_blank" className="underline underline-offset-2">
          {t("Leerlo antes de aceptar")}
        </Link>
      </Casilla>

      {error ? <Aviso tono="error">{error}</Aviso> : null}

      <Boton type="submit" medida="grande" ancho="completo" disabled={!listo || enviando}>
        {t("Continuar")}
      </Boton>

      <Etiqueta>
        {t(
          "Los datos de salud y las fotos vienen después, y con su propio consentimiento.",
        )}
      </Etiqueta>
    </form>
  );
}

/* ------------------------------------------------------------ Paso 2 --- */

function PasoDelCodigo({
  slug,
  correo,
  codigoDeCortesia,
  onCodigo,
  onVolver,
}: {
  slug: string;
  correo: string;
  /** Fuera de producción el correo no sale de ningún buzón: sin esto no se puede seguir. */
  codigoDeCortesia: string | null;
  onCodigo: (codigo: string | null) => void;
  onVolver: () => void;
}) {
  const navegar = useNavigate();
  const [codigo, setCodigo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const { t } = useIdioma();

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      guardarActor(await api.registro.verificar(slug, correo, codigo.trim()));
      guardarRegistro(slug, correo, true);
      void navegar("/solicitud", { replace: true });
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : t("No se pudo verificar el código."));
    } finally {
      setEnviando(false);
    }
  }

  async function reenviar() {
    setError(null);
    setAviso(null);
    try {
      const hecho = await api.registro.reenviar(slug, correo);
      onCodigo(hecho.codigo);
      setAviso(t("Te mandamos otro código."));
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.message : t("No se pudo reenviar el código."));
    }
  }

  return (
    <form className="flex flex-col gap-5" onSubmit={(e) => void enviar(e)}>
      <Apoyo>
        {t("Mandamos un código de 6 dígitos a")} <strong className="font-medium">{correo}</strong>.{" "}
        {t("Vence en 15 minutos.")}
      </Apoyo>

      {codigoDeCortesia ? (
        <Aviso tono="atencion" titulo={t("Estás en desarrollo")}>
          {t("El correo no sale de ningún buzón, así que aquí está el código:")}{" "}
          <strong className="cifra font-semibold">{codigoDeCortesia}</strong>
        </Aviso>
      ) : null}

      <Campo id="rg-codigo" etiqueta={t("Código")}>
        <Entrada
          id="rg-codigo"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          placeholder="000000"
          className="cifra text-center text-guia tracking-[0.4em]"
          value={codigo}
          onChange={(e) => setCodigo(e.target.value.replace(/\D/g, "").slice(0, 6))}
        />
      </Campo>

      {error ? <Aviso tono="error">{error}</Aviso> : null}
      {aviso ? <Aviso tono="exito">{aviso}</Aviso> : null}

      <Boton type="submit" medida="grande" ancho="completo" disabled={codigo.length < 6 || enviando}>
        {t("Verificar")}
      </Boton>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <Boton tono="discreto" medida="chica" type="button" onClick={() => void reenviar()}>
          {t("Mandar otro código")}
        </Boton>
        <Boton tono="discreto" medida="chica" type="button" onClick={onVolver}>
          {t("Corregir mis datos")}
        </Boton>
      </div>
    </form>
  );
}
