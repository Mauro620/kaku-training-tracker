"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, CloudOff, Loader2 } from "lucide-react";

import {
  contarFallidos,
  contarPendientes,
  reintentar,
  descartar,
  tipoEvento,
} from "@/lib/sync/outbox";

import type { ItemOutbox } from "@/lib/sync/tipos";

/**
 * Chip de sincronizacion (Fase 5, ROADMAP §5).
 *
 * Tres estados visuales:
 *  - Sin pendientes ni fallidos: no se muestra (no agrega ruido).
 *  - Pendientes: muestra "Sincronizando N" con spinner.
 *  - Fallidos: muestra "N sin sincronizar" con icono de nube tachada;
 *    al tocar abre un mini-drawer con la lista y botones Reintentar /
 *    Descartar por item.
 *
 * Posicion: esquina inferior derecha, encima del bottom nav (z-20). El
 * nav usa z-10, asi que el chip queda visible sin pisar el contenido.
 *
 * Implementacion: poll cada 1.5s. No usamos `useLiveQuery` de Dexie para
 * no agregar una dep reactiva (zustand ya esta en el proyecto y no lo
 * necesitamos aca). Si en algun momento la UI quiere reactividad fina,
 * migrar.
 */
export function SyncChip() {
  const [pendientes, setPendientes] = useState(0);
  const [fallidos, setFallidos] = useState(0);
  const [mostrarFallidos, setMostrarFallidos] = useState(false);
  const [itemsFallidos, setItemsFallidos] = useState<ItemOutbox[]>([]);

  useEffect(() => {
    let cancelado = false;

    async function refrescar() {
      const [p, f] = await Promise.all([
        contarPendientes(),
        contarFallidos(),
      ]);
      if (cancelado) return;
      setPendientes(p);
      setFallidos(f);
    }

    void refrescar();
    const interval = setInterval(refrescar, 1_500);
    return () => {
      cancelado = true;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (!mostrarFallidos) return;
    let cancelado = false;

    async function cargar() {
      const { listar } = await import("@/lib/sync/outbox");
      const items = await listar();
      if (cancelado) return;
      setItemsFallidos(items.filter((i) => i.estado === "fallido"));
    }

    void cargar();
    return () => {
      cancelado = true;
    };
  }, [mostrarFallidos]);

  if (pendientes === 0 && fallidos === 0) return null;

  if (fallidos > 0 && !mostrarFallidos) {
    return (
      <button
        type="button"
        onClick={() => setMostrarFallidos(true)}
        className="fixed bottom-24 right-4 z-20 flex items-center gap-2 rounded-full border border-amber-700 bg-amber-950/90 px-3 py-2 text-xs text-amber-100 shadow-lg backdrop-blur"
        aria-label={`${fallidos} cambios sin sincronizar`}
      >
        <CloudOff size={14} aria-hidden />
        <span>{fallidos} sin sincronizar</span>
      </button>
    );
  }

  if (mostrarFallidos) {
    return (
      <div className="fixed bottom-24 right-4 left-4 z-20 max-h-[60vh] overflow-y-auto rounded-2xl border border-amber-700 bg-amber-950/95 p-4 text-amber-50 shadow-xl backdrop-blur md:left-auto md:max-w-sm">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-medium">Cambios sin sincronizar</h2>
          <button
            type="button"
            onClick={() => setMostrarFallidos(false)}
            className="text-amber-200 hover:text-amber-50"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>
        <ul className="mt-3 space-y-2">
          {itemsFallidos.map((item) => (
            <li
              key={item.id}
              className="rounded-lg border border-amber-800 bg-amber-950/60 p-2 text-xs"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-medium">{tipoEvento(item)}</div>
                  <div className="text-amber-200">{item.ultimo_error}</div>
                </div>
                <div className="flex shrink-0 gap-1">
                  <button
                    type="button"
                    onClick={() => reintentar(item.id)}
                    className="rounded border border-amber-700 px-2 py-1 hover:bg-amber-900"
                  >
                    Reintentar
                  </button>
                  <button
                    type="button"
                    onClick={() => descartar(item.id)}
                    className="rounded border border-amber-700 px-2 py-1 hover:bg-amber-900"
                  >
                    Descartar
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div
      className="fixed bottom-24 right-4 z-20 flex items-center gap-2 rounded-full border border-border-subtle bg-canvas/90 px-3 py-2 text-xs text-text-secondary shadow-lg backdrop-blur"
      aria-live="polite"
    >
      <Loader2 size={14} className="animate-spin" aria-hidden />
      <span>Sincronizando {pendientes}</span>
      <CheckCircle2 size={14} className="opacity-0" aria-hidden />
    </div>
  );
}