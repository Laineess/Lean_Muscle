/** Primitivas del sistema.
 *
 *  Editorial y calmado: el dato manda y todo lo demás se quita de en medio. Por eso hay
 *  menos cajas de las que uno esperaría — una tarjeta solo existe cuando de verdad agrupa
 *  cosas que se leen juntas.
 *
 *  El dorado nunca lleva texto largo: vive en filetes, bordes y estados activos. Para las
 *  pocas palabras que sí van en acento se usa `text-acento-texto`, que es la versión
 *  oscurecida que sí pasa contraste.
 *
 *  El movimiento vive aquí y no en las pantallas. Duraciones y curvas salen de los tokens
 *  de `index.css`, y son cortas a propósito: esto se usa de pie y con prisa. Un icono
 *  acompaña al texto, nunca lo sustituye, y siempre va `aria-hidden`.
 */

import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { AlertTriangle, CheckCircle2, Info, Loader2, OctagonAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";

import { cn } from "@/lib/utils";
import type { Direccion } from "@/lib/formato";

/* ---------------------------------------------------------------- Botón --- */

const boton = cva(
  "inline-flex items-center justify-center gap-2 rounded-marco font-medium " +
    // El hundido del `active` es lo único que responde a un dedo: en teléfono no hay hover
    // y sin él el botón parece muerto hasta que la pantalla cambia.
    "transition-[background-color,border-color,color,opacity,transform] " +
    "duration-[var(--mov-rapido)] ease-salida active:scale-[0.97] " +
    "disabled:pointer-events-none disabled:opacity-40 " +
    "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-acento-texto",
  {
    variants: {
      tono: {
        // El botón sólido es negro, no dorado: en una interfaz calmada el peso lo da el
        // contraste, no el color.
        solido: "bg-tinta text-fondo hover:opacity-90",
        contorno: "border border-linea-fuerte text-tinta hover:bg-fondo-sutil",
        discreto: "text-tinta-media hover:text-tinta hover:bg-fondo-sutil",
        peligro: "border border-peligro text-peligro hover:bg-peligro-sutil",
      },
      medida: {
        // 44 px es el mínimo táctil cómodo; la alumna usa esto de pie, en ayunas.
        normal: "h-11 px-5 text-menor",
        grande: "h-13 px-7 text-cuerpo",
        chica: "h-8 px-3 text-micro",
        icono: "size-9",
      },
      ancho: { auto: "", completo: "w-full" },
    },
    defaultVariants: { tono: "solido", medida: "normal", ancho: "auto" },
  },
);

export interface BotonProps
  extends ComponentProps<"button">,
    VariantProps<typeof boton> {
  asChild?: boolean;
  /** Mientras la petición viaja: rueda a la izquierda y el botón deja de aceptar clics.
   *  Sin esto la coach vuelve a apretar y se manda dos veces. */
  cargando?: boolean;
}

export function Boton({
  className,
  tono,
  medida,
  ancho,
  asChild,
  cargando,
  disabled,
  children,
  ...props
}: BotonProps) {
  // `Slot` exige un hijo único, así que en ese caso no se le puede inyectar la rueda.
  if (asChild) {
    return (
      <Slot
        className={cn(boton({ tono, medida, ancho }), className)}
        // Sin esto, un `<Boton asChild disabled>` quedaba habilitado: `disabled` está
        // destructurado arriba y ya no viaja dentro de `props`.
        {...(disabled === undefined ? {} : { disabled })}
        {...props}
      >
        {children}
      </Slot>
    );
  }
  return (
    <button
      className={cn(boton({ tono, medida, ancho }), className)}
      disabled={disabled ?? cargando}
      aria-busy={cargando ? true : undefined}
      {...props}
    >
      {cargando ? <Loader2 aria-hidden className="size-4 shrink-0 animate-gira" /> : null}
      {children}
    </button>
  );
}

/* --------------------------------------------------------------- Textos --- */

export function Portada({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <h1 className={cn("text-portada font-semibold tracking-[-0.02em] text-balance", className)}>
      {children}
    </h1>
  );
}

export function Titulo({
  children,
  className,
  icono: Icono,
}: {
  children: ReactNode;
  className?: string;
  /** Acompaña al título, nunca lo sustituye. Va `aria-hidden`: quien escucha la pantalla
   *  ya tiene el texto y el icono solo sería ruido. */
  icono?: LucideIcon;
}) {
  return (
    <h2
      className={cn(
        "text-titulo font-semibold tracking-[-0.015em] text-balance",
        Icono && "flex items-center gap-2.5",
        className,
      )}
    >
      {Icono ? <Icono aria-hidden className="size-5 shrink-0 text-acento" /> : null}
      {children}
    </h2>
  );
}

/** Etiqueta de sección: versalitas pequeñas, el único adorno tipográfico del sistema. */
export function Etiqueta({
  children,
  className,
  icono: Icono,
}: {
  children: ReactNode;
  className?: string;
  icono?: LucideIcon;
}) {
  return (
    <p
      className={cn(
        "text-micro font-semibold uppercase tracking-[0.12em] text-tinta-suave",
        Icono && "flex items-center gap-1.5",
        className,
      )}
    >
      {Icono ? <Icono aria-hidden className="size-3.5 shrink-0 text-acento" /> : null}
      {children}
    </p>
  );
}

export function Apoyo({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("text-menor leading-relaxed text-tinta-media", className)}>{children}</p>;
}

/* -------------------------------------------------------------- Tarjeta --- */

export function Tarjeta({
  children,
  className,
  acentuada,
  interactiva,
  segunda,
}: {
  children: ReactNode;
  className?: string;
  acentuada?: boolean;
  /** Solo cuando la tarjeta entera abre algo. Si no lleva a ningún lado, no se mueve:
   *  una tarjeta que reacciona y no hace nada promete un clic que no existe. */
  interactiva?: boolean;
  /** El filete en el segundo color, para distinguir dos tarjetas hermanas. */
  segunda?: boolean;
}) {
  return (
    <section
      className={cn(
        "rounded-marco border border-linea bg-fondo-elevado p-5 sm:p-6",
        acentuada && "border-l-[3px] border-l-acento bg-acento-sutil/40",
        segunda && "border-l-[3px] border-l-secundario bg-secundario-sutil/40",
        interactiva && "alza cursor-pointer hover:border-tinta",
        className,
      )}
    >
      {children}
    </section>
  );
}

/* ----------------------------------------------------------------- Dato --- */

const COLOR_DIRECCION: Record<Direccion, string> = {
  // Bajar no siempre es bueno ni subir malo: quién lo interpreta es la coach. El color
  // solo distingue el sentido del cambio, no lo califica.
  baja: "text-tinta-media",
  sube: "text-acento-texto",
  igual: "text-tinta-suave",
};

export interface DatoProps {
  rotulo: string;
  valor: string;
  /** `| undefined` explícito: con `exactOptionalPropertyTypes` una prop opcional no
      acepta undefined a menos que se declare, y estos valores vienen de cálculos. */
  unidad?: string | undefined;
  nota?: string | undefined;
  direccion?: Direccion | undefined;
  grande?: boolean | undefined;
}

export function Dato({ rotulo, valor, unidad, nota, direccion, grande }: DatoProps) {
  return (
    <div className="flex flex-col gap-1">
      <Etiqueta>{rotulo}</Etiqueta>
      <p
        className={cn(
          "cifra font-semibold tracking-[-0.03em]",
          grande ? "text-cifra" : "text-portada",
        )}
      >
        {valor}
        {/* La unidad en acento: aparece junto a cada cifra de la interfaz, así que es donde
            el color de la coach se reparte por todas las pantallas sin manchar ninguna. */}
        {unidad ? (
          <span className="ml-1.5 text-guia font-medium text-acento-texto">{unidad}</span>
        ) : null}
      </p>
      {nota ? (
        <p className={cn("text-menor font-medium", direccion ? COLOR_DIRECCION[direccion] : "text-tinta-media")}>
          {nota}
        </p>
      ) : null}
    </div>
  );
}

/* ----------------------------------------------------------------- Chip --- */

const chip = cva(
  "inline-flex items-center gap-1.5 rounded-marco border px-2 py-0.5 " +
    "text-micro font-semibold uppercase tracking-[0.06em] whitespace-nowrap " +
    "transition-colors duration-[var(--mov-rapido)] ease-suave",
  {
    variants: {
      tono: {
        neutro: "border-linea text-tinta-suave",
        espera: "border-acento text-acento-texto bg-acento-sutil",
        exito: "border-exito text-exito bg-exito-sutil",
        error: "border-peligro text-peligro bg-peligro-sutil",
        // Los dos de la coach. No dicen nada del estado: dicen de quién es esto.
        marca: "border-acento bg-acento text-fondo",
        segundo: "border-secundario text-secundario-texto bg-secundario-sutil",
      },
    },
    defaultVariants: { tono: "neutro" },
  },
);

export function Chip({
  children,
  tono,
  className,
}: { children: ReactNode; className?: string } & VariantProps<typeof chip>) {
  return <span className={cn(chip({ tono }), className)}>{children}</span>;
}

/* ---------------------------------------------------------------- Aviso --- */

const aviso = cva("rounded-marco border border-l-[3px] px-4 py-3 text-menor leading-relaxed", {
  variants: {
    tono: {
      info: "border-l-tinta bg-fondo-sutil",
      atencion: "border-l-acento bg-acento-sutil",
      exito: "border-l-exito bg-exito-sutil",
      error: "border-l-peligro bg-peligro-sutil",
    },
  },
  defaultVariants: { tono: "info" },
});

type TonoAviso = NonNullable<VariantProps<typeof aviso>["tono"]>;

/** El icono repite lo que ya dice el color del filete, para quien no distingue los tonos. */
const ICONO_AVISO: Record<TonoAviso, LucideIcon> = {
  info: Info,
  atencion: AlertTriangle,
  exito: CheckCircle2,
  error: OctagonAlert,
};

const COLOR_ICONO_AVISO: Record<TonoAviso, string> = {
  info: "text-tinta-media",
  atencion: "text-acento-texto",
  exito: "text-exito",
  error: "text-peligro",
};

export function Aviso({
  titulo,
  children,
  tono,
  className,
  icono,
  sinIcono,
}: {
  titulo?: string;
  children: ReactNode;
  className?: string;
  /** Para cambiarlo por uno que hable del caso concreto: una nube caída, un candado. */
  icono?: LucideIcon;
  sinIcono?: boolean;
} & VariantProps<typeof aviso>) {
  const t: TonoAviso = tono ?? "info";
  const Icono = icono ?? ICONO_AVISO[t];
  return (
    <div
      role={t === "error" ? "alert" : undefined}
      className={cn(aviso({ tono }), "animate-entra", className)}
    >
      <div className="flex gap-3">
        {sinIcono ? null : (
          <Icono aria-hidden className={cn("mt-0.5 size-4 shrink-0", COLOR_ICONO_AVISO[t])} />
        )}
        <div className="min-w-0 flex-1">
          {titulo ? <strong className="mb-0.5 block font-semibold">{titulo}</strong> : null}
          {children}
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- Campo --- */

export function Campo({
  id,
  etiqueta,
  ayuda,
  error,
  sufijo,
  children,
}: {
  id: string;
  etiqueta: string;
  ayuda?: ReactNode;
  error?: string;
  sufijo?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={id}
        className="text-micro font-semibold uppercase tracking-[0.08em] text-tinta-media"
      >
        {etiqueta}
      </label>
      <div className={cn("flex", sufijo && "items-stretch")}>
        {children}
        {sufijo ? (
          <span className="grid place-items-center rounded-r-marco border border-l-0 border-linea bg-fondo-sutil px-3 text-menor font-medium text-tinta-suave">
            {sufijo}
          </span>
        ) : null}
      </div>
      {error ? (
        <p className="text-micro font-medium text-peligro">{error}</p>
      ) : ayuda ? (
        <p className="text-micro text-tinta-suave">{ayuda}</p>
      ) : null}
    </div>
  );
}

export function Entrada({ className, ...props }: ComponentProps<"input">) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-marco border border-linea bg-fondo px-3 text-cuerpo",
        "placeholder:text-tinta-suave focus:border-tinta focus:outline-none",
        "transition-colors duration-[var(--mov-rapido)] ease-suave hover:border-tinta-suave",
        props.type === "number" && "cifra",
        className,
      )}
      {...props}
    />
  );
}

