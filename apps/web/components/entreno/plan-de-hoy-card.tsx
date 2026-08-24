"use client";

import { useState } from "react";
import { BentoCard } from "@/components/ui/bento-card";
import { SelectorSesionSemana } from "@/components/entreno/selector-sesion-semana";
import {
  useEjercicios,
  useTiposSesion,
  type Sesion,
  type SesionPlan,
} from "@/lib/api/hooks";

type Props = {
  planesDeHoy: SesionPlan[];
  sesionesDeHoy: Sesion[];
  planesDeLaSemana: SesionPlan[];
  onEmpezar: (plan: SesionPlan | null) => void;
  onVerSesion: (sesionId: string) => void;
};

/**
 * La tarjeta que manda en la pantalla Entreno. Tres estados excluyentes:
 * hay plan pendiente para hoy, ya se registro la sesion, o no hay plan.
 *
 * Reemplaza al empty state "Aun no hay sesiones hoy" de SesionesList, que
 * solo miraba sesiones REALES y por eso nunca mostraba la planificacion
 * aunque el JSON se hubiera importado bien.
 */
export function PlanDeHoyCard({
  planesDeHoy,
  sesionesDeHoy,
  planesDeLaSemana,
  onEmpezar,
  onVerSesion,
}: Props) {
  const tipos = useTiposSesion();
  const ejercicios = useEjercicios();
  const [eligiendoOtra, setEligiendoOtra] = useState(false);

  const nombreTipo = (id: number) =>
    tipos.data?.find((t) => t.id === id)?.nombre ?? "Sesion";

  // Un plan con sesion real ya no es "de hoy pendiente": el backend lo dejo
  // en cumplido/movido, asi que alcanza con leer el estado.
  const pendiente = planesDeHoy.find((p) => p.estado === "pendiente") ?? null;
  const sesionDeHoy = sesionesDeHoy[0] ?? null;
  const planDeLaSesion =
    sesionDeHoy?.sesion_plan_id != null
      ? (planesDeLaSemana.find((p) => p.id === sesionDeHoy.sesion_plan_id) ?? null)
      : null;

  const otrasPendientes = planesDeLaSemana.filter(
    (p) => p.estado === "pendiente" && p.id !== pendiente?.id,
  );

  return (
    <BentoCard>
      <p className="mb-3 text-[11px] font-normal tracking-widest uppercase text-text-secondary">
        Plan de hoy
      </p>

      {sesionDeHoy ? (
        <SesionRegistrada
          sesion={sesionDeHoy}
          plan={planDeLaSesion}
          tipoNombre={nombreTipo(sesionDeHoy.tipo_sesion_id)}
          onVer={() => onVerSesion(sesionDeHoy.id)}
        />
      ) : pendiente ? (
        <PlanPendiente
          plan={pendiente}
          tipoNombre={nombreTipo(pendiente.tipo_sesion_id)}
          nombreEjercicio={(id) =>
            ejercicios.data?.find((e) => e.id === id)?.nombre ?? `Ejercicio ${id}`
          }
          onEmpezar={() => onEmpezar(pendiente)}
        />
      ) : (
        <SinPlan onLibre={() => onEmpezar(null)} />
      )}

      {!sesionDeHoy && otrasPendientes.length > 0 && (
        <button
          type="button"
          onClick={() => setEligiendoOtra(true)}
          className="mt-3 w-full rounded-full border border-border-subtle px-4 py-2.5 text-[13px] font-medium text-text-primary"
        >
          Hacer otra sesion de la semana
        </button>
      )}

      {eligiendoOtra && (
        <SelectorSesionSemana
          planes={otrasPendientes}
          onElegir={(plan) => {
            setEligiendoOtra(false);
            onEmpezar(plan);
          }}
          onCerrar={() => setEligiendoOtra(false)}
        />
      )}
    </BentoCard>
  );
}

function PlanPendiente({
  plan,
  tipoNombre,
  nombreEjercicio,
  onEmpezar,
}: {
  plan: SesionPlan;
  tipoNombre: string;
  nombreEjercicio: (id: number) => string;
  onEmpezar: () => void;
}) {
  const meta = [
    plan.duracion_min_est && `${plan.duracion_min_est} min`,
    plan.rpe_objetivo && `RPE objetivo ${plan.rpe_objetivo}`,
  ]
    .filter(Boolean)
    .join(" · ");

  const bloques = plan.bloques_planeados;
  const nombres = bloques.slice(0, 3).map((b) => nombreEjercicio(b.ejercicio_id));

  return (
    <>
      <p className="text-[20px] font-semibold text-text-primary">{tipoNombre}</p>
      {plan.objetivo && (
        <p className="mt-0.5 text-[14px] text-text-secondary">{plan.objetivo}</p>
      )}
      {meta && (
        <p className="mt-1 text-[11px] uppercase tracking-widest text-text-secondary">
          {meta}
        </p>
      )}

      {bloques.length > 0 && (
        <p className="mt-3 text-[13px] text-text-secondary">
          {bloques.length} bloque{bloques.length === 1 ? "" : "s"} ·{" "}
          {nombres.join(", ")}
          {bloques.length > nombres.length ? "…" : ""}
        </p>
      )}

      <button
        type="button"
        onClick={onEmpezar}
        className="mt-4 w-full rounded-full bg-accent px-4 py-3 text-[14px] font-semibold text-bg transition hover:bg-accent/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        Empezar sesion
      </button>
    </>
  );
}

function SesionRegistrada({
  sesion,
  plan,
  tipoNombre,
  onVer,
}: {
  sesion: Sesion;
  plan: SesionPlan | null;
  tipoNombre: string;
  onVer: () => void;
}) {
  return (
    <>
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-[20px] font-semibold text-text-primary">{tipoNombre}</p>
        <p className="text-[24px] font-bold tabular text-text-primary">
          {sesion.carga_srpe}
        </p>
      </div>
      <p className="mt-0.5 text-[11px] uppercase tracking-widest text-text-secondary">
        {sesion.duracion_min} min · RPE {sesion.rpe} · carga
      </p>

      {plan && (plan.duracion_min_est || plan.rpe_objetivo) && (
        <p className="mt-2 text-[13px] text-text-secondary">
          plan: {plan.duracion_min_est ?? "—"} min RPE {plan.rpe_objetivo ?? "—"} · real:{" "}
          {sesion.duracion_min} min RPE {sesion.rpe}
        </p>
      )}

      <button
        type="button"
        onClick={onVer}
        className="mt-4 w-full rounded-full border border-border-subtle px-4 py-2.5 text-[13px] font-medium text-text-primary"
      >
        Ver detalle
      </button>
    </>
  );
}

function SinPlan({ onLibre }: { onLibre: () => void }) {
  return (
    <>
      <p className="text-[16px] text-text-primary">Sin sesion planeada para hoy.</p>
      <button
        type="button"
        onClick={onLibre}
        className="mt-4 w-full rounded-full border border-border-subtle px-4 py-2.5 text-[13px] font-medium text-text-primary"
      >
        Registrar sesion libre
      </button>
    </>
  );
}
