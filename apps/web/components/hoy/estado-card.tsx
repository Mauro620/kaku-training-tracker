"use client";

import { CircularProgressRing } from "@/components/ui/circular-progress-ring";
import { BentoCard } from "@/components/ui/bento-card";

/**
 * Estado del día (DESIGN.md §4.1).
 * El cálculo completo del Estado (REGLAS_NEGOCIO §9) requiere ACWR,
 * historial de 28 días y la línea base de Hooper. Eso es Fase 8.
 * Hasta entonces: placeholder honesto. Mostrar un número inventado en la
 * pantalla principal sería peor que mostrar `—`.
 */
export function EstadoCard() {
  return (
    <BentoCard>
      <div className="flex items-center gap-6">
        <CircularProgressRing valor={null} />
        <div className="flex-1">
          <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
            Estado del día
          </p>
          <p className="mt-2 text-[18px] font-semibold leading-tight text-text-primary">
            Cálculo disponible en fase 8
          </p>
          <p className="mt-1 text-[13px] font-normal text-text-secondary">
            Necesita 28 días de historial para ACWR y línea base de Hooper.
          </p>
        </div>
      </div>
    </BentoCard>
  );
}
