"use client";

import Link from "next/link";
import { ClipboardList } from "lucide-react";

import { TarjetaComposicion } from "@/components/progreso/tarjeta-composicion";
import { TarjetaCumplimiento } from "@/components/progreso/tarjeta-cumplimiento";
import { TarjetaRecuperacion } from "@/components/progreso/tarjeta-recuperacion";
import { TarjetaRendimiento } from "@/components/progreso/tarjeta-rendimiento";

/**
 * Pantalla Progreso: cuatro preguntas, cada una con su respuesta en una frase.
 * La captura (tests, medida, partido) vive en /progreso/registrar.
 */
export function ProgresoScreen() {
  return (
    <div className="flex flex-col gap-4 pb-32">
      <Link
        href="/progreso/registrar"
        className="flex items-center justify-between rounded-pill bg-surface-secondary px-4 py-3 text-[13px] font-medium text-text-primary"
      >
        <span className="flex items-center gap-2">
          <ClipboardList size={16} aria-hidden /> Registrar test, medida o partido
        </span>
        <span aria-hidden className="text-text-secondary">›</span>
      </Link>
      <TarjetaCumplimiento />
      <TarjetaRendimiento />
      <TarjetaRecuperacion />
      <TarjetaComposicion />
    </div>
  );
}
