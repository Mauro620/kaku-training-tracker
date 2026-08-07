"use client";

import { useState } from "react";
import { BentoCard } from "@/components/ui/bento-card";
import { SesionDetalle } from "@/components/entreno/sesion-detalle";
import {
  useSesionesDeFecha,
  useTiposSesion,
  useEjercicios,
  type Bloque,
  type BloquePlan,
  type Sesion,
  type SesionPlan,
} from "@/lib/api/hooks";

type Props = { fecha: string; planes: SesionPlan[] };

/**
 * Lista de las sesiones registradas en la fecha (ROADMAP §4).
 * El backend carga los bloques via selectinload asi que no hay N+1.
 * Tocar una sesion abre el detalle/edicion (sesion-detalle.tsx).
 */
export function SesionesList({ fecha, planes }: Props) {
  const { data, isLoading } = useSesionesDeFecha(fecha);
  const tipos = useTiposSesion();
  const ejercicios = useEjercicios();
  const [sesionAbiertaId, setSesionAbiertaId] = useState<string | null>(null);

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
              onAbrir={() => setSesionAbiertaId(s.id)}
            />
          ))}
        </div>
      )}

      {sesionAbiertaId && (
        <SesionDetalle
          sesionId={sesionAbiertaId}
          onCerrar={() => setSesionAbiertaId(null)}
        />
      )}
    </BentoCard>
  );
}

function SesionCard({
  sesion,
  plan,
  tipoNombre,
  ejercicioNombre,
  onAbrir,
}: {
  sesion: Sesion;
  plan: SesionPlan | null;
  tipoNombre: string | undefined;
  ejercicioNombre: (id: number) => string | undefined;
  onAbrir: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onAbrir}
      className="w-full rounded-bento border border-border-subtle bg-surface-secondary p-4 text-left"
    >
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[16px] font-semibold text-text-primary">
          {tipoNombre ?? "Sesion"}
        </p>
        <p className="text-[20px] font-bold tabular text-text-primary">{sesion.carga_srpe}</p>
      </div>
      <p className="text-[11px] uppercase tracking-widest text-text-secondary">
        {sesion.duracion_min} min · RPE {sesion.rpe}
        {sesion.bloques.length > 0
          ? ` · ${sesion.bloques.length} bloque${sesion.bloques.length === 1 ? "" : "s"}`
          : " · sin bloques"}
      </p>
      {plan && <DeltaPlan sesion={sesion} plan={plan} />}
      {sesion.nota && (
        <p className="mt-2 text-[13px] text-text-secondary">{sesion.nota}</p>
      )}
      {sesion.bloques.length > 0 ? (
        <ul className="mt-3 flex flex-col gap-1 border-t border-border-subtle pt-2">
          {sesion.bloques.map((b) => {
            // Match por ejercicio: el orden del bloque real no tiene por
            // que coincidir con el del planeado (se puede reordenar en el
            // momento sin que eso invalide el objetivo).
            const objetivo = plan?.bloques_planeados.find(
              (bp) => bp.ejercicio_id === b.ejercicio_id,
            );
            return (
              <li key={b.id} className="flex items-center justify-between text-[13px]">
                <span className="text-text-primary">
                  {ejercicioNombre(b.ejercicio_id) ?? `Ejercicio ${b.ejercicio_id}`}
                </span>
                <span className="text-text-secondary tabular">
                  <DescripcionBloque bloque={b} objetivo={objetivo} />
                </span>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="mt-3 text-[12px] text-text-secondary">Sesion sin bloques.</p>
      )}
    </button>
  );
}

// Formatea segun que campos trae el bloque real (series/reps/peso, o
// reps/distancia, o duracion, o tecnica con calidad — REGLAS_NEGOCIO §15),
// y agrega el delta contra el objetivo planeado cuando aplica.
function DescripcionBloque({
  bloque,
  objetivo,
}: {
  bloque: Bloque;
  objetivo: BloquePlan | undefined;
}) {
  const partes: string[] = [];
  if (bloque.series !== null && bloque.reps !== null) {
    partes.push(`${bloque.series}×${bloque.reps}`);
  } else if (bloque.reps !== null) {
    partes.push(`${bloque.reps} reps`);
  }
  if (bloque.peso_kg) partes.push(`${bloque.peso_kg}kg`);
  if (bloque.distancia_m) partes.push(`${bloque.distancia_m}m`);
  if (bloque.duracion_s !== null) partes.push(`${bloque.duracion_s}s`);
  if (bloque.calidad !== null) partes.push(`calidad ${bloque.calidad}/5`);
  if (bloque.rpe !== null) partes.push(`RPE ${bloque.rpe}`);
  if (bloque.dolor_lumbar) partes.push("lumbar");

  const deltas: string[] = [];
  if (objetivo?.peso_objetivo_kg && bloque.peso_kg) {
    const d = Number(bloque.peso_kg) - Number(objetivo.peso_objetivo_kg);
    deltas.push(`obj ${objetivo.peso_objetivo_kg}kg (Δ${d > 0 ? "+" : ""}${d})`);
  }
  if (objetivo?.distancia_objetivo_m && bloque.distancia_m) {
    const d = Number(bloque.distancia_m) - Number(objetivo.distancia_objetivo_m);
    deltas.push(`obj ${objetivo.distancia_objetivo_m}m (Δ${d > 0 ? "+" : ""}${d})`);
  }
  if (objetivo?.duracion_objetivo_s && bloque.duracion_s !== null) {
    const d = bloque.duracion_s - objetivo.duracion_objetivo_s;
    deltas.push(`obj ${objetivo.duracion_objetivo_s}s (Δ${d > 0 ? "+" : ""}${d})`);
  }

  return <>{[...partes, ...deltas].join(" · ")}</>;
}

// RPE y duracion siempre; peso/distancia/duracion por bloque solo si el
// bloque real matchea un objetivo planeado por ejercicio (arriba, junto a
// cada bloque) — bloque_plan es opcional.
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
