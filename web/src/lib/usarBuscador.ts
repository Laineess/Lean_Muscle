/** Estado del buscador global, con su atajo ⌘K / Ctrl+K. */

import { useEffect, useState } from "react";

export function useBuscador() {
  const [abierto, setAbierto] = useState(false);

  useEffect(() => {
    const alTeclear = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setAbierto((v) => !v);
      }
    };
    document.addEventListener("keydown", alTeclear);
    return () => document.removeEventListener("keydown", alTeclear);
  }, []);

  return { abierto, setAbierto };
}
