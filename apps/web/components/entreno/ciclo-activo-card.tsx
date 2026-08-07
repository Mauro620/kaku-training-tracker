"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { BentoCard } from "@/components/ui/bento-card";
import { useCiclos, type Ciclo } from "@/lib/api/hooks";

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

  if (!ciclos.data || ciclos.data.length === 0) return null;

  const ciclo = elegirCicloActivo(ciclos.data, fecha);
  if (!ciclo) return null;

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
        </div>
        <ChevronRight size={18} className="text-text-secondary" />
      </BentoCard>
    </Link>
  );
}

function elegirCicloActivo(ciclos: Ciclo[], fecha: string): Ciclo | null {
  const noCerrados = ciclos.filter((c) => c.estado !== "cerrado");
  if (noCerrados.length === 0) return null;

  const dentroDeRango = noCerrados.find(
    (c) => c.fecha_inicio <= fecha && fecha <= c.fecha_fin_prevista,
  );
  if (dentroDeRango) return dentroDeRango;

  return (
    [...noCerrados].sort((a, b) => (a.fecha_inicio < b.fecha_inicio ? 1 : -1))[0] ?? null
  );
}
