"use client";

import { useState, useEffect } from "react";

import {
  useEjerciciosList,
  useFusionarEjercicio,
  useEjercicio,
  type TipoMedicion,
} from "@/lib/api/hooks";
import { Sheet } from "@/components/ui/sheet";

export type FusionEjercicioDialogProps = {
  origenId: number | null;
  destinoIdPreseleccionado?: number | null;
  open: boolean;
  onClose: () => void;
  onConfirm?: (destinoId: number) => Promise<void>;
};

/**
 * FusionEjercicioDialog: modal para fusionar ejercicios.
 * - Selector de destino (filtrado por tipo_medicion del origen)
 * - Preview con conteos estimados
 * - Confirmacion con invalidacion automatica
 */
export function FusionEjercicioDialog({
  origenId,
  destinoIdPreseleccionado,
  open,
  onClose,
  onConfirm,
}: FusionEjercicioDialogProps) {
  const { data: origen } = useEjercicio(origenId);
  const [destinoId, setDestinoId] = useState<number | null>(destinoIdPreseleccionado ?? null);

  // Lista de ejercicios del mismo tipo_medicion para el selector
  const tipoMedicion = origen?.tipo_medicion as TipoMedicion | undefined;
  const { data: ejerciciosList } = useEjerciciosList(
    null,
    tipoMedicion ?? null,
    true, // solo activos
    undefined,
  );

  const fusionar = useFusionarEjercicio(origenId ?? 0);

  // Resetear destino cuando cambia el origen o se abre el dialog
  useEffect(() => {
    if (open) {
      setDestinoId(destinoIdPreseleccionado ?? null);
    }
  }, [open, destinoIdPreseleccionado]);

  if (!origenId || !open) return null;

  // Filtrar ejercicios del selector (excluir el origen)
  const opcionesDestino =
    ejerciciosList?.items.filter((e) => e.id !== origenId) ?? [];

  const ejercicioDestino = ejerciciosList?.items.find((e) => e.id === destinoId);

  // Handlers
  const handleConfirmar = async () => {
    if (!destinoId) return;

    try {
      await fusionar.mutateAsync({ destino_id: destinoId });
      
      // Mostrar mensaje de exito con conteos del backend
      const resultado = fusionar.data;
      if (resultado) {
        alert(
          `Fusion confirmada: ${resultado.bloques_reasignados} bloques movidos, ${resultado.bloques_plan_reasignados} bloques de plan movidos, origen archivado.`,
        );
      }

      onClose();
      onConfirm?.(destinoId);
    } catch (err) {
      alert("Error al fusionar: " + (err instanceof Error ? err.message : "Error desconocido"));
    }
  };

  // Preview de conteos (estimado desde el historial)
  const bloquesEstimados = origen?.historial?.length ?? 0;

  return (
    <Sheet open={open} onClose={onClose} title="Fusionar ejercicios">
      <div className="space-y-6">
        {/* Selector de destino */}
        <section>
          <label className="mb-2 block text-[14px] font-semibold text-text-primary">
            Ejercicio destino
          </label>
          <select
            value={destinoId ?? ""}
            onChange={(e) => setDestinoId(e.target.value ? Number(e.target.value) : null)}
            className="w-full rounded-xl border border-border-subtle bg-surface-primary p-3 text-[14px] text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="" disabled>
              Selecciona un ejercicio...
            </option>
            {opcionesDestino.map((ejercicio) => (
              <option key={ejercicio.id} value={ejercicio.id}>
                {ejercicio.nombre} ({ejercicio.usos} usos)
              </option>
            ))}
          </select>
          {destinoId === origenId && (
            <p className="mt-1 text-[12px] text-state-danger">
              No puedes fusionar un ejercicio consigo mismo.
            </p>
          )}
        </section>

        {/* Preview block */}
        {destinoId && ejercicioDestino && origen && (
          <section className="rounded-xl border border-border-subtle bg-surface-primary p-4">
            <h3 className="mb-2 text-[14px] font-semibold text-text-primary">Vista previa</h3>
            <p className="text-[13px] text-text-primary">
              Se moveran{" "}
              <span className="font-semibold">{bloquesEstimados}</span> bloques de{" "}
              <span className="font-semibold">{origen.nombre}</span> a{" "}
              <span className="font-semibold">{ejercicioDestino.nombre}</span>.
            </p>
            <p className="mt-2 text-[12px] text-text-secondary">
              Los conteos exactos llegan al confirmar.
            </p>
          </section>
        )}

        {/* Botones de accion */}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-full bg-surface-secondary px-4 py-3 text-[14px] font-semibold text-text-secondary transition hover:bg-surface-secondary/80"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleConfirmar}
            disabled={!destinoId || destinoId === origenId || fusionar.isPending}
            className="flex-1 rounded-full bg-accent px-4 py-3 text-[14px] font-semibold text-bg transition hover:bg-accent/90 disabled:opacity-50"
          >
            {fusionar.isPending ? "Fusionando..." : "Confirmar fusion"}
          </button>
        </div>
      </div>
    </Sheet>
  );
}
