"use client";

import { useState } from "react";
import Link from "next/link";
import { BentoCard } from "@/components/ui/bento-card";
import { SelectorSesionSemana } from "@/components/entreno/selector-sesion-semana";
import { DetalleEjercicioSheet } from "@/components/entreno/detalle-ejercicio-sheet";
import {
  useDescartarPlan,
  useEjerciciosList,
  useTiposSesion,
  type Sesion,
  type SesionPlan,
} from "@/lib/api/hooks";
import { resolverPlanDeHoy } from "@/lib/plan-de-hoy";

type Props = {
  planesDeHoy: SesionPlan[];
  sesionesDeHoy: Sesion[];
  planesDeLaSemana: SesionPlan[];
  onEmpezar: (plan: SesionPlan | null) => void;
  onVerSesion: (sesionId: string) => void;
};

/**
 * La tarjeta que manda en la pantalla Entreno. Un dia puede tener varias
 * sesiones (ej. activacion + partido): se muestran las ya registradas, el plan
 * que sigue pendiente y los descartados; ninguna tapa a las demas.
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
  const ejercicios = useEjerciciosList();
  const [eligiendoOtra, setEligiendoOtra] = useState(false);
  const [ejercicioSheetId, setEjercicioSheetId] = useState<number | null>(null);

  const nombreTipo = (id: number) =>
    tipos.data?.find((t) => t.id === id)?.nombre ?? "Sesion";

  const descartar = useDescartarPlan();
  const { sesiones, pendientes, descartados, otrasPendientes } = resolverPlanDeHoy(
    planesDeHoy,
    sesionesDeHoy,
    planesDeLaSemana,
  );
  const principal = pendientes[0] ?? null;
  const tambienHoy = pendientes.slice(1);
  const planDe = (sesion: Sesion) =>
    sesion.sesion_plan_id != null
      ? (planesDeLaSemana.find((p) => p.id === sesion.sesion_plan_id) ?? null)
      : null;
  const nombreEjercicio = (id: number) =>
    ejercicios.data?.items.find((e) => e.id === id)?.nombre ?? `Ejercicio ${id}`;

  return (
    <BentoCard>
      <p className="mb-3 text-[11px] font-normal tracking-widest uppercase text-text-secondary">
        Plan de hoy
      </p>

      {sesiones.map((sesion) => (
        <div key={sesion.id} className="mb-4 border-b border-border-subtle pb-4">
          <SesionRegistrada
            sesion={sesion}
            plan={planDe(sesion)}
            tipoNombre={nombreTipo(sesion.tipo_sesion_id)}
            onVer={() => onVerSesion(sesion.id)}
          />
        </div>
      ))}

      {principal ? (
        <PlanPendiente
          plan={principal}
          etiqueta={sesiones.length > 0 ? "Sigue" : null}
          tipoNombre={nombreTipo(principal.tipo_sesion_id)}
          nombreEjercicio={nombreEjercicio}
          onAbrirEjercicio={(id) => setEjercicioSheetId(id)}
          onEmpezar={() => onEmpezar(principal)}
          onDescartar={() => descartar.mutate(principal.id)}
          descartando={descartar.isPending}
        />
      ) : sesiones.length === 0 ? (
        <SinPlan onLibre={() => onEmpezar(null)} />
      ) : (
        <button
          type="button"
          onClick={() => onEmpezar(null)}
          className="w-full rounded-full border border-border-subtle px-4 py-2.5 text-[13px] font-medium text-text-primary"
        >
          Registrar otra sesion
        </button>
      )}

      {tambienHoy.length > 0 && (
        <ul className="mt-4 flex flex-col gap-2">
          {tambienHoy.map((p) => (
            <li
              key={p.id}
              className="flex items-center justify-between gap-2 rounded-bento border border-border-subtle bg-surface-secondary px-4 py-2.5"
            >
              <span className="text-[14px] font-medium text-text-primary">
                {nombreTipo(p.tipo_sesion_id)}
              </span>
              <button
                type="button"
                onClick={() => onEmpezar(p)}
                className="text-[13px] font-medium text-text-primary underline"
              >
                Empezar
              </button>
            </li>
          ))}
        </ul>
      )}

      {descartados.length > 0 && (
        <ul className="mt-4 flex flex-col gap-1 text-[12px] text-text-secondary">
          {descartados.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-2">
              <span>Descartada: {nombreTipo(p.tipo_sesion_id)}</span>
              {/* El detalle es donde se recupera un descarte accidental. */}
              <Link href={`/entreno/planes/${p.id}`} className="text-text-primary underline">
                Ver / recuperar
              </Link>
            </li>
          ))}
        </ul>
      )}

      {otrasPendientes.length > 0 && (
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

      <DetalleEjercicioSheet
        ejercicioId={ejercicioSheetId}
        open={ejercicioSheetId !== null}
        onClose={() => setEjercicioSheetId(null)}
        fallback={
          ejercicioSheetId !== null
            ? ejercicios.data?.items.find((e) => e.id === ejercicioSheetId) ?? null
            : null
        }
      />
    </BentoCard>
  );
}

function PlanPendiente({
  plan,
  etiqueta,
  tipoNombre,
  nombreEjercicio,
  onAbrirEjercicio,
  onEmpezar,
  onDescartar,
  descartando,
}: {
  plan: SesionPlan;
  etiqueta: string | null;
  tipoNombre: string;
  nombreEjercicio: (id: number) => string;
  onAbrirEjercicio: (id: number) => void;
  onEmpezar: () => void;
  onDescartar: () => void;
  descartando: boolean;
}) {
  const meta = [
    plan.duracion_min_est && `${plan.duracion_min_est} min`,
    plan.rpe_objetivo && `RPE objetivo ${plan.rpe_objetivo}`,
  ]
    .filter(Boolean)
    .join(" · ");

  const bloques = plan.bloques_planeados;
  const visibles = bloques.slice(0, 3);
  const restantes = bloques.length - visibles.length;

  return (
    <>
      {etiqueta && (
        <p className="mb-1 text-[11px] uppercase tracking-widest text-text-secondary">{etiqueta}</p>
      )}
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
        <div className="mt-3 flex flex-wrap items-center gap-x-1 gap-y-1 text-[13px] text-text-secondary">
          <span>
            {bloques.length} bloque{bloques.length === 1 ? "" : "s"} ·{" "}
          </span>
          {visibles.map((b, idx) => (
            <span key={b.id} className="inline-flex items-center">
              <button
                type="button"
                onClick={() => onAbrirEjercicio(b.ejercicio_id)}
                className="text-text-primary hover:underline"
              >
                {nombreEjercicio(b.ejercicio_id)}
              </button>
              {idx < visibles.length - 1 && <span className="mx-1 text-text-secondary">,</span>}
            </span>
          ))}
          {restantes > 0 && <span className="text-text-secondary"> · +{restantes}</span>}
        </div>
      )}

      <button
        type="button"
        onClick={onEmpezar}
        className="mt-4 w-full rounded-full bg-accent px-4 py-3 text-[14px] font-semibold text-bg transition hover:bg-accent/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        Empezar sesion
      </button>
      <button
        type="button"
        onClick={onDescartar}
        disabled={descartando}
        className="mt-2 w-full rounded-full px-4 py-2 text-[13px] text-text-secondary disabled:opacity-50"
      >
        No la voy a hacer (descartar)
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
