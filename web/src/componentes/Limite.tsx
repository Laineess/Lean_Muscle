/** Límite de error: una pantalla que truena no se lleva la aplicación por delante.
 *
 *  Sin esto, cualquier excepción sin capturar deja la ventana en negro y sin barra de
 *  navegación, así que no hay manera de salir salvo escribir la URL a mano. Con esto, el
 *  error se queda dentro de la pantalla que lo produjo y la persona puede volver.
 *
 *  El detalle técnico se muestra en desarrollo y se calla en producción: a la alumna no le
 *  sirve un `TypeError` y a la coach tampoco.
 */

import { Component, type ErrorInfo, type ReactNode } from "react";

import { Aviso, Boton } from "@/componentes/primitivas";

interface Props {
  children: ReactNode;
  /** Se reinicia el límite cuando cambia. Con la ruta basta: al navegar se vuelve a probar. */
  clave?: string;
}

interface Estado {
  error: Error | null;
}

export class Limite extends Component<Props, Estado> {
  state: Estado = { error: null };

  static getDerivedStateFromError(error: Error): Estado {
    return { error };
  }

  componentDidUpdate(anterior: Props): void {
    // Al cambiar de pantalla se vuelve a intentar: quedarse con el error de la anterior
    // convertiría un fallo puntual en uno permanente.
    if (this.state.error && anterior.clave !== this.props.clave) {
      this.setState({ error: null });
    }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // A la consola completo: es lo único que permite encontrarlo después.
    console.error("Pantalla caída:", error, info.componentStack);
  }

  render(): ReactNode {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div className="flex flex-col gap-6">
        <Aviso tono="error" titulo="Esta pantalla no se pudo mostrar">
          Algo falló al pintarla. El resto de la aplicación sigue funcionando: usa el menú
          para ir a otro lado.
          {import.meta.env.DEV ? (
            <code className="mt-3 block text-micro text-tinta-media">{error.message}</code>
          ) : null}
        </Aviso>
        <div className="flex flex-wrap gap-2">
          <Boton onClick={() => this.setState({ error: null })}>Volver a intentar</Boton>
          <Boton tono="contorno" onClick={() => window.location.replace("/")}>
            Ir al inicio
          </Boton>
        </div>
      </div>
    );
  }
}
