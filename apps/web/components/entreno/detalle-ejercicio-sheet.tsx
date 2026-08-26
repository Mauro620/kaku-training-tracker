"use client";

import { useEffect, useState } from "react";
import { Pencil, Trash2, Archive, GitMerge, X } from "lucide-react";

import {
  useEjercicio,
  useActualizarEjercicio,
  useEliminarEjercicio,
  type EjercicioDetalleRead,
} from "@/lib/api/hooks";
import { formatearFechaLarga } from "@/lib/fecha";
import { Sheet } from "@/components/ui/sheet";
import { ActionPopoverMenu } from "@/components/ui/action-popover-menu";
import { EmptyState } from "@/components/ui/empty-state";
import type { FusionEjercicioDialogProps } from "./fusion-ejercicio-dialog";

type DetalleEjercicioSheetProps = {
  ejercicioId: number | null;
  open: boolean;
  onClose: () => void;
  onFusionarClick?: (origenId: number) => void;
};

/**
 * DetalleEjercicioSheet: panel deslizante con detalle de un ejercicio.
 * - Header con chips: tipo_medicion (no editable), patron, carga_lumbar
 * - Descripcion editable inline (optimistic update)
 * - Historial top 5 ejecuciones
 * - Posibles duplicados con boton Fusionar
 * - Menu tres puntos: Editar, Archivar, Fusionar, Eliminar
 */
