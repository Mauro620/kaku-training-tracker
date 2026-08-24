import {
  useCiclos,
  usePlanesDeSemana,
  useSemanas,
  type Ciclo,
  type CicloSemana,
  type SesionPlan,
} from "@/lib/api/hooks";

/**
 * Resuelve "en que semana del ciclo estoy" para la pantalla Entreno.
 *
 * El rango de la semana N no es una columna: se deriva de `ciclo.fecha_inicio`
 * (REGLAS_NEGOCIO §13.1), y el backend ancla esa fecha al lunes ISO al crear
 * el ciclo. Por eso acá alcanza con dividir por 7 la distancia en dias: no
 * hace falta arrastrar ningun offset de dia de la semana.
 */
export function useSemanaActual(fecha: string) {
  const ciclos = useCiclos();
  const ciclo = ciclos.data ? elegirCicloActivo(ciclos.data, fecha) : null;

  const semanas = useSemanas(ciclo?.id ?? null);
  const numero = ciclo ? numeroDeSemana(ciclo.fecha_inicio, fecha) : null;
  const semana =
    numero === null ? null : (semanas.data?.find((s) => s.numero === numero) ?? null);

  const planes = usePlanesDeSemana(semana?.id ?? null);

  return {
    ciclo,
    semana,
    numeroSemana: numero,
    planes: planes.data ?? [],
    cargando: ciclos.isLoading || semanas.isLoading || planes.isLoading,
  };
}

/**
 * "Activo" es el ciclo no cerrado cuyo rango cubre `fecha`; si ninguno cubre
 * exacto (recien creado antes de empezar, o pasado de fecha_fin_prevista sin
 * cerrar) cae al no cerrado mas reciente, para no dejar la pantalla vacia sin
 * motivo. No mira `estado === "activo"`: nadie escribe ese valor todavia.
 */
export function elegirCicloActivo(ciclos: Ciclo[], fecha: string): Ciclo | null {
  const noCerrados = ciclos.filter((c) => c.estado !== "cerrado");
  if (noCerrados.length === 0) return null;

  const dentroDeRango = noCerrados.find(
    (c) => c.fecha_inicio <= fecha && fecha <= c.fecha_fin_prevista,
  );
  if (dentroDeRango) return dentroDeRango;

  return (
    [...noCerrados].sort((a, b) => (a.fecha_inicio < b.fecha_inicio ? 1 : -1))[0] ?? null
  );
}

/** 1-indexado, igual que `ciclo_semana.numero`. */
export function numeroDeSemana(fechaInicioCiclo: string, fecha: string): number {
  const dias = diferenciaEnDias(fechaInicioCiclo, fecha);
  return Math.floor(dias / 7) + 1;
}

/**
 * Offset del dia dentro de su semana del ciclo, comparable contra
 * `sesion_plan.dia_sugerido` (0=lunes..6=domingo).
 */
export function diaDeLaSemana(fechaInicioCiclo: string, fecha: string): number {
  return ((diferenciaEnDias(fechaInicioCiclo, fecha) % 7) + 7) % 7;
}

export const NOMBRE_DIA = [
  "Lunes",
  "Martes",
  "Miercoles",
  "Jueves",
  "Viernes",
  "Sabado",
  "Domingo",
] as const;

/**
 * Cuantas sesiones de la semana ya se hicieron. `movido` cuenta: se ejecuto
 * otro dia pero sigue cumpliendo la composicion semanal (PLAN_IMPORT.md §2.1).
 * `descartado` sale del denominador: el usuario declaro que no se hace, y no
 * tiene sentido que arrastre el progreso para abajo.
 */
export function progresoDeSemana(planes: SesionPlan[]): {
  hechas: number;
  total: number;
} {
  const cuentan = planes.filter((p) => p.estado !== "descartado");
  const hechas = cuentan.filter(
    (p) => p.estado === "cumplido" || p.estado === "movido",
  ).length;
  return { hechas, total: cuentan.length };
}

export type { CicloSemana };

// Mediodia para que un cambio de horario de verano no coma ni agregue un dia.
function diferenciaEnDias(desde: string, hasta: string): number {
  const a = new Date(`${desde}T12:00:00`);
  const b = new Date(`${hasta}T12:00:00`);
  return Math.round((b.getTime() - a.getTime()) / 86_400_000);
}
