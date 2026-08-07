import type { ReactNode } from "react";
import { BottomNav } from "@/components/nav/bottom-nav";
import { SwipeNav } from "@/components/nav/swipe-nav";
import { SyncChip } from "@/components/sync-chip";

/**
 * Layout del grupo (tabs): el bottom nav aparece en cada pestaña, y un swipe
 * horizontal cambia de pestaña como en una app nativa. El padding-bottom del
 * contenido lo deja respirar para no quedar tapado por el nav.
 *
 * SyncChip (Fase 5): chip flotante con el estado de la cola de salida.
 * Solo aparece si hay pendientes o fallidos; no agrega ruido cuando
 * todo esta sincronizado.
 */
export default function TabsLayout({ children }: { children: ReactNode }) {
  return (
    <SwipeNav>
      {children}
      <BottomNav />
      <SyncChip />
    </SwipeNav>
  );
}
