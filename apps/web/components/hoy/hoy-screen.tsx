"use client";

import { EstadoCard } from "@/components/hoy/estado-card";
import { SuenoCard } from "@/components/hoy/sueno-card";
import { BienestarCard } from "@/components/hoy/bienestar-card";
import { HidratacionCard } from "@/components/hoy/hidratacion-card";
import { HabitosCard } from "@/components/hoy/habitos-card";
import { useFechaDeRegistro } from "@/lib/fecha";

/**
 * Pantalla Hoy (ROADMAP §3, DESIGN.md §4.1).
 * Composición: EstadoCard full-width arriba, Sueño+Bienestar en fila de
 * dos, Hidratación y Hábitos full-width al final.
 */
export function HoyScreen() {
  const fecha = useFechaDeRegistro();
  return (
    <div className="flex flex-col gap-4 pb-32">
      <EstadoCard />
      <div className="flex flex-col md:flex-row gap-4">
        <SuenoCard fecha={fecha} />
        <BienestarCard fecha={fecha} />
      </div>
      <HidratacionCard fecha={fecha} />
      <HabitosCard fecha={fecha} />
    </div>
  );
}
