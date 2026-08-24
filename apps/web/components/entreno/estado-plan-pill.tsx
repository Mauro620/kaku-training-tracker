import type { SesionPlan } from "@/lib/api/hooks";

// Estado del plan de sesion (Fase 4 R4, ver docs/schema.dbml Tabla sesion_plan
// y backend apps/api/app/models/entrenamiento/plan.py).
//   pendiente  -> todavia no se ejecuto
//   cumplido   -> existe una sesion real que lo referencia
//   movido     -> se ejecuto otro dia de la misma semana (lo resuelve el server)
//   descartado -> el usuario declaro que no se va a hacer
//
// Cada estado mapea a tokens del design system existentes en globals.css
// (DESIGN.md §1.2). No se introducen colores nuevos: se usan los roles ya
// aprobados (text-primary sobre fondos semanticos, igual que el resto del
// proyecto: ver components/hoy/hidratacion-card.tsx).

type Props = {
  estado: SesionPlan["estado"];
  compacto?: boolean;
};

const ETIQUETA: Record<SesionPlan["estado"], string> = {
  pendiente: "Pendiente",
  cumplido: "Cumplido",
  movido: "Movido",
  descartado: "Descartado",
};

// Variantes. Pendiente es neutro (gris tenue sobre canvas); cumplido /
// movido / descartado llevan el acento de su rol pero manteniendo legibilidad
// (texto blanco sobre color solido, mismo patron que StatusPill en DESIGN.md).
const COLOR: Record<SesionPlan["estado"], string> = {
  pendiente: "bg-surface-secondary text-text-secondary",
  cumplido: "bg-state-positive text-canvas",
  movido: "bg-state-warning text-canvas",
  descartado: "bg-state-focus text-canvas",
};

export function EstadoPlanPill({ estado, compacto = false }: Props) {
  const padding = compacto ? "px-2 py-0.5 text-[10px]" : "px-3 py-1 text-[11px]";
  return (
    <span
      className={`inline-flex items-center rounded-pill font-semibold uppercase tracking-widest ${padding} ${COLOR[estado]}`}
    >
      {ETIQUETA[estado]}
    </span>
  );
}
