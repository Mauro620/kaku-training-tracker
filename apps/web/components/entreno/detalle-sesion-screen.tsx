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
  useSesion,
  type SesionDetalleRead,
  type BloqueDetalleRead,
  type TipoMedicion,
} from "@/lib/api/hooks";
import { formatearFechaLarga } from "@/lib/fecha";

type Props = { sesionId: string };

export function DetalleSesionScreen({ sesionId }: Props) {
  const { data: sesion, isLoading, error } = useSesion(sesionId);

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
          title="Error al cargar la sesion"
          description="No se pudo obtener la informacion de esta sesion."
          action={{ label: "Volver a Entreno", onClick: () => (window.location.href = "/entreno") }}
        />
      </div>
    );
  }

  if (!sesion) {
    return (
      <div className="mx-auto max-w-3xl px-5 pt-[calc(env(safe-area-inset-top)+2rem)] pb-32">
        <EmptyState
          title="Sesion no encontrada"
          description="La sesion que buscas no existe o fue eliminada."
          action={{ label: "Volver a Entreno", onClick: () => (window.location.href = "/entreno") }}
        />
      </div>
    );
  }

  return <DetalleSesionContent sesion={sesion} />;
}

function DetalleSesionContent({ sesion }: { sesion: SesionDetalleRead }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const plan = sesion.plan;

  // Estado para el sheet: null = cerrado, number = ejercicioId abierto
  const [ejercicioSheetOpen, setEjercicioSheetOpen] = useState<number | null>(null);
  // Estado para el dialog de fusion: null = cerrado, number = origenId abierto
  const [fusionOrigenId, setFusionOrigenId] = useState<number | null>(null);

  const handleFusionarClick = (origenId: number) => {
    setEjercicioSheetOpen(null); // cerrar sheet
    setFusionOrigenId(origenId); // abrir dialog con este origenId
  };

  const handleFusionConfirm = async (_destinoId: number) => {
    // Invalidar la query de sesion para que se recargue con los datos actualizados
    await queryClient.invalidateQueries({ queryKey: ["sesion"] });
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
          <p className="text-[20px] font-semibold text-text-primary">
            {sesion.tipo_sesion.nombre}
          </p>
          <p className="text-[24px] font-bold tabular text-text-primary">
            {sesion.carga_srpe}
          </p>
        </div>
        <p className="mt-0.5 text-[14px] text-text-secondary">
          {formatearFechaLarga(sesion.fecha)} · {sesion.duracion_min} min · RPE {sesion.rpe}
        </p>
        {plan && (
          <>
            <p className="mt-1 text-[14px] text-text-secondary">{plan.nombre}</p>
            {plan.ciclo && (
              <p className="mt-0.5 text-[11px] uppercase tracking-widest text-text-secondary">
                Ciclo {plan.ciclo.numero} · semana {plan.ciclo.semana} · {plan.ciclo.fase}
              </p>
            )}
            {plan.nota && (
              <div className="mt-3 rounded-xl bg-surface-secondary p-3 text-[14px] text-text-primary">
                {plan.nota}
              </div>
            )}
          </>
        )}
      </div>

      {/* Resumen con delta */}
      {plan && sesion.delta ? (
        <BentoCard>
          <div className="grid grid-cols-3 gap-4">
            <DeltaColumn
              label="Duracion"
              value={`${sesion.duracion_min} min`}
              delta={sesion.delta.duracion_min}
              deltaSuffix="min"
              colorRule={(d) => (d === 0 ? "yellow" : d < 0 ? "green" : "neutral")}
            />
            <DeltaColumn
              label="RPE"
              value={sesion.rpe.toString()}
              delta={sesion.delta.rpe}
              colorRule={(d) => (d >= 2 ? "yellow" : "neutral")}
            />
            <DeltaColumn
              label="Carga"
              value={sesion.carga_srpe.toString()}
              delta={sesion.delta.carga_srpe}
              colorRule={(d) => "neutral"}
            />
          </div>
        </BentoCard>
      ) : (
        <BentoCard>
          <div className="grid grid-cols-3 gap-4">
            <SimpleColumn label="Duracion" value={`${sesion.duracion_min} min`} />
            <SimpleColumn label="RPE" value={sesion.rpe.toString()} />
            <SimpleColumn label="Carga" value={sesion.carga_srpe.toString()} />
          </div>
        </BentoCard>
      )}

      {/* Bloques */}
      <div className="mt-6">
        <p className="mb-3 text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Bloques
        </p>
        {sesion.bloques.length === 0 && !plan ? (
          <EmptyState
            title="Sesion sin bloques"
            description="No se registraron bloques en esta sesion."
          />
        ) : (
          <div className="flex flex-col gap-2">
            {sesion.bloques.map((bloque) => (
              <BloqueCard
                key={bloque.id}
                bloque={bloque}
                onVerEjercicio={() => setEjercicioSheetOpen(bloque.ejercicio.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Bloques no ejecutados */}
      {sesion.bloques_no_ejecutados.length > 0 && (
        <div className="mt-6">
          <p className="mb-3 text-[11px] font-normal tracking-widest uppercase text-text-secondary">
            Bloques no ejecutados{" "}
            <span className="rounded-full bg-surface-secondary px-2 py-0.5 text-[10px]">
              {sesion.bloques_no_ejecutados.length}
            </span>
          </p>
          <div className="flex flex-col gap-2">
            {sesion.bloques_no_ejecutados.map((b, idx) => (
              <BloqueNoEjecutadoRow key={idx} bloque={b} />
            ))}
          </div>
        </div>
      )}

      {/* Molestias */}
      {sesion.molestias.length > 0 && (
        <div className="mt-6">
          <p className="mb-3 text-[11px] font-normal tracking-widest uppercase text-text-secondary">
            Molestias
          </p>
          <div className="flex flex-col gap-2">
            {sesion.molestias.map((m, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-xl border border-border-subtle px-4 py-3"
              >
                <span className="text-[14px] text-text-primary">{m.zona}</span>
                <span className="text-[13px] text-text-secondary">
                  intensidad {m.intensidad}/5
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

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

function DeltaColumn({
  label,
  value,
  delta,
  deltaSuffix = "",
  colorRule,
}: {
  label: string;
  value: string;
  delta: number | string | null;
  deltaSuffix?: string;
  colorRule: (delta: number) => "green" | "yellow" | "neutral";
}) {
  const deltaNum = typeof delta === "string" ? parseFloat(delta) : delta;
  const hasDelta = deltaNum !== null && deltaNum !== 0;
  const sign = deltaNum !== null && deltaNum > 0 ? "+" : "";
  const color = hasDelta ? colorRule(deltaNum) : "neutral";

  const colorClass =
    color === "green"
      ? "text-state-success"
      : color === "yellow"
        ? "text-warning"
        : "text-text-secondary";

  return (
    <div className="text-center">
      <p className="text-[11px] uppercase tracking-widest text-text-secondary">{label}</p>
      <p className="mt-1 text-[20px] font-bold tabular text-text-primary">{value}</p>
      {hasDelta && (
        <p className={`mt-0.5 text-[12px] tabular ${colorClass}`}>
          {sign}
          {deltaNum}
          {deltaSuffix && ` ${deltaSuffix}`}
        </p>
      )}
    </div>
  );
}

function SimpleColumn({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <p className="text-[11px] uppercase tracking-widest text-text-secondary">{label}</p>
      <p className="mt-1 text-[20px] font-bold tabular text-text-primary">{value}</p>
    </div>
  );
}

function BloqueCard({
  bloque,
  onVerEjercicio,
}: {
  bloque: BloqueDetalleRead;
  onVerEjercicio: () => void;
}) {
  const { ejercicio, objetivo, delta } = bloque;
  const tipoMedicion = ejercicio.tipo_medicion;

  // Determinar si el bloque tiene deltas no cero
  const hasNonZeroDelta =
    (delta.series !== null && delta.series !== 0) ||
    (delta.reps !== null && delta.reps !== 0) ||
    (delta.peso_kg !== null && parseFloat(delta.peso_kg) !== 0) ||
    (delta.distancia_m !== null && parseFloat(delta.distancia_m) !== 0) ||
    (delta.duracion_s !== null && delta.duracion_s !== 0);

  const paddingClass = hasNonZeroDelta ? "py-4" : "py-2.5";

  const valorString = renderValor(bloque, tipoMedicion);
  const objetivoString = objetivo ? renderObjetivo(objetivo, tipoMedicion) : null;

  // Renderizar delta chip si corresponde
  const deltaChip = renderDeltaChip(delta, tipoMedicion);

  return (
    <div
      className={`rounded-xl border border-border-subtle px-4 ${paddingClass}`}
    >
      <div className="flex items-start justify-between gap-2">
        <button
          type="button"
          onClick={onVerEjercicio}
          className="text-left text-[15px] font-semibold text-text-primary hover:underline"
        >
          {ejercicio.nombre}
        </button>
        {bloque.dolor_lumbar && (
          <span className="h-2 w-2 shrink-0 rounded-full bg-state-danger" />
        )}
      </div>

      {ejercicio.descripcion && (
        <p className="mt-1 text-[12px] text-text-secondary">{ejercicio.descripcion}</p>
      )}

      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        <p className="text-[13px] text-text-secondary">{valorString}</p>
        {deltaChip}
      </div>

      {bloque.nota && (
        <div className="mt-2 rounded-lg bg-surface-secondary px-3 py-2 text-[13px] italic text-text-secondary">
          {bloque.nota}
        </div>
      )}

      {objetivoString && (
        <p className="mt-1 text-[12px] text-text-secondary">Plan: {objetivoString}</p>
      )}
    </div>
  );
}

function renderValor(bloque: BloqueDetalleRead, tipo: TipoMedicion): string {
  const { series, reps, distancia_m, duracion_s, calidad, peso_kg, rpe } = bloque;

  switch (tipo) {
    case "carga":
      return `${series ?? "−"}×${reps ?? "−"} @ ${peso_kg !== null ? `${peso_kg}kg` : "−kg"}${rpe !== null ? ` · RPE ${rpe}` : ""}`;
    case "distancia":
      return `${reps ?? "−"}×${distancia_m !== null ? `${distancia_m}m` : "−m"}`;
    case "tiempo":
      return `${series ?? "−"}×${duracion_s !== null ? `${duracion_s}s` : "−s"}`;
    case "tecnica":
      return `${reps ?? duracion_s ?? "−"} (calidad ${calidad ?? "−"})`;
  }
}

function renderObjetivo(objetivo: any, tipo: TipoMedicion): string {
  const { series, reps_min, reps_max, peso_objetivo_kg, distancia_objetivo_m, duracion_objetivo_s } = objetivo;

  switch (tipo) {
    case "carga":
      return `${series ?? "−"}×${reps_min ?? "−"}-${reps_max ?? "−"} @ ${peso_objetivo_kg !== null ? `${peso_objetivo_kg}kg` : "−kg"}`;
    case "distancia":
      return `${reps_min ?? "−"}×${distancia_objetivo_m !== null ? `${distancia_objetivo_m}m` : "−m"}`;
    case "tiempo":
      return `${series ?? "−"}×${duracion_objetivo_s !== null ? `${duracion_objetivo_s}s` : "−s"}`;
    case "tecnica":
      return `${reps_min ?? duracion_objetivo_s ?? "−"}`;
  }
}

function renderDeltaChip(delta: any, tipo: TipoMedicion): React.ReactNode {
  // Solo mostrar delta si es no-null y no-cero
  const deltas = [];

  if (tipo === "carga") {
    if (delta.peso_kg !== null) {
      const val = parseFloat(delta.peso_kg);
      if (val !== 0) {
        const sign = val > 0 ? "+" : "";
        const color = val < 0 ? "text-warning" : "text-text-secondary";
        deltas.push(
          <span key="peso" className={`text-[11px] tabular ${color}`}>
            {sign}
            {val}kg
          </span>,
        );
      }
    }
    if (delta.reps !== null && delta.reps !== 0) {
      const sign = delta.reps > 0 ? "+" : "";
      deltas.push(
        <span key="reps" className="text-[11px] tabular text-text-secondary">
          {sign}
          {delta.reps} reps
        </span>,
      );
    }
  }

  if (deltas.length === 0) return null;
  return (
    <span className="rounded-full bg-surface-secondary px-2 py-0.5 text-[11px]">
      {deltas}
    </span>
  );
}

function BloqueNoEjecutadoRow({ bloque }: { bloque: any }) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-border-subtle bg-surface-secondary/50 px-4 py-3">
      <div>
        <p className="text-[13px] font-medium text-text-secondary">
          Orden {bloque.orden} · {bloque.ejercicio_nombre}
        </p>
        {bloque.objetivo && (
          <p className="mt-0.5 text-[12px] text-text-secondary">
            Plan: {renderObjetivo(bloque.objetivo, "carga")}
          </p>
        )}
      </div>
    </div>
  );
}
