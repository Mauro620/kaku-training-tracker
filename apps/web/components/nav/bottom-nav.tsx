"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { TABS } from "@/lib/tabs";

/**
 * Bottom navigation de 4 pestañas (DESIGN.md §2.1).
 * Flotante inferior con backdrop-blur. El icono activo es blanco puro.
 * El lineamiento de tabs es de Fase 3; Entreno/Cocina/Progreso se
 * implementaron en sus respectivas fases (4/6/7).
 */
export function BottomNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-10 mx-auto flex max-w-3xl items-center justify-around bg-canvas/80 backdrop-blur-xl border-t border-border-subtle pb-[env(safe-area-inset-bottom)]">
      {TABS.map(({ href, icono: Icono, etiqueta }) => {
        const activa = pathname?.startsWith(href) ?? false;
        return (
          <Link
            key={href}
            href={href}
            aria-current={activa ? "page" : undefined}
            className={`flex flex-col items-center gap-1 py-3 px-4 ${
              activa ? "text-text-primary" : "text-text-secondary"
            }`}
          >
            <Icono size={22} strokeWidth={activa ? 2.4 : 1.8} aria-hidden />
            <span className="text-[10px] tracking-widest uppercase">{etiqueta}</span>
          </Link>
        );
      })}
    </nav>
  );
}
