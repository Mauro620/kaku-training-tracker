"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { BentoCard } from "@/components/ui/bento-card";
import { useCiclos } from "@/lib/api/hooks";
import { elegirCicloActivo, progresoDeSemana, useSemanaActual } from "@/lib/semana";

type Props = { fecha: string };

/**
 * Ciclo activo visible arriba de Entreno: numero, objetivo y rango de
 * fechas, con link al detalle. "Activo" es el que no esta cerrado y cuyo
 * rango cubre `fecha`; si ninguno cubre exacto (recien creado antes de
 * empezar, o se paso de fecha_fin_prevista sin cerrarlo), cae al no
 * cerrado mas reciente para no dejar la pantalla vacia sin motivo.
 */
export function CicloActivoCard({ fecha }: Props) {
  const ciclos = useCiclos();
  const actual = useSemanaActual(fecha);

  const ciclo = ciclos.data ? elegirCicloActivo(ciclos.data, fecha) : null;
  if (!ciclo) return null;

  const progreso = progresoDeSemana(actual.planes);

  return (
    <Link href={`/entreno/ciclos/${ciclo.id}`}>
      <BentoCard className="flex items-center justify-between">
        <div>
          <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
            Ciclo #{ciclo.numero}
          </p>
          <p className="mt-0.5 text-[16px] font-semibold text-text-primary">
            {ciclo.objetivo}
          </p>
          <p className="mt-0.5 text-[11px] text-text-secondary">
            {ciclo.fecha_inicio} → {ciclo.fecha_fin_prevista}
          </p>
          {actual.semana && (
            <p className="mt-1 text-[11px] uppercase tracking-widest text-text-secondary">
              Semana {actual.semana.numero} de {ciclo.semanas} · {actual.semana.fase} ·{" "}
              {progreso.hechas} de {progreso.total} sesiones
            </p>
          )}
        </div>
        <ChevronRight size={18} className="text-text-secondary" />
      </BentoCard>
    </Link>
  );
}
