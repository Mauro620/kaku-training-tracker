"use client";

import { BentoCard } from "@/components/ui/bento-card";
import { useSesionesDeFecha, useTiposSesion, useEjercicios, type Sesion } from "@/lib/api/hooks";

type Props = { fecha: string };

/**
 * Lista de las sesiones registradas en la fecha (ROADMAP §4).
 * El backend carga las series via selectinload asi que no hay N+1.
 */
export function SesionesList({ fecha }: Props) {
  const { data, isLoading } = useSesionesDeFecha(fecha);
  const tipos = useTiposSesion();
  const ejercicios = useEjercicios();

  return (
    <BentoCard>
      <header className="mb-4 flex items-center justify-between">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Sesiones de hoy
        </p>
        {data && (
          <span className="text-[11px] text-text-secondary">
            {data.length} registrada{data.length === 1 ? "" : "s"}
          </span>
        )}
      </header>

      {isLoading ? (
        <div className="h-24" />
      ) : !data || data.length === 0 ? (
        <p className="text-[14px] text-text-secondary">Aun no hay sesiones hoy.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {data.map((s) => (
            <SesionCard
              key={s.id}
              sesion={s}
              tipoNombre={tipos.data?.find((t) => t.id === s.tipo_sesion_id)?.nombre}
              ejercicioNombre={(id) =>
                ejercicios.data?.find((e) => e.id === id)?.nombre
              }
            />
          ))}
        </div>
      )}
    </BentoCard>
  );
}

function SesionCard({
  sesion,
  tipoNombre,
  ejercicioNombre,
}: {
  sesion: Sesion;
  tipoNombre: string | undefined;
  ejercicioNombre: (id: number) => string | undefined;
}) {
  return (
    <div className="rounded-bento border border-border-subtle bg-surface-secondary p-4">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[16px] font-semibold text-text-primary">
          {tipoNombre ?? "Sesion"}
        </p>
        <p className="text-[20px] font-bold tabular text-text-primary">{sesion.carga_srpe}</p>
      </div>
      <p className="text-[11px] uppercase tracking-widest text-text-secondary">
        {sesion.duracion_min} min · RPE {sesion.rpe} · {sesion.series.length} serie
        {sesion.series.length === 1 ? "" : "s"}
      </p>
      {sesion.nota && (
        <p className="mt-2 text-[13px] text-text-secondary">{sesion.nota}</p>
      )}
      {sesion.series.length > 0 && (
        <ul className="mt-3 flex flex-col gap-1 border-t border-border-subtle pt-2">
          {sesion.series.map((se) => (
            <li
              key={se.id}
              className="flex items-center justify-between text-[13px]"
            >
              <span className="text-text-primary">
                {ejercicioNombre(se.ejercicio_id) ?? `Ejercicio ${se.ejercicio_id}`}
              </span>
              <span className="text-text-secondary tabular">
                {se.series}×{se.reps}
                {se.peso_kg ? ` · ${se.peso_kg}kg` : ""}
                {se.rpe ? ` · RPE ${se.rpe}` : ""}
                {se.dolor_lumbar ? " · lumbar" : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
