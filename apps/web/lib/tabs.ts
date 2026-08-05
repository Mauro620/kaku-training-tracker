import { Calendar, Dumbbell, Home, UtensilsCrossed } from "lucide-react";

/**
 * Las cuatro pestañas (ROADMAP §7, DESIGN.md §2.1). Una sola fuente: la
 * usan tanto BottomNav como el gesto de swipe, para que el orden nunca
 * diverja entre los dos.
 */
export const TABS = [
  { href: "/hoy", etiqueta: "Hoy", icono: Home },
  { href: "/entreno", etiqueta: "Entreno", icono: Dumbbell },
  { href: "/cocina", etiqueta: "Cocina", icono: UtensilsCrossed },
  { href: "/progreso", etiqueta: "Progreso", icono: Calendar },
] as const;
