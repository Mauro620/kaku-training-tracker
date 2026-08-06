"use client";

import { BentoCard } from "@/components/ui/bento-card";
import {
  useSesionesDeFecha,
  useTiposSesion,
  useEjercicios,
  type Sesion,
  type SesionPlan,
} from "@/lib/api/hooks";

type Props = { fecha: string; planes: SesionPlan[] };

/**
 * Lista de las sesiones registradas en la fecha (ROADMAP §4).
 * El backend carga las series via selectinload asi que no hay N+1.
 */
export function SesionesList({ fecha, planes }: Props) {
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
              plan={planes.find((p) => p.id === s.sesion_plan_id) ?? null}
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
  plan,
  tipoNombre,
  ejercicioNombre,
}: {
  sesion: Sesion;
  plan: SesionPlan | null;
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
      {plan && <DeltaPlan sesion={sesion} plan={plan} />}
      {sesion.nota && (
        <p className="mt-2 text-[13px] text-text-secondary">{sesion.nota}</p>
      )}
      {sesion.series.length > 0 && (
        <ul className="mt-3 flex flex-col gap-1 border-t border-border-subtle pt-2">
          {sesion.series.map((se) => {
            // Match por ejercicio: el orden de la serie real no tiene por
            // que coincidir con el de la planeada (se puede reordenar en el
            // momento sin que eso invalide el objetivo).
            const objetivo = plan?.series_planeadas.find(
              (sp) => sp.ejercicio_id === se.ejercicio_id,
            );
            const deltaPeso =
              objetivo?.peso_objetivo_kg && se.peso_kg
                ? Number(se.peso_kg) - Number(objetivo.peso_objetivo_kg)
                : null;
            return (
              <li key={se.id} className="flex items-center justify-between text-[13px]">
                <span className="text-text-primary">
                  {ejercicioNombre(se.ejercicio_id) ?? `Ejercicio ${se.ejercicio_id}`}
                </span>
                <span className="text-text-secondary tabular">
                  {se.series}×{se.reps}
                  {se.peso_kg ? ` · ${se.peso_kg}kg` : ""}
                  {se.rpe ? ` · RPE ${se.rpe}` : ""}
                  {se.dolor_lumbar ? " · lumbar" : ""}
                  {deltaPeso !== null &&
                    ` · obj ${objetivo!.peso_objetivo_kg}kg (Δ${deltaPeso > 0 ? "+" : ""}${deltaPeso})`}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// RPE y duracion siempre; peso solo si la serie real matchea una planeada
// por ejercicio (arriba, junto a cada serie) — serie_plan es opcional.
function DeltaPlan({ sesion, plan }: { sesion: Sesion; plan: SesionPlan }) {
  const deltaDuracion =
    plan.duracion_min_est !== null ? sesion.duracion_min - plan.duracion_min_est : null;
  const deltaRpe = plan.rpe_objetivo !== null ? sesion.rpe - plan.rpe_objetivo : null;

  if (deltaDuracion === null && deltaRpe === null) return null;

  return (
    <p className="mt-1 text-[11px] text-text-secondary">
      Plan: {plan.rpe_objetivo !== null && `RPE ${plan.rpe_objetivo}`}
      {plan.rpe_objetivo !== null && plan.duracion_min_est !== null ? " · " : ""}
      {plan.duracion_min_est !== null && `${plan.duracion_min_est} min`}
      {" · Δ "}
      {[
        deltaRpe !== null && `RPE ${deltaRpe > 0 ? "+" : ""}${deltaRpe}`,
        deltaDuracion !== null && `${deltaDuracion > 0 ? "+" : ""}${deltaDuracion} min`,
      ]
        .filter(Boolean)
        .join(" · ")}
    </p>
  );
}
