"use client";

import { X } from "lucide-react";
import { useTiposSesion, type SesionPlan } from "@/lib/api/hooks";
import { NOMBRE_DIA } from "@/lib/semana";

type Props = {
  planes: SesionPlan[];
  onElegir: (plan: SesionPlan) => void;
  onCerrar: () => void;
};

/**
 * Hoja para elegir otra sesion PENDIENTE de la semana y hacerla hoy.
 *
 * No hay intercambio de dias ni reasignacion: la sesion se crea con
 * `fecha = hoy` y `sesion_plan_id` = el plan elegido. Si ese plan tenia otro
 * `dia_sugerido`, el backend lo marca `movido` solo, y `movido` sigue
 * contando para el cumplimiento semanal. El plan de hoy queda `pendiente` y
 * se puede hacer cualquier otro dia.
 */
export function SelectorSesionSemana({ planes, onElegir, onCerrar }: Props) {
  const tipos = useTiposSesion();

  return (
    <div className="fixed inset-0 z-50 flex items-end bg-black/50" onClick={onCerrar}>
      <div
        className="max-h-[80vh] w-full overflow-y-auto rounded-t-bento bg-canvas px-5 pt-5 pb-[calc(env(safe-area-inset-bottom)+1.5rem)]"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="mb-4 flex items-center justify-between">
          <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
            Otra sesion de la semana
          </p>
          <button type="button" onClick={onCerrar} aria-label="Cerrar">
            <X size={18} className="text-text-secondary" />
          </button>
        </header>

        <p className="mb-4 text-[13px] text-text-secondary">
          Se registra con la fecha de hoy. El plan original queda marcado como
          movido y sigue contando para la semana.
        </p>

        <div className="flex flex-col gap-2">
          {planes.map((p) => {
            const nombre =
              tipos.data?.find((t) => t.id === p.tipo_sesion_id)?.nombre ?? "Sesion";
            const dia =
              p.dia_sugerido !== null ? NOMBRE_DIA[p.dia_sugerido] : "Sin dia";
            const meta = [
              p.duracion_min_est && `${p.duracion_min_est} min`,
              p.rpe_objetivo && `RPE ${p.rpe_objetivo}`,
              p.bloques_planeados.length > 0 &&
                `${p.bloques_planeados.length} bloques`,
            ]
              .filter(Boolean)
              .join(" · ");

            return (
              <button
                key={p.id}
                type="button"
                onClick={() => onElegir(p)}
                className="rounded-bento border border-border-subtle bg-surface-secondary p-4 text-left"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[15px] font-semibold text-text-primary">
                    {nombre}
                  </span>
                  <span className="text-[11px] uppercase tracking-widest text-text-secondary">
                    {dia}
                  </span>
                </div>
                {p.objetivo && (
                  <p className="mt-0.5 text-[13px] text-text-secondary">{p.objetivo}</p>
                )}
                {meta && (
                  <p className="mt-1 text-[11px] text-text-secondary">{meta}</p>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

