/** Diálogo modal sobre Radix.
 *
 *  Radix resuelve lo que es fácil hacer mal a mano: atrapar el foco dentro, devolverlo al
 *  disparador al cerrar, cerrar con Escape, y anunciarlo a un lector de pantalla.
 *
 *  En teléfono entra desde abajo y ocupa el ancho completo; en escritorio se centra.
 */

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";

import { Etiqueta } from "@/componentes/primitivas";

export function Dialogo({
  abierto,
  onCambio,
  etiqueta,
  titulo,
  descripcion,
  children,
  pie,
}: {
  abierto: boolean;
  onCambio: (v: boolean) => void;
  etiqueta?: string;
  titulo: string;
  descripcion?: string;
  children: ReactNode;
  pie?: ReactNode;
}) {
  return (
    <Dialog.Root open={abierto} onOpenChange={onCambio}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-tinta/40 backdrop-blur-sm" />
        <Dialog.Content
          className="fixed inset-x-0 bottom-0 z-50 flex max-h-[92vh] flex-col overflow-hidden rounded-t-marco border-t border-linea bg-fondo-elevado sm:inset-0 sm:m-auto sm:h-fit sm:max-w-lg sm:rounded-marco sm:border"
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
              aria-label="Cerrar"
              className="grid size-8 shrink-0 place-items-center rounded-marco border border-linea text-tinta-media transition-colors hover:border-tinta hover:text-tinta"
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
