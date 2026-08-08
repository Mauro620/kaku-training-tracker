"use client";

import { BienestarCard } from "@/components/hoy/bienestar-card";
import { CierreDelDiaCard } from "@/components/hoy/cierre-del-dia-card";
import { HabitosCard } from "@/components/hoy/habitos-card";
import { HidratacionCard } from "@/components/hoy/hidratacion-card";
import { SuenoCard } from "@/components/hoy/sueno-card";
import { useFechaDeRegistro } from "@/lib/fecha";

/**
 * Pantalla Hoy (ROADMAP §3, DESIGN.md §4.1).
 *
 * Composicion vertical (H1-H3 de la revision de UI): el orden importa,
 * no es estetico. Sueño va primero porque es el cuello de botella del
 * usuario: si no durmio, el resto del dia arranca con handicap.
 *
 *   1. Cierre del dia  -> 4 segmentos, "3 de 4", "Falta X".
 *   2. Sueño           -> horas + objetivo + 14 dias + deuda 7d.
 *   3. Bienestar       -> 4 sliders de Hooper con direccion visible.
 *   4. Hidratacion     -> ml + objetivo a la barra.
 *   5. Habitos         -> checklist.
 *
 * Ningun numero aparece solo en estas tarjetas: cada valor viene con
 * su objetivo, su delta o su contexto.
 */
export function HoyScreen() {
  const fecha = useFechaDeRegistro();
  return (
    <div className="flex flex-col gap-4 pb-32">
      <CierreDelDiaCard fecha={fecha} />
      <SuenoCard fecha={fecha} />
      <BienestarCard fecha={fecha} />
      <HidratacionCard fecha={fecha} />
      <HabitosCard fecha={fecha} />
    </div>
  );
}
