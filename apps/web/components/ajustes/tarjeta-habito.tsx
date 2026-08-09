"use client";

import { ArrowDown, ArrowUp, Archive, Pencil, RotateCcw } from "lucide-react";

import type { Habito } from "@/lib/api/hooks";

interface Props {
  habito: Habito;
  /** Posicion actual entre los habitos activos. */
  indice: number;
  /** Total de habitos activos (para deshabilitar los extremos). */
  total: number;
  archivado?: boolean;
  onEditar: () => void;
  onArchivar: () => void;
  onMover: (dir: "arriba" | "abajo") => void;
  /** Solo cuando archivado=true: lo devuelve a activos. */
  onReactivar?: () => void;
}

/**
 * Tarjeta de un habito en la pantalla Ajustes.
 *
 * Stepper (no drag-and-drop): la lista es corta y los steppers son
 * inequivocos en mobile. Las teclas son nativas del navegador; los
 * botones explicitos funcionan en mobile sin library.
 */
export function TarjetaHabito({
  habito,
  indice,
  total,
  archivado,
  onEditar,
  onArchivar,
  onMover,
  onReactivar,
}: Props) {
  return (
    <li
      className={`flex items-center gap-  rounded-2xl border border-border bg-bg-card px-4 py-3 ${
        archivado ? "opacity-60" : ""
      }`}
    >
      {archivado ? (
        <>
          <span className="flex-1 text-[14px] text-text-secondary">
            {habito.nombre}
          </span>
          {onReactivar && (
            <button
              type="button"
              aria-label="Reactivar"
              title="Reactivar"
              onClick={onReactivar}
              className="rounded-md p-1.5 text-text-secondary transition hover:bg-bg-elevated hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <RotateCcw className="h-4 w-4" strokeWidth={2} aria-hidden />
            </button>
          )}
        </>
      ) : (
        <>
          <div className="flex flex-col">
            <button
              type="button"
              aria-label="Mover arriba"
              title="Mover arriba"
              disabled={indice === 0}
              onClick={() => onMover("arriba")}
              className="rounded-md p-1 text-text-secondary transition hover:bg-bg-elevated hover:text-text-primary disabled:opacity-30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <ArrowUp className="h-3.5 w-3.5" strokeWidth={2.5} aria-hidden />
            </button>
            <button
              type="button"
              aria-label="Mover abajo"
              title="Mover abajo"
              disabled={indice === total - 1}
              onClick={() => onMover("abajo")}
              className="rounded-md p-1 text-text-secondary transition hover:bg-bg-elevated hover:text-text-primary disabled:opacity-30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <ArrowDown className="h-3.5 w-3.5" strokeWidth={2.5} aria-hidden />
            </button>
          </div>
          <span className="flex-1 text-[14px] font-medium text-text-primary">
            {habito.nombre}
          </span>
        </>
      )}

      <button
        type="button"
        aria-label="Editar"
        title="Editar"
        onClick={onEditar}
        className="rounded-md p-1.5 text-text-secondary transition hover:bg-bg-elevated hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        <Pencil className="h-4 w-4" strokeWidth={2} aria-hidden />
      </button>

      {!archivado && (
        <button
          type="button"
          aria-label="Archivar"
          title="Archivar"
          onClick={onArchivar}
          className="rounded-md p-1.5 text-text-secondary transition hover:bg-bg-elevated hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <Archive className="h-4 w-4" strokeWidth={2} aria-hidden />
        </button>
      )}
    </li>
  );
}