export function DetalleEjercicioSheet({
  ejercicioId,
  open,
  onClose,
  onFusionarClick,
}: DetalleEjercicioSheetProps) {
  const { data: ejercicio, isLoading } = useEjercicio(ejercicioId);
  const actualizar = useActualizarEjercicio(ejercicioId ?? 0);
  const eliminar = useEliminarEjercicio(ejercicioId ?? 0);

  // Estado local para edicion inline de descripcion
  const [editandoDescripcion, setEditandoDescripcion] = useState(false);
  const [descripcionValue, setDescripcionValue] = useState("");

  // Sincronizar descripcion cuando llega un ejercicio distinto al actual
  // Solo re-sincronizamos cuando cambia el id del ejercicio; cambios en otros
  // campos no deben pisar lo que el usuario esta editando.
  const ejercicioIdActual = ejercicio?.id;
  useEffect(() => {
    if (ejercicio) {
      setDescripcionValue(ejercicio.descripcion ?? "");
      setEditandoDescripcion(false);
    }
    // ejercicio se lee dentro pero queremos que reaccione solo al id.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ejercicioIdActual]);

  if (!ejercicioId || !open) return null;

  // Handlers
  const handleGuardarDescripcion = async () => {
    if (!ejercicioId) return;
    
    const valor = descripcionValue.trim();
    await actualizar.mutateAsync({
      descripcion: valor === "" ? null : valor,
    });
    setEditandoDescripcion(false);
  };

  const handleCancelarEdicion = () => {
    setDescripcionValue(ejercicio?.descripcion ?? "");
    setEditandoDescripcion(false);
  };

  const handleArchivar = async () => {
    if (!ejercicioId) return;
    await actualizar.mutateAsync({ activo: false });
    onClose();
  };

  const handleEliminar = async () => {
    if (!ejercicioId) return;
    try {
      await eliminar.mutateAsync();
      onClose();
    } catch (err) {
      // Si el backend devuelve 409, mostrar mensaje de error
      if (err instanceof Error && err.message.includes("409")) {
        alert("No se puede eliminar: el ejercicio tiene bloques asociados. Usa Fusionar en su lugar.");
      } else {
        alert("Error al eliminar: " + (err instanceof Error ? err.message : "Error desconocido"));
      }
    }
  };

  const accionesMenu = [
    {
      label: "Editar descripcion",
      onClick: () => setEditandoDescripcion(true),
      icon: <Pencil className="h-4 w-4" />,
    },
    {
      label: "Archivar",
      onClick: handleArchivar,
      icon: <Archive className="h-4 w-4" />,
    },
    {
      label: "Fusionar",
      onClick: () => onFusionarClick?.(ejercicioId),
      icon: <GitMerge className="h-4 w-4" />,
    },
    {
      label: "Eliminar",
      onClick: handleEliminar,
      icon: <Trash2 className="h-4 w-4" />,
      danger: true,
    },
  ];

  // Render de chips del header
  const renderChipCargaLumbar = (carga: "alta" | "media" | "baja") => {
    const colorClass =
      carga === "alta"
        ? "text-state-danger"
        : "text-text-secondary";
    return (
      <span className={`rounded-full bg-surface-secondary px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide ${colorClass}`}>
        {carga} lumbar
      </span>
    );
  };

  // Render de historial segun tipo_medicion
  const renderValorHistorial = (item: EjercicioDetalleRead["historial"][number]) => {
    // EjercicioHistorialItem solo tiene series, reps, peso_kg
    // Para distancia/tiempo/tecnica, el backend deberia devolver campos extra
    // Por ahora usamos lo disponible
    switch (ejercicio?.tipo_medicion) {
      case "carga":
        return `${item.series}×${item.reps} @ ${item.peso_kg}kg`;
      case "distancia":
        // El backend no devuelve distancia_m en el historial de ejercicio
        return `${item.reps} reps`;
      case "tiempo":
        return `${item.series} series`;
      case "tecnica":
        return `${item.reps ?? item.series} reps`;
      default:
        return "-";
    }
  };

  if (isLoading) {
    return (
      <Sheet open={open} onClose={onClose} title="Cargando...">
        <div className="space-y-4">
          <div className="animate-pulse space-y-2">
            <div className="h-4 w-3/4 rounded bg-surface-secondary" />
            <div className="h-4 w-1/2 rounded bg-surface-secondary" />
            <div className="h-4 w-full rounded bg-surface-secondary" />
          </div>
        </div>
      </Sheet>
    );
  }

  if (!ejercicio) {
    return (
      <Sheet open={open} onClose={onClose} title="Ejercicio no encontrado">
        <EmptyState
          title="Ejercicio no encontrado"
          description="El ejercicio que buscas no existe o fue eliminado."
        />
      </Sheet>
    );
  }

  return (
    <Sheet open={open} onClose={onClose} title={ejercicio.nombre}>
      <div className="space-y-6">
        {/* Header de chips */}
        <div className="flex flex-wrap gap-2">
          <span
            className="relative rounded-full bg-surface-secondary px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-text-secondary"
            title="No editable: cambiarlo invalidaria el historico"
          >
            {ejercicio.tipo_medicion}
          </span>
          {ejercicio.patron && (
            <span className="rounded-full bg-surface-secondary px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-text-secondary">
              {ejercicio.patron}
            </span>
          )}
          {ejercicio.carga_lumbar && renderChipCargaLumbar(ejercicio.carga_lumbar)}
        </div>

        {/* Descripcion */}
        <section>
          <h3 className="mb-2 text-[14px] font-semibold text-text-primary">Descripcion</h3>
          {editandoDescripcion ? (
            <div className="space-y-2">
              <textarea
                value={descripcionValue}
                onChange={(e) => setDescripcionValue(e.target.value)}
                placeholder="Agregar descripcion..."
                rows={3}
                className="w-full rounded-xl border border-border-subtle bg-surface-primary p-3 text-[14px] text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent"
                autoFocus
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleGuardarDescripcion}
                  disabled={actualizar.isPending}
                  className="rounded-full bg-accent px-4 py-2 text-[13px] font-semibold text-bg transition hover:bg-accent/90 disabled:opacity-50"
                >
                  {actualizar.isPending ? "Guardando..." : "Guardar"}
                </button>
                <button
                  type="button"
                  onClick={handleCancelarEdicion}
                  className="rounded-full bg-surface-secondary px-4 py-2 text-[13px] font-medium text-text-secondary transition hover:bg-surface-secondary/80"
                >
                  Cancelar
                </button>
              </div>
            </div>
          ) : ejercicio.descripcion ? (
            <div className="flex items-start justify-between gap-2">
              <p className="text-[14px] text-text-primary">{ejercicio.descripcion}</p>
              <button
                type="button"
                onClick={() => {
                  setDescripcionValue(ejercicio.descripcion ?? "");
                  setEditandoDescripcion(true);
                }}
                className="flex items-center gap-1 text-[12px] font-medium text-text-secondary transition hover:text-text-primary"
              >
                <Pencil className="h-3.5 w-3.5" />
                Editar
              </button>
            </div>
          ) : (
            <EmptyState
              title="Sin descripcion"
              action={{
                label: "Agregar descripcion",
                onClick: () => setEditandoDescripcion(true),
              }}
            />
          )}
        </section>

        {/* Historial (top 5) */}
        <section>
          <h3 className="mb-2 text-[14px] font-semibold text-text-primary">Historial</h3>
          {ejercicio.historial.length === 0 ? (
            <p className="rounded-xl border border-border-subtle bg-surface-primary p-4 text-[13px] text-text-secondary">
              Todavia no lo has ejecutado
            </p>
          ) : (
            <ul className="space-y-2">
              {ejercicio.historial.slice(0, 5).map((item, idx) => (
                <li
                  key={idx}
                  className="flex items-center justify-between rounded-xl border border-border-subtle bg-surface-primary p-3"
                >
                  <span className="text-[13px] text-text-secondary">
                    {formatearFechaLarga(item.fecha)}
                  </span>
                  <span className="text-[13px] font-medium text-text-primary">
                    {renderValorHistorial(item)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Posibles duplicados */}
        {ejercicio.posibles_duplicados.length > 0 && (
          <section>
            <h3 className="mb-2 text-[14px] font-semibold text-text-primary">Posibles duplicados</h3>
            <ul className="space-y-2">
              {ejercicio.posibles_duplicados.map((duplicado) => (
                <li
                  key={duplicado.id}
                  className="flex items-center justify-between rounded-xl border border-border-subtle bg-surface-primary p-3"
                >
                  <div>
                    <p className="text-[13px] font-medium text-text-primary">{duplicado.nombre}</p>
                    <p className="text-[11px] text-text-secondary">
                      Similitud: {(duplicado.similitud * 100).toFixed(0)}%
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => onFusionarClick?.(ejercicioId)}
                    className="rounded-full bg-surface-secondary px-3 py-1.5 text-[12px] font-medium text-text-secondary transition hover:bg-surface-secondary/80"
                  >
                    Fusionar
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Footer con menu de tres puntos */}
        <div className="flex justify-end border-t border-border-subtle pt-4">
          <ActionPopoverMenu items={accionesMenu} />
        </div>
      </div>
    </Sheet>
  );
}
