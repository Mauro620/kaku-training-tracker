"use client";

import { useState } from "react";
import { BentoCard } from "@/components/ui/bento-card";
import { useZonasCorporales, useCrearMolestia, type Molestia } from "@/lib/api/hooks";

type Props = {
  fecha: string;
  /** Molestias ya registradas en la fecha, para no duplicar la creacion. */
  existentes: Molestia[];
};

/**
 * Molestia del dia (ROADMAP §4).
 * Una fila por zona marcada. El backend hace upsert por (fecha, zona) asi
 * que tocar la misma zona dos veces actualiza la intensidad.
 */
export function MolestiaForm({ fecha, existentes }: Props) {
  const { data: zonas, isLoading } = useZonasCorporales();
  const crear = useCrearMolestia(fecha);

  const [zonaId, setZonaId] = useState<number | null>(null);
  const [intensidad, setIntensidad] = useState<number>(5);
  const [nota, setNota] = useState("");

  const pendiente = zonaId !== null;

  return (
    <BentoCard>
      <header className="mb-4 flex items-center justify-between">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Molestias
        </p>
        <span className="text-[11px] text-text-secondary">
          {existentes.length} marcada{existentes.length === 1 ? "" : "s"}
        </span>
      </header>

      {isLoading ? (
        <div className="h-20" />
      ) : (
        <>
          <p className="mb-3 text-[13px] text-text-secondary">Zona</p>
          <div className="flex flex-wrap gap-2">
            {zonas?.map((z) => {
              const yaExiste = existentes.some((m) => m.zona_id === z.id);
              const activo = zonaId === z.id;
              return (
                <button
                  key={z.id}
                  type="button"
                  onClick={() => setZonaId(z.id)}
                  className={`min-h-[40px] px-4 rounded-pill text-[13px] capitalize ${
                    activo
                      ? "bg-text-primary text-canvas"
                      : yaExiste
                        ? "bg-surface-secondary text-text-primary border border-state-warning"
                        : "bg-surface-secondary text-text-secondary"
                  }`}
                >
                  {z.nombre}
                </button>
              );
            })}
          </div>

          {zonaId !== null && (
            <>
              <p className="mt-5 mb-2 text-[13px] text-text-secondary">Intensidad (1–10)</p>
              <input
                type="range"
                min={1}
                max={10}
                value={intensidad}
                onChange={(e) => setIntensidad(Number(e.target.value))}
                className="w-full accent-text-primary"
              />
              <p className="text-center text-[20px] font-bold tabular text-text-primary">
                {intensidad}
              </p>

              <p className="mt-4 mb-2 text-[13px] text-text-secondary">Nota (opcional)</p>
              <input
                type="text"
                value={nota}
                onChange={(e) => setNota(e.target.value)}
                placeholder="ej. dolor al final del entrenamiento"
                className="w-full bg-surface-secondary rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
              />

              <button
                type="button"
                disabled={crear.isPending}
                onClick={async () => {
                  await crear.mutateAsync({
                    zona_id: zonaId,
                    intensidad,
                    nota: nota || null,
                  });
                  setZonaId(null);
                  setIntensidad(5);
                  setNota("");
                }}
                className="mt-5 w-full bg-text-primary text-canvas rounded-pill py-3 text-[14px] font-semibold disabled:opacity-50"
              >
                {crear.isPending ? "Guardando..." : "Guardar molestia"}
              </button>
            </>
          )}

          {!pendiente && existentes.length > 0 && (
            <ul className="mt-4 flex flex-col gap-2">
              {existentes.map((m) => {
                const z = zonas?.find((zn) => zn.id === m.zona_id);
                return (
                  <li
                    key={m.id}
                    className="flex items-center justify-between bg-surface-secondary rounded-pill px-5 py-2 text-[14px]"
                  >
                    <span className="capitalize">{z?.nombre ?? `zona ${m.zona_id}`}</span>
                    <span className="tabular text-text-secondary">{m.intensidad}/10</span>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}
    </BentoCard>
  );
}
