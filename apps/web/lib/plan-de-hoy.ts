import type { Sesion, SesionPlan } from "@/lib/api/hooks";

// Logica pura de la tarjeta "Plan de hoy". Vive fuera del .tsx por la misma
// razon que lib/importar-plan.ts (sin jsdom, vitest no transforma JSX).

export type PlanDeHoy = {
  /** Sesiones reales de hoy, todas: un dia puede tener varias (ej. activacion + partido). */
  sesiones: Sesion[];
  /** Planes de hoy que siguen sin ejecutarse ni descartarse. El primero es el principal. */
  pendientes: SesionPlan[];
  /** Planes de hoy que el usuario descarto. Se muestran apagados, no desaparecen. */
  descartados: SesionPlan[];
  /** Pendientes de OTROS dias de la semana, para "hacer otra sesion". */
  otrasPendientes: SesionPlan[];
};

// Antes la tarjeta tomaba `sesionesDeHoy[0]` y, con una sola sesion registrada,
// escondia el plan pendiente y el boton de otra sesion: con dos planes el mismo
// dia (activacion + partido) la segunda no se podia iniciar. Aqui ninguna
// sesion tapa a los planes que quedan.
export function resolverPlanDeHoy(
  planesDeHoy: SesionPlan[],
  sesionesDeHoy: Sesion[],
  planesDeLaSemana: SesionPlan[],
): PlanDeHoy {
  // Un plan con sesion real ya no esta pendiente (el backend lo deja en
  // cumplido/movido), pero se excluye tambien por id por si el estado llega
  // desfasado de la lista de sesiones (offline, refetch a medias).
  const ejecutados = new Set(
    sesionesDeHoy.map((s) => s.sesion_plan_id).filter((id): id is number => id !== null),
  );
  const idsDeHoy = new Set(planesDeHoy.map((p) => p.id));
  return {
    sesiones: sesionesDeHoy,
    pendientes: planesDeHoy.filter((p) => p.estado === "pendiente" && !ejecutados.has(p.id)),
    descartados: planesDeHoy.filter((p) => p.estado === "descartado"),
    otrasPendientes: planesDeLaSemana.filter(
      (p) => p.estado === "pendiente" && !idsDeHoy.has(p.id) && !ejecutados.has(p.id),
    ),
  };
}
