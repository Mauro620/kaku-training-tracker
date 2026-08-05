import type { ReactNode } from "react";
import { BottomNav } from "@/components/nav/bottom-nav";

/**
 * Layout del grupo (tabs): el bottom nav aparece en cada pestaña. El
 * padding-bottom del contenido lo deja respirar para no quedar tapado.
 */
export default function TabsLayout({ children }: { children: ReactNode }) {
  return (
    <>
      {children}
      <BottomNav />
    </>
  );
}
