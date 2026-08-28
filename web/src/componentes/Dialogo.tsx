/** Diálogo modal sobre Radix.
 *
 *  Radix resuelve lo que es fácil hacer mal a mano: atrapar el foco dentro, devolverlo al
 *  disparador al cerrar, cerrar con Escape, y anunciarlo a un lector de pantalla.
 *
 *  En teléfono entra desde abajo y ocupa el ancho completo; en escritorio se centra.
 *
 *  La animación cuelga del `data-state` que Radix pone en el nodo, y Radix retrasa el
 *  desmontaje hasta que termina. Por eso el diálogo también se va con gracia, en vez de
 *  desaparecer de golpe. Al cerrar dura menos que al abrir: irse rápido se agradece.
 */

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";

import { Etiqueta } from "@/componentes/primitivas";
import { useIdioma } from "@/lib/idioma";

export function Dialogo({
  abierto,
  onCambio,
  etiqueta,
  titulo,
  descripcion,
  children,
  pie,
  ancho = "normal",
}: {
  abierto: boolean;
  onCambio: (v: boolean) => void;
  etiqueta?: string;
  titulo: string;
  descripcion?: string;
  children: ReactNode;
  pie?: ReactNode;
  /** «ancho» para contenido que se lee mal angosto, como una lámina de referencia. */
  ancho?: "normal" | "ancho";
}) {
  const { t } = useIdioma();
  return (
    <Dialog.Root open={abierto} onOpenChange={onCambio}>
      <Dialog.Portal>
        <Dialog.Overlay
          className="fixed inset-0 z-40 bg-tinta/40 backdrop-blur-sm data-[state=open]:animate-aparece data-[state=closed]:animate-desaparece"
        />
        <Dialog.Content
          className={`fixed inset-x-0 bottom-0 z-50 flex max-h-[92vh] flex-col overflow-hidden rounded-t-marco border-t border-linea bg-fondo-elevado sm:inset-0 sm:m-auto sm:h-fit sm:rounded-marco sm:border ${
            ancho === "ancho" ? "sm:max-w-3xl" : "sm:max-w-lg"
          } data-[state=open]:animate-sube-hoja data-[state=closed]:animate-baja-hoja sm:data-[state=open]:animate-emerge sm:data-[state=closed]:animate-se-encoge`}
          aria-describedby={descripcion ? undefined : ""}
        >
          <header className="flex items-start justify-between gap-4 border-b border-linea px-5 py-4">
            <div className="flex flex-col gap-1">
              {etiqueta ? <Etiqueta>{etiqueta}</Etiqueta> : null}
              <Dialog.Title className="text-guia font-semibold tracking-[-0.01em]">
                {titulo}
              </Dialog.Title>
              {descripcion ? (
                <Dialog.Description className="text-menor text-tinta-media">
                  {descripcion}
                </Dialog.Description>
              ) : null}
            </div>
            <Dialog.Close
              aria-label={t("Cerrar")}
              className="hunde grid size-8 shrink-0 place-items-center rounded-marco border border-linea text-tinta-media transition-colors duration-[var(--mov-rapido)] ease-suave hover:border-tinta hover:text-tinta"
            >
              <X className="size-4" />
            </Dialog.Close>
          </header>

          <div className="flex flex-col gap-4 overflow-y-auto px-5 py-5">{children}</div>

          {pie ? (
            <footer className="flex flex-wrap justify-end gap-2 border-t border-linea px-5 py-4">
              {pie}
            </footer>
          ) : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
