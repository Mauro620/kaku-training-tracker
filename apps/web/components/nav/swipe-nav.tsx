"use client";

import { useRouter, usePathname } from "next/navigation";
import { useRef, type ReactNode, type TouchEvent } from "react";
import { TABS } from "@/lib/tabs";

type Props = { children: ReactNode };

const UMBRAL_PX = 60;

/**
 * Swipe horizontal entre las cuatro pestañas, como una app nativa.
 *
 * Un scroll vertical normal no dispara nada: se descarta cuando el
 * desplazamiento vertical es mayor que el horizontal. Swipear más allá de
 * la primera o la última pestaña no hace nada (no da la vuelta).
 */
export function SwipeNav({ children }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const inicio = useRef<{ x: number; y: number } | null>(null);

  function onTouchStart(e: TouchEvent<HTMLDivElement>) {
    const toque = e.touches[0];
    inicio.current = toque ? { x: toque.clientX, y: toque.clientY } : null;
  }

  function onTouchEnd(e: TouchEvent<HTMLDivElement>) {
    const partida = inicio.current;
    inicio.current = null;
    if (!partida) return;

    const toque = e.changedTouches[0];
    if (!toque) return;

    const dx = toque.clientX - partida.x;
    const dy = toque.clientY - partida.y;
    if (Math.abs(dx) < UMBRAL_PX || Math.abs(dx) < Math.abs(dy)) return;

    const actual = TABS.findIndex((tab) => pathname?.startsWith(tab.href));
    if (actual === -1) return;

    // Swipe a la izquierda (dx negativo) avanza a la pestaña siguiente.
    const destino = TABS[actual + (dx < 0 ? 1 : -1)];
    if (destino) router.push(destino.href);
  }

  return (
    <div onTouchStart={onTouchStart} onTouchEnd={onTouchEnd} className="min-h-dvh">
      {children}
    </div>
  );
}