export function Selector({ className, children, ...props }: ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "h-11 w-full rounded-marco border border-linea bg-fondo px-3 text-cuerpo",
        "focus:border-tinta focus:outline-none",
        "transition-colors duration-[var(--mov-rapido)] ease-suave hover:border-tinta-suave",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}

/** Casilla de consentimiento. Nunca llega premarcada: es requisito legal, no estético. */
export function Casilla({
  id,
  titulo,
  children,
  ...props
}: { id: string; titulo: string; children?: ReactNode } & ComponentProps<"input">) {
  return (
    <label
      htmlFor={id}
      className={cn(
        "flex cursor-pointer items-start gap-3 rounded-marco border border-linea p-4",
        "transition-colors duration-[var(--mov-rapido)] ease-suave",
        "hover:border-tinta has-checked:border-acento has-checked:bg-acento-sutil",
      )}
    >
      <input
        id={id}
        type="checkbox"
        className="mt-0.5 size-5 shrink-0 accent-[var(--acento-texto)]"
        {...props}
      />
      <span className="text-menor leading-relaxed">
        <strong className="font-semibold">{titulo}</strong>
        {children ? <span className="block text-tinta-media">{children}</span> : null}
      </span>
    </label>
  );
}

/* ---------------------------------------------------------------- Vacío --- */

export function Vacio({ children }: { children: ReactNode }) {
  return (
    <p className="animate-entra rounded-marco border border-dashed border-linea px-4 py-10 text-center text-menor text-tinta-suave">
      {children}
    </p>
  );
}

/** Separador editorial: una línea fina que respira. */
export function Regla({ className, acentuada }: { className?: string; acentuada?: boolean }) {
  if (!acentuada) return <hr className={cn("border-0 border-t border-linea", className)} />;
  // Un tramo corto en acento sobre la línea gris: separa y marca de quién es la pantalla.
  return (
    <div className={cn("relative border-t border-linea", className)} role="separator">
      <span className="absolute -top-px left-0 block h-0.5 w-12 rounded-full bg-acento" />
    </div>
  );
}
