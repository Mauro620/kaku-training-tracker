"use client";

import { useState } from "react";
import { BentoCard } from "@/components/ui/bento-card";
import { useMedidas, useRegistrarMedida } from "@/lib/api/hooks";

export function MedidaCard({ fecha }: { fecha: string }) {
  const medidas = useMedidas();
  const registrar = useRegistrarMedida();

  const [peso, setPeso] = useState("");
  const [fcReposo, setFcReposo] = useState("");

  const ultima = medidas.data?.[0] ?? null;

  return (
    <BentoCard>
      <header className="mb-4 flex items-center justify-between">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Medida corporal
        </p>
        {ultima && (
          <span className="text-[11px] text-text-secondary">
            Ultima: {ultima.peso_kg} kg ({ultima.fecha})
          </span>
        )}
      </header>

      <div className="grid grid-cols-2 gap-2">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            Peso (kg)
          </span>
          <input
            type="number"
            step="0.01"
            value={peso}
            onChange={(e) => setPeso(e.target.value)}
            className="bg-surface-secondary rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            FC reposo (opcional)
          </span>
          <input
            type="number"
            value={fcReposo}
            onChange={(e) => setFcReposo(e.target.value)}
            className="bg-surface-secondary rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
      </div>

      <button
        type="button"
        disabled={peso.trim() === "" || Number(peso) <= 0 || registrar.isPending}
        onClick={async () => {
          await registrar.mutateAsync({
            fecha,
            peso_kg: peso,
            fc_reposo: fcReposo.trim() === "" ? null : Number(fcReposo),
          });
          setPeso("");
          setFcReposo("");
        }}
        className="mt-4 w-full bg-text-primary text-canvas rounded-pill py-3 text-[14px] font-semibold disabled:opacity-50"
      >
        {registrar.isPending ? "Guardando..." : "Guardar medida"}
      </button>
    </BentoCard>
  );
}
