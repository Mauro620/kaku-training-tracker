"use client";

import { useState } from "react";
import Link from "next/link";

import { ChevronDown, ChevronRight, Dumbbell, Plus } from "lucide-react";

import { useHabitosAjustes } from "@/lib/api/hooks";
import type { Habito } from "@/lib/api/hooks";

import { TarjetaHabito } from "./tarjeta-habito";
import { DialogoHabito } from "./dialogo-habito";

/**
 * Pantalla Ajustes de habitos (D1-D4).
 * - Lista todos los habitos (incluyendo archivados).
 * - Archivar es `activo = false`, NUNCA DELETE (D3).
 * - Reordenar via stepper (no drag-and-drop): la lista es corta y
 *   los steppers son inequivocos en mobile.
 */
export function AjustesScreen() {
  const { habitos, cargando, error, crear, actualizar, archivar, reordenar } =
    useHabitosAjustes();

  const [dialogoAbierto, setDialogoAbierto] = useState(false);
  const [editando, setEditando] = useState<Habito | null>(null);
  const [mostrarArchivados, setMostrarArchivados] = useState(false);

  if (cargando) {
    return (
      <p className="text-[13px] text-text-secondary">Cargando...</p>
    );
  }
  if (error) {
    return (
      <p className="text-[13px] text-red-400">{error}</p>
    );
  }

  const activos = habitos.filter((h) => h.activo);
  const archivados = habitos.filter((h) => !h.activo);

  return (
    <div className="space-y-6">
      {/* Seccion Catalogo */}
      <section className="rounded-2xl border border-border-subtle bg-surface-primary p-4">
        <header className="mb-3 flex items-center justify-between">
          <h2 className="text-[15px] font-semibold text-text-primary">
            Catalogo
          </h2>
        </header>
        <Link
          href="/entreno/ejercicios"
          className="flex items-center justify-between rounded-xl border border-border-subtle bg-surface-secondary p-3 transition hover:bg-surface-secondary/80"
        >
          <div className="flex items-center gap-3">
            <Dumbbell className="h-5 w-5 text-text-secondary" />
            <span className="text-[14px] font-medium text-text-primary">
              Banco de ejercicios
            </span>
          </div>
          <ChevronRight className="h-5 w-5 text-text-secondary" />
        </Link>
      </section>

      <section>
        <header className="mb-3 flex items-center justify-between">
          <h2 className="text-[15px] font-semibold text-text-primary">
            Habitos
          </h2>
          <button
            type="button"
            onClick={() => {
              setEditando(null);
              setDialogoAbierto(true);
            }}
            className="inline-flex items-center gap-1.5 rounded-full bg-accent px-3 py-1.5 text-[12px] font-medium text-bg hover:bg-accent/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            <Plus className="h-3.5 w-3.5" strokeWidth={2.5} aria-hidden />
            Nuevo habito
          </button>
        </header>

        {activos.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-border bg-bg-card p-6 text-center text-[13px] text-text-secondary">
            No tenes habitos. Crea uno para empezar a registrar.
          </p>
        ) : (
          <ul className="space-y-2">
            {activos.map((h, idx) => (
              <TarjetaHabito
                key={h.id}
                habito={h}
                indice={idx}
                total={activos.length}
                onEditar={() => {
                  setEditando(h);
                  setDialogoAbierto(true);
                }}
                onArchivar={() => archivar(h.id)}
                onMover={(dir) => reordenar(h.id, dir, activos)}
              />
            ))}
          </ul>
        )}
      </section>

      {archivados.length > 0 && (
        <section>
          <button
            type="button"
            aria-expanded={mostrarArchivados}
            onClick={() => setMostrarArchivados((v) => !v)}
            className="flex w-full items-center gap-1.5 rounded-md py-1.5 text-left transition hover:bg-bg-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {mostrarArchivados ? (
              <ChevronDown className="h-3.5 w-3.5 text-text-secondary" aria-hidden />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-text-secondary" aria-hidden />
            )}
            <span className="text-[13px] font-medium text-text-secondary">
              Archivados ({archivados.length})
            </span>
          </button>
          {mostrarArchivados && (
            <ul className="mt-2 space-y-2">
              {archivados.map((h) => (
                <TarjetaHabito
                  key={h.id}
                  habito={h}
                  indice={0}
                  total={1}
                  archivado
                  onEditar={() => {
                    setEditando(h);
                    setDialogoAbierto(true);
                  }}
                  onArchivar={() => {}}
                  onMover={() => {}}
                  onReactivar={() => actualizar(h.id, { activo: true })}
                />
              ))}
            </ul>
          )}
        </section>
      )}

      <DialogoHabito
        abierto={dialogoAbierto}
        inicial={editando}
        onCerrar={() => setDialogoAbierto(false)}
        onGuardar={async (nombre) => {
          if (editando) {
            await actualizar(editando.id, { nombre });
          } else {
            await crear(nombre);
          }
        }}
      />
    </div>
  );
}
