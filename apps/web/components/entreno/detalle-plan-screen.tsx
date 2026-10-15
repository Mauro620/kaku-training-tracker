"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { BentoCard } from "@/components/ui/bento-card";
import { EmptyState } from "@/components/ui/empty-state";
import { DetalleEjercicioSheet } from "@/components/entreno/detalle-ejercicio-sheet";
import { FusionEjercicioDialog } from "@/components/entreno/fusion-ejercicio-dialog";
import {
  usePlanDetalle,
  useRecuperarPlan,
  useTiposSesion,
  type PlanDetalleRead,
  type BloquePlanDetalleRead,
  type TipoMedicion,
} from "@/lib/api/hooks";
import { formatearFechaLarga } from "@/lib/fecha";

type Props = { planId: number };

export function DetallePlanScreen({ planId }: Props) {
  const { data: plan, isLoading, error } = usePlanDetalle(planId);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-5 pt-[calc(env(safe-area-inset-top)+2rem)] pb-32">
        <div className="mb-4 h-8 w-32 animate-pulse rounded bg-surface-secondary" />
        <div className="flex flex-col gap-4">
          <div className="h-40 animate-pulse rounded-2xl bg-surface-secondary" />
          <div className="h-40 animate-pulse rounded-2xl bg-surface-secondary" />
          <div className="h-40 animate-pulse rounded-2xl bg-surface-secondary" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-5 pt-[calc(env(safe-area-inset-top)+2rem)] pb-32">
        <EmptyState
          title="Error al cargar el plan"
          description="No se pudo obtener la informacion de este plan."
          action={{ label: "Volver a Entreno", onClick: () => (window.location.href = "/entreno") }}
        />
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="mx-auto max-w-3xl px-5 pt-[calc(env(safe-area-inset-top)+2rem)] pb-32">
        <EmptyState
          title="Plan no encontrado"
          description="El plan que buscas no existe o fue eliminado."
          action={{ label: "Volver a Entreno", onClick: () => (window.location.href = "/entreno") }}
        />
      </div>
    );
  }

  return <DetallePlanContent plan={plan} />;
}

