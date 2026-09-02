/** La cuenta de la coach, tal como ella la declaró.
 *
 *  Es texto libre de la coach: cada banco se llena distinto, así que no se toca. Se muestra
 *  en las pantallas donde la alumna tiene que pagar (reservar, inscribirse, saldar un adeudo)
 *  y se oculta entero si la coach no la ha escrito todavía.
 */

import { Landmark } from "lucide-react";

import { Apoyo, Etiqueta } from "@/componentes/primitivas";
import { useIdioma } from "@/lib/idioma";

export function DatosBancarios({ texto }: { texto: string | null | undefined }) {
  const { t } = useIdioma();
  const contenido = (texto ?? "").trim();
  if (!contenido) return null;

  return (
    <div className="flex flex-col gap-1.5 border-t border-linea pt-3">
      <Etiqueta icono={Landmark}>{t("Para pagar")}</Etiqueta>
      <Apoyo className="whitespace-pre-line text-tinta">{contenido}</Apoyo>
    </div>
  );
}