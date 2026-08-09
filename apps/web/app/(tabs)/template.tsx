import type { ReactNode } from "react";

/**
 * A diferencia de layout.tsx, un template remonta en cada navegacion (swipe
 * entre tabs, entrar/salir de un detalle, volver atras): eso es lo que
 * permite que la animacion de entrada se dispare cada vez, no solo una vez
 * al cargar la app. CSS puro (ver .animate-enter en globals.css), nada de
 * libreria de animacion para esto.
 */
export default function Template({ children }: { children: ReactNode }) {
  return <div className="animate-enter">{children}</div>;
}
