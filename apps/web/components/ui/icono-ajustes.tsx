import Link from "next/link";

import { Settings } from "lucide-react";

/**
 * D1 (revision de UI): acceso a /ajustes desde el header de Hoy.
 * Boton cuadrado de 40x40 con icono Settings. Tooltip "Ajustes".
 */
export function IconoAjustes() {
  return (
    <Link
      href="/ajustes"
      aria-label="Ajustes"
      title="Ajustes"
      className="flex h-10 w-10 items-center justify-center rounded-full text-text-secondary transition hover:bg-bg-card hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
    >
      <Settings className="h-5 w-5" strokeWidth={2} aria-hidden />
    </Link>
  );
}
