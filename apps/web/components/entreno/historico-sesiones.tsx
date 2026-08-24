"use client";

import { BentoCard } from "@/components/ui/bento-card";
import { useTiposSesion, useUltimasSesiones } from "@/lib/api/hooks";

type Props = { onVerSesion: (sesionId: string) => void };

/** Las ultimas 10 sesiones registradas. Tocar una abre el detalle existente. */
export function HistoricoSesiones({ onVerSesion }: Props) {
  const { data, isLoading } = useUltimasSesiones(10);
  const tipos = useTiposSesion();

  if (isLoading) return null;
  if (!data || data.length === 0) return null;

  return (
    <BentoCard>
      <p className="mb-3 text-[11px] font-normal tracking-widest uppercase text-text-secondary">
        Historico
      </p>

      <div className="flex flex-col">
        {data.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => onVerSesion(s.id)}
            className="flex items-center gap-3 border-b border-border-subtle py-2.5 text-left last:border-b-0"
          >
            <span className="w-14 shrink-0 text-[11px] tabular text-text-secondary">
              {s.fecha.slice(5)}
            </span>
            <span className="min-w-0 flex-1 truncate text-[14px] text-text-primary">
              {tipos.data?.find((t) => t.id === s.tipo_sesion_id)?.nombre ?? "Sesion"}
            </span>
            <span className="shrink-0 text-[11px] tabular text-text-secondary">
              {s.duracion_min}min · RPE {s.rpe}
            </span>
            <span className="w-10 shrink-0 text-right text-[14px] font-semibold tabular text-text-primary">
              {s.carga_srpe}
            </span>
          </button>
        ))}
      </div>
    </BentoCard>
  );
}
