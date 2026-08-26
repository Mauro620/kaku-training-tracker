"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, MoreVertical } from "lucide-react";
import { BentoCard } from "@/components/ui/bento-card";
import { EstadoPlanPill } from "@/components/entreno/estado-plan-pill";
import { DetalleEjercicioSheet } from "@/components/entreno/detalle-ejercicio-sheet";
import {
  useDescartarPlan,
  useEjerciciosList,
  useTiposSesion,
  type SesionPlan,
} from "@/lib/api/hooks";
import { NOMBRE_DIA } from "@/lib/semana";

type Props = { planes: SesionPlan[]; diaDeHoy: number | null };

/**
 * El resto de la semana planeada. Ordena por dia, no por id: el JSON puede
 * traer las sesiones en cualquier orden y lo que importa es el calendario.
 * Tocar una fila despliega sus bloques ahi mismo, sin navegar.
 */
export function RestoDeLaSemana({ planes, diaDeHoy }: Props) {
  const tipos = useTiposSesion();
  const ejercicios = useEjerciciosList();
  const [abierto, setAbierto] = useState<number | null>(null);
  const [menu, setMenu] = useState<number | null>(null);
  const [ejercicioSheetId, setEjercicioSheetId] = useState<number | null>(null);
  const descartar = useDescartarPlan();

  const otros = planes
    .filter((p) => p.dia_sugerido !== diaDeHoy)
    .sort((a, b) => (a.dia_sugerido ?? 99) - (b.dia_sugerido ?? 99));

  if (otros.length === 0) return null;

  return (
    <BentoCard>
      <p className="mb-3 text-[11px] font-normal tracking-widest uppercase text-text-secondary">
        Resto de la semana
      </p>

      <div className="flex flex-col gap-2">
        {otros.map((p) => {
          const nombre =
            tipos.data?.find((t) => t.id === p.tipo_sesion_id)?.nombre ?? "Sesion";
          const dia = p.dia_sugerido !== null ? NOMBRE_DIA[p.dia_sugerido] : "Sin dia";
          const estaAbierto = abierto === p.id;

          return (
            <div
              key={p.id}
              className="rounded-bento border border-border-subtle bg-surface-secondary"
            >
              <div className="flex items-center gap-2 p-3">
                <button
                  type="button"
                  onClick={() => setAbierto(estaAbierto ? null : p.id)}
                  className="flex min-w-0 flex-1 items-center gap-3 text-left"
                >
                  <span className="w-16 shrink-0 text-[11px] uppercase tracking-widest text-text-secondary">
                    {dia}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[14px] font-medium text-text-primary">
                    {nombre}
                  </span>
                  <EstadoPlanPill estado={p.estado} compacto />
                  {estaAbierto ? (
                    <ChevronUp size={16} className="shrink-0 text-text-secondary" />
                  ) : (
                    <ChevronDown size={16} className="shrink-0 text-text-secondary" />
                  )}
                </button>

                {p.estado === "pendiente" && (
                  <button
                    type="button"
                    onClick={() => setMenu(menu === p.id ? null : p.id)}
                    aria-label="Acciones"
                    className="shrink-0 p-1"
                  >
                    <MoreVertical size={16} className="text-text-secondary" />
                  </button>
                )}
              </div>

              {menu === p.id && (
                <div className="border-t border-border-subtle px-3 py-2">
                  <button
                    type="button"
                    disabled={descartar.isPending}
                    onClick={() => {
                      descartar.mutate(p.id);
                      setMenu(null);
                    }}
                    className="text-[13px] text-text-secondary disabled:opacity-50"
                  >
                    Descartar esta sesion
                  </button>
                </div>
              )}

              {estaAbierto && (
                <ul className="flex flex-col gap-1 border-t border-border-subtle px-3 py-2">
                  {p.objetivo && (
                    <li className="mb-1 text-[13px] text-text-secondary">
                      {p.objetivo}
                    </li>
                  )}
                  {p.bloques_planeados.length === 0 ? (
                    <li className="text-[12px] text-text-secondary">
                      Sin bloques planeados.
                    </li>
                  ) : (
                    p.bloques_planeados.map((b) => {
                      const item = ejercicios.data?.items.find((e) => e.id === b.ejercicio_id);
                      return (
                        <li
                          key={b.id}
                          className="flex items-center justify-between gap-2 text-[13px]"
                        >
                          <button
                            type="button"
                            onClick={() => setEjercicioSheetId(b.ejercicio_id)}
                            className="min-w-0 flex-1 truncate text-left text-text-primary hover:underline"
                          >
                            {item?.nombre ?? `Ejercicio ${b.ejercicio_id}`}
                          </button>
                          <span className="shrink-0 tabular text-text-secondary">
                            {describirObjetivo(b)}
                          </span>
                        </li>
                      );
                    })
                  )}
                </ul>
              )}
            </div>
          );
        })}
      </div>

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

function describirObjetivo(b: SesionPlan["bloques_planeados"][number]): string {
  const reps =
    b.reps_min !== null && b.reps_max !== null
      ? b.reps_min === b.reps_max
        ? `${b.reps_min}`
        : `${b.reps_min}-${b.reps_max}`
      : null;

  return (
    [
      b.series !== null && reps !== null ? `${b.series}x${reps}` : (reps ?? null),
      b.peso_objetivo_kg !== null && `${b.peso_objetivo_kg} kg`,
      b.distancia_objetivo_m !== null && `${b.distancia_objetivo_m} m`,
      b.duracion_objetivo_s !== null && `${b.duracion_objetivo_s}s`,
    ]
      .filter(Boolean)
      .join(" · ") || "—"
  );
}
