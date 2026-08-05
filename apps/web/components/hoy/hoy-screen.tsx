import { EstadoCard } from "@/components/hoy/estado-card";
import { SuenoCard } from "@/components/hoy/sueno-card";
import { BienestarCard } from "@/components/hoy/bienestar-card";
import { HabitosCard } from "@/components/hoy/habitos-card";

/**
 * Pantalla Hoy (ROADMAP §3, DESIGN.md §4.1).
 * Composición: EstadoCard full-width arriba, Sueño+Bienestar en fila de
 * dos, Hábitos full-width al final.
 *
 * La fecha de hoy se calcula en local (no UTC) para alinear con el
 * invariante de sueño (REGLAS_NEGOCIO §6, PENDIENTES.md): el registro del
 * despertar pertenece a la fecha local de fin.
 */
export function HoyScreen() {
  const fecha = formatFechaLocal(new Date());
  return (
    <div className="flex flex-col gap-4 pb-32">
      <EstadoCard />
      <div className="flex flex-col md:flex-row gap-4">
        <SuenoCard fecha={fecha} />
        <BienestarCard fecha={fecha} />
      </div>
      <HabitosCard fecha={fecha} />
    </div>
  );
}

function formatFechaLocal(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}
