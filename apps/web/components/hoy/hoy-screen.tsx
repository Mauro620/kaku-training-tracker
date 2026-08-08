"use client";

import { BienestarCard } from "@/components/hoy/bienestar-card";
import { CierreDelDiaCard } from "@/components/hoy/cierre-del-dia-card";
import { HabitosCard } from "@/components/hoy/habitos-card";
import { CierreSemanalCard } from "@/components/hoy/cierre-semanal-card";
import { HidratacionCard } from "@/components/hoy/hidratacion-card";
import { SuenoCard } from "@/components/hoy/sueno-card";
import { useFechaDeRegistro } from "@/lib/fecha";

/**
 * Pantalla Hoy (ROADMAP §3, DESIGN.md §4.1).
 *
 * Composicion vertical (H1-H3 + C de la revision de UI): el orden importa,
 * no es estetico. Sueño va primero porque es el cuello de botella del
 * usuario: si no durmio, el resto del dia arranca con handicap.
 *
 *   1. Cierre del dia  -> 4 segmentos, "3 de 4", "Falta X".
 *   2. Sueño           -> horas + objetivo + 14 dias + deuda 7d.
 *   3. Bienestar       -> 4 sliders de Hooper con direccion visible.
 *   4. Hidratacion     -> ml + objetivo a la barra.
 *   5. Habitos         -> checklist.
 *   6. Esta semana     -> grid 5x7 de cumplimiento.
 *
 * Ningun numero aparece solo en estas tarjetas: cada valor viene con
 * su objetivo, su delta o su contexto.
 */
/**
 * Semana ISO: lunes..domingo. La UI usa este rango para "esta semana"
 * (C de la revision de UI). Si la pantalla Hoy la abre un miercoles,
 * "esta semana" es lunes..domingo, no lunes..miercoles.
 */
function inicioSemana(fecha: string): string {
  const d = new Date(`${fecha}T12:00:00`);
  const dia = d.getDay(); // 0 = domingo, 1 = lunes, ..., 6 = sabado
  const offset = dia === 0 ? -6 : 1 - dia;
  d.setDate(d.getDate() + offset);
  return isoLocal(d);
}

function finSemana(fecha: string): string {
  const d = new Date(`${fecha}T12:00:00`);
  const dia = d.getDay();
  const offset = dia === 0 ? 0 : 7 - dia;
  d.setDate(d.getDate() + offset);
  return isoLocal(d);
}

function isoLocal(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function HoyScreen() {
  const fecha = useFechaDeRegistro();
  return (
    <div className="flex flex-col gap-4 pb-32">
      <CierreDelDiaCard fecha={fecha} />
      <SuenoCard fecha={fecha} />
      <BienestarCard fecha={fecha} />
      <HidratacionCard fecha={fecha} />
      <HabitosCard fecha={fecha} />
      <CierreSemanalCard
        desde={inicioSemana(fecha)}
        hasta={finSemana(fecha)}
      />
    </div>
  );
}