function DetallePlanContent({ plan }: { plan: PlanDetalleRead }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const tipos = useTiposSesion();
  const tipoNombre = tipos.data?.find((t) => t.id === plan.tipo_sesion_id)?.nombre ?? "Plan";

  const recuperar = useRecuperarPlan();
  const [ejercicioSheetOpen, setEjercicioSheetOpen] = useState<number | null>(null);
  const [fusionOrigenId, setFusionOrigenId] = useState<number | null>(null);

  const handleFusionarClick = (origenId: number) => {
    setEjercicioSheetOpen(null);
    setFusionOrigenId(origenId);
  };

  const handleFusionConfirm = async (_destinoId: number) => {
    await queryClient.invalidateQueries({ queryKey: ["planes"] });
    setFusionOrigenId(null);
  };

  return (
    <div className="mx-auto max-w-3xl px-5 pt-[calc(env(safe-area-inset-top)+2rem)] pb-32">
      {/* Header */}
      <button
        type="button"
        onClick={() => router.back()}
        className="mb-4 flex items-center gap-1 text-[13px] text-text-secondary"
      >
        <ChevronLeft size={16} /> Volver
      </button>

      <div className="mb-4">
        <div className="flex items-baseline justify-between gap-2">
          <p className="text-[20px] font-semibold text-text-primary">{tipoNombre}</p>
          <EstadoChip estado={plan.estado} />
        </div>
        <p className="mt-0.5 text-[14px] text-text-secondary">
          {plan.nombre ?? plan.objetivo ?? "Plan"}
        </p>
        {plan.ciclo && (
          <p className="mt-1 text-[11px] uppercase tracking-widest text-text-secondary">
            Ciclo {plan.ciclo.numero} · semana {plan.ciclo.semana} · {plan.ciclo.fase}
          </p>
        )}
        {plan.fecha_prevista && (
          <p className="mt-0.5 text-[14px] text-text-secondary">
            {formatearFechaLarga(plan.fecha_prevista)}
          </p>
        )}
        {plan.nota && (
          <div className="mt-3 rounded-xl bg-surface-secondary p-3 text-[14px] text-text-primary">
            {plan.nota}
          </div>
        )}
      </div>

      {/* Un descarte se puede deshacer: sin esto un toque accidental no tenia
          vuelta atras. */}
      {plan.estado === "descartado" && (
        <BentoCard className="mb-4">
          <p className="text-[14px] text-text-primary">Descartaste este plan.</p>
          <p className="mt-1 text-[13px] text-text-secondary">
            No cuenta para el cumplimiento. Si fue sin querer, puedes recuperarlo y
            vuelve a quedar pendiente.
          </p>
          <button
            type="button"
            onClick={() => recuperar.mutate(plan.id)}
            disabled={recuperar.isPending}
            className="mt-3 w-full rounded-full bg-accent px-4 py-3 text-[14px] font-semibold text-bg transition hover:bg-accent/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50"
          >
            {recuperar.isPending ? "Recuperando..." : "Recuperar plan"}
          </button>
          {recuperar.isError && (
            <p className="mt-2 text-[13px] text-state-danger">
              No se pudo recuperar el plan. Intenta de nuevo.
            </p>
          )}
        </BentoCard>
      )}

      {/* Resumen meta */}
      {(plan.duracion_min_est || plan.rpe_objetivo) && (
        <BentoCard>
          <div className="grid grid-cols-2 gap-4">
            {plan.duracion_min_est && (
              <div className="text-center">
                <p className="text-[11px] uppercase tracking-widest text-text-secondary">
                  Duracion
                </p>
                <p className="mt-1 text-[20px] font-bold tabular text-text-primary">
                  {plan.duracion_min_est} min
                </p>
              </div>
            )}
            {plan.rpe_objetivo && (
              <div className="text-center">
                <p className="text-[11px] uppercase tracking-widest text-text-secondary">
                  RPE objetivo
                </p>
                <p className="mt-1 text-[20px] font-bold tabular text-text-primary">
                  {plan.rpe_objetivo}
                </p>
              </div>
            )}
          </div>
        </BentoCard>
      )}

      {/* Bloques planeados */}
      <div className="mt-6">
        <p className="mb-3 text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Bloques planeados
        </p>
        {plan.bloques_planeados.length === 0 ? (
          <EmptyState
            title="Este plan no tiene bloques"
            description="No hay ejercicios asignados a este plan."
          />
        ) : (
          <div className="flex flex-col gap-2">
            {plan.bloques_planeados.map((bloque) => (
              <BloqueCard
                key={bloque.id}
                bloque={bloque}
                onVerEjercicio={() => setEjercicioSheetOpen(bloque.ejercicio.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Sheet de detalle de ejercicio */}
      {ejercicioSheetOpen !== null && (
        <DetalleEjercicioSheet
          ejercicioId={ejercicioSheetOpen}
          open={true}
          onClose={() => setEjercicioSheetOpen(null)}
          onFusionarClick={handleFusionarClick}
        />
      )}

      {/* Dialog de fusion */}
      {fusionOrigenId !== null && (
        <FusionEjercicioDialog
          origenId={fusionOrigenId}
          open={true}
          onClose={() => setFusionOrigenId(null)}
          onConfirm={handleFusionConfirm}
        />
      )}
    </div>
  );
}

function EstadoChip({ estado }: { estado: PlanDetalleRead["estado"] }) {
  const colorClass =
    estado === "pendiente"
      ? "text-text-secondary"
      : estado === "cumplido"
        ? "text-state-positive"
        : estado === "movido"
          ? "text-state-warning"
          : "text-state-danger";

  return (
    <span className={`text-[13px] ${colorClass}`}>
      {estado}
    </span>
  );
}

function BloqueCard({
  bloque,
  onVerEjercicio,
}: {
  bloque: BloquePlanDetalleRead;
  onVerEjercicio: () => void;
}) {
  const { ejercicio } = bloque;
  const tipoMedicion = ejercicio.tipo_medicion;
  const valorString = renderValor(bloque, tipoMedicion);

  return (
    <div className="rounded-xl border border-border-subtle px-4 py-3">
      <div className="flex items-start justify-between gap-2">
        <button
          type="button"
          onClick={onVerEjercicio}
          className="text-left text-[15px] font-semibold text-text-primary hover:underline"
        >
          {ejercicio.nombre}
        </button>
      </div>

      {ejercicio.descripcion && (
        <p className="mt-1 text-[12px] text-text-secondary">{ejercicio.descripcion}</p>
      )}

      <div className="mt-1.5">
        <p className="text-[13px] text-text-secondary">{valorString}</p>
      </div>

      {bloque.nota && (
        <div className="mt-2 rounded-lg bg-surface-secondary px-3 py-2 text-[13px] italic text-text-secondary">
          {bloque.nota}
        </div>
      )}
    </div>
  );
}

function renderValor(bloque: BloquePlanDetalleRead, tipo: TipoMedicion): string {
  const { series, reps_min, reps_max, peso_objetivo_kg, distancia_objetivo_m, duracion_objetivo_s } = bloque;

  switch (tipo) {
    case "carga":
      return `${series ?? "−"}×${reps_min ?? "−"}-${reps_max ?? "−"} @ ${peso_objetivo_kg !== null ? `${peso_objetivo_kg}kg` : "-kg"}`;
    case "distancia":
      return `${reps_min ?? "−"}×${distancia_objetivo_m !== null ? `${distancia_objetivo_m}m` : "-m"}`;
    case "tiempo":
      return `${series ?? "−"}×${duracion_objetivo_s !== null ? `${duracion_objetivo_s}s` : "-s"}`;
    case "tecnica":
      return `${reps_min ?? duracion_objetivo_s ?? "−"}`;
  }
}
