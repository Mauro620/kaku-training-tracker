"use client";

import Link from "next/link";
import { Calendar, FileJson } from "lucide-react";

/**
 * Acciones globales del header de Entreno (Fase 4 R3a + R4).
 * - Ciclos vive en /entreno/ciclos, agrupado con la captura de sesion.
 * - Importar plan semanal vive en /entreno/importar (Fase 4 R4): el
 *   pegado de JSON es una operacion de escritorio, deliberada, que
 *   no comparte el flujo de captura diaria.
 */
export function HeaderAcciones() {
  return (
    <div className="flex items-center gap-2">
      <Link
        href="/entreno/importar"
        aria-label="Importar plan semanal"
        className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-secondary"
      >
        <FileJson size={18} strokeWidth={1.8} />
      </Link>
      <Link
        href="/entreno/ciclos"
        aria-label="Ciclos"
        className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-secondary"
      >
        <Calendar size={18} strokeWidth={1.8} />
      </Link>
    </div>
  );
}
