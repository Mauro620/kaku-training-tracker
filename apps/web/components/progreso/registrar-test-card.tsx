"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { BentoCard } from "@/components/ui/bento-card";
import { Cronometro } from "@/components/progreso/cronometro";
import { useRegistrarTest, useTiposTest } from "@/lib/api/hooks";

export function RegistrarTestCard({ fecha }: { fecha: string }) {
  const tipos = useTiposTest();
  const registrar = useRegistrarTest(fecha);

  const [tipoTestId, setTipoTestId] = useState<number | null>(null);
  const [superficie, setSuperficie] = useState("");
  const [valores, setValores] = useState<string[]>([]);

  const tipo = tipos.data?.find((t) => t.id === tipoTestId) ?? null;
  const primerTipo = tipos.data?.[0];
  if (!tipoTestId && primerTipo) {
    setTipoTestId(primerTipo.id);
  }

  function agregarValor(v: string) {
    if (v.trim() === "" || Number.isNaN(Number(v))) return;
    setValores((arr) => [...arr, v]);
  }

  function quitarValor(idx: number) {
    setValores((arr) => arr.filter((_, i) => i !== idx));
  }

  return (
    <BentoCard>
      <header className="mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Registrar test
        </p>
      </header>

      <div className="flex flex-col gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            Tipo de test
          </span>
          <select
            value={tipoTestId ?? ""}
            onChange={(e) => {
              setTipoTestId(Number(e.target.value));
              setValores([]);
            }}
            className="bg-surface-secondary rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          >
            {tipos.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nombre} ({t.unidad})
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            Superficie (opcional)
          </span>
          <input
            type="text"
            value={superficie}
            onChange={(e) => setSuperficie(e.target.value)}
            placeholder="ej. grama, pista, cancha sintetica"
            className="bg-surface-secondary rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>

        {tipo?.unidad === "s" && <Cronometro onMarcar={(s) => agregarValor(String(s))} />}

        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-[10px] uppercase tracking-widest text-text-secondary">
              Intentos {tipo && `(${tipo.unidad})`}
            </p>
            <button
              type="button"
              onClick={() => agregarValor("0")}
              className="flex items-center gap-1 rounded-pill bg-surface-secondary px-3 py-1 text-[12px] font-medium text-text-primary"
            >
              <Plus size={12} /> Manual
            </button>
          </div>
          <div className="flex flex-col gap-2">
            {valores.map((v, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className="w-6 text-[12px] text-text-secondary">{idx + 1}</span>
                <input
                  type="number"
                  step="0.001"
                  value={v}
                  onChange={(e) =>
                    setValores((arr) => arr.map((x, i) => (i === idx ? e.target.value : x)))
                  }
                  className="flex-1 bg-surface-secondary rounded-pill px-4 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
                />
                <button
                  type="button"
                  onClick={() => quitarValor(idx)}
                  aria-label="Quitar intento"
                  className="p-1 text-text-secondary"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
            {valores.length === 0 && (
              <p className="text-[13px] text-text-secondary">
                Sin intentos todavia. Usa el cronometro o agrega uno manual.
              </p>
            )}
          </div>
        </div>

        <button
          type="button"
          disabled={
            tipoTestId === null ||
            valores.length === 0 ||
            valores.some((v) => v.trim() === "" || Number(v) <= 0) ||
            registrar.isPending
          }
          onClick={async () => {
            if (tipoTestId === null) return;
            await registrar.mutateAsync({
              idempotency_key: crypto.randomUUID(),
              tipo_test_id: tipoTestId,
              superficie: superficie.trim() || null,
              valores,
            });
            setValores([]);
            setSuperficie("");
          }}
          className="mt-2 w-full bg-text-primary text-canvas rounded-pill py-3 text-[14px] font-semibold disabled:opacity-50"
        >
          {registrar.isPending ? "Guardando..." : "Guardar test"}
        </button>
      </div>
    </BentoCard>
  );
}
