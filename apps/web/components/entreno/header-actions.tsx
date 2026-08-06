"use client";

import Link from "next/link";
import { Calendar } from "lucide-react";

/**
 * Acciones globales del header de Entreno (Fase 4 R3a).
 * Ciclos vive dentro de /entreno/ciclos para mantenerlo agrupado con la
 * captura de sesion: ambos son "pensar el entrenamiento".
 */
export function HeaderAcciones() {
  return (
    <Link
      href="/entreno/ciclos"
      aria-label="Ciclos"
      className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-secondary"
    >
      <Calendar size={18} strokeWidth={1.8} />
    </Link>
  );
}
