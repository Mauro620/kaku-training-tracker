import type { ReactNode } from "react";
import { BottomNav } from "@/components/nav/bottom-nav";
import { SwipeNav } from "@/components/nav/swipe-nav";

/**
 * Layout del grupo (tabs): el bottom nav aparece en cada pestaña, y un swipe
 * horizontal cambia de pestaña como en una app nativa. El padding-bottom del
 * contenido lo deja respirar para no quedar tapado por el nav.
 */
export default function TabsLayout({ children }: { children: ReactNode }) {
  return (
    <SwipeNav>
      {children}
      <BottomNav />
    </SwipeNav>
  );
}
