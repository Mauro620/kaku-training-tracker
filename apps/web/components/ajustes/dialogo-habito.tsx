"use client";

import { useEffect, useState } from "react";

import type { Habito } from "@/lib/api/hooks";

interface Props {
  abierto: boolean;
  /** null = modo crear. Si trae un habito, modo editar. */
  inicial: Habito | null;
  onCerrar: () => void;
  onGuardar: (nombre: string) => Promise<void>;
}

/**
 * Dialogo para crear / editar / archivar un habito.
 *
 * Tres modos en la misma pantalla:
 *  - crear: vacio, input focus, boton "Crear".
 *  - editar: prellenado, input focus, boton "Guardar".
 *  - archivado: input deshabilitado, accion secundaria "Reactivar".
 *
 * Validacion inline: error si el nombre esta vacio o tiene mas de 60.
 */
export function DialogoHabito({ abierto, inicial, onCerrar, onGuardar }: Props) {
  const [nombre, setNombre] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (abierto) {
      setNombre(inicial?.nombre ?? "");
      setError(null);
    }
  }, [abierto, inicial]);

  const archivado = inicial ? !inicial.activo : false;

  function validar(valor: string): string | null {
    const limpio = valor.trim();
    if (limpio.length === 0) return "El nombre no puede estar vacio.";
    if (limpio.length > 60) return "Maximo 60 caracteres.";
    return null;
  }

  async function handleGuardar() {
    const e = validar(nombre);
    if (e) {
      setError(e);
      return;
    }
    setGuardando(true);
    setError(null);
    try {
      await onGuardar(nombre.trim());
      onCerrar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar.");
    } finally {
      setGuardando(false);
    }
  }

  if (!abierto) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={inicial ? "Editar habito" : "Nuevo habito"}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
      onClick={onCerrar}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-border bg-bg-card p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-[18px] font-bold text-text-primary">
          {inicial ? "Editar habito" : "Nuevo habito"}
        </h2>

        {archivado && (
          <p className="mt-3 rounded-lg border border-border bg-bg-elevated px-3 py-2 text-[12px] text-text-secondary">
            Este habito esta archivado. Para reactivarlo, primero
            guardalo con un nombre nuevo.
          </p>
        )}

        <label className="mt-4 block">
          <span className="text-[12px] font-medium text-text-secondary">
            Nombre
          </span>
          <input
            type="text"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            disabled={archivado}
            maxLength={60}
            autoFocus
            className="mt-1.5 w-full rounded-lg border border-border bg-bg-elevated px-3 py-2 text-[14px] text-text-primary outline-none transition focus:border-accent focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50"
          />
        </label>

        {error && (
          <p className="mt-2 text-[12px] text-red-400">{error}</p>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCerrar}
            className="rounded-full px-4 py-2 text-[13px] font-medium text-text-secondary transition hover:bg-bg-elevated hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleGuardar}
            disabled={guardando || archivado}
            className="rounded-full bg-accent px-4 py-2 text-[13px] font-medium text-bg transition hover:bg-accent/90 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {guardando ? "Guardando..." : inicial ? "Guardar" : "Crear"}
          </button>
        </div>
      </div>
    </div>
  );
}
