"use client";

import { useMemo } from "react";
import { BentoCard } from "@/components/ui/bento-card";
import { CheckTile } from "@/components/ui/check-tile";
import {
  useHabitos,
  useHabitosDeHoy,
  useMarcarHabito,
} from "@/lib/api/hooks";

type Props = { fecha: string };

/**
 * Checklist de hábitos del día (DESIGN.md §2.1 §3.2, SPEC.md §2.4).
 * Lista los hábitos activos del usuario y muestra cuáles ya se marcaron
 * para la fecha. Tocar un tile hace upsert con el valor opuesto.
 */
export function HabitosCard({ fecha }: Props) {
  const habitos = useHabitos();
  const registros = useHabitosDeHoy(fecha);
  const marcar = useMarcarHabito(fecha);

  const marcados = useMemo(() => {
    const set = new Set<number>();
    registros.data?.forEach((r) => {
      if (r.valor) set.add(r.habito_id);
    });
    return set;
  }, [registros.data]);

  return (
    <BentoCard>
      <header className="flex items-center justify-between mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Hábitos
        </p>
        {habitos.data && (
          <span className="text-[11px] text-text-secondary">
            {marcados.size} / {habitos.data.length}
          </span>
        )}
      </header>

      {habitos.isLoading ? (
        <div className="h-24" />
      ) : habitos.data && habitos.data.length > 0 ? (
        <div className="flex flex-col gap-2">
          {habitos.data.map((h) => (
            <CheckTile
              key={h.id}
              nombre={h.nombre}
              checked={marcados.has(h.id)}
              sincronizando={marcar.isPending && marcar.variables?.habito_id === h.id}
              onToggle={() =>
                marcar.mutate({ habito_id: h.id, valor: !marcados.has(h.id) })
              }
            />
          ))}
        </div>
      ) : (
        <p className="text-[14px] text-text-secondary">No hay hábitos configurados.</p>
      )}
    </BentoCard>
  );
}
