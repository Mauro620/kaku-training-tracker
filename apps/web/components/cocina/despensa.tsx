"use client";

import { ShoppingCart, X } from "lucide-react";

import { BentoCard } from "@/components/ui/bento-card";
import {
  useDespensa,
  useEliminarDeDespensa,
  useListaDeMercado,
  useUpsertDespensa,
} from "@/lib/api/hooks";

/**
 * Despensa del usuario + lista de mercado (Fase 6, ROADMAP §6).
 *
 * Lista de mercado = imprescindible = true AND en_stock = false (DB).
 * UI: dos secciones en la misma card. El toggle es por fila, no un edit
 * global (la UI es chica y no vale un modal).
 */
export function DespensaCard() {
  const despensa = useDespensa();
  const lista = useListaDeMercado();
  const upsert = useUpsertDespensa();
  const quitar = useEliminarDeDespensa();

  const items = despensa.data ?? [];
  const aComprar = lista.data?.items ?? [];

  return (
    <BentoCard>
      <header className="flex items-center justify-between mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Despensa
        </p>
        {aComprar.length > 0 && (
          <span className="flex items-center gap-1.5 rounded-pill bg-state-warning/20 px-2.5 py-1 text-[11px] font-semibold text-text-primary">
            <ShoppingCart size={12} aria-hidden />
            {aComprar.length} sin stock
          </span>
        )}
      </header>

      {aComprar.length > 0 && (
        <div className="mb-4 rounded-lg bg-surface-secondary p-3">
          <p className="text-[11px] tracking-widest uppercase text-text-secondary mb-2">
            Lista de mercado
          </p>
          <ul className="flex flex-col gap-1">
            {aComprar.map((it) => (
              <li key={it.alimento_id} className="flex items-center justify-between text-[13px]">
                <span className="text-text-primary">{it.alimento_nombre}</span>
                <button
                  type="button"
                  onClick={() =>
                    upsert.mutate({
                      alimento_id: it.alimento_id,
                      imprescindible: it.imprescindible,
                      en_stock: true,
                    })
                  }
                  className="text-[11px] text-text-secondary hover:text-state-positive"
                >
                  Marcar como comprado
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {despensa.isLoading ? (
        <div className="h-20" />
      ) : items.length === 0 ? (
        <p className="text-[13px] text-text-secondary">
          Marca aca los alimentos que tenes en casa. Imprescindible + sin
          stock arma la lista de mercado.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((it) => (
            <li
              key={it.alimento_id}
              className="flex items-center justify-between gap-3 rounded-lg bg-surface-secondary px-3 py-2"
            >
              <span className="text-[13px] font-semibold text-text-primary">
                {it.alimento_nombre}
              </span>
              <div className="flex items-center gap-2">
                <ToggleImprescindible
                  activo={it.imprescindible}
                  onToggle={() =>
                    upsert.mutate({
                      alimento_id: it.alimento_id,
                      imprescindible: !it.imprescindible,
                      en_stock: it.en_stock,
                    })
                  }
                />
                <ToggleStock
                  enStock={it.en_stock}
                  onToggle={() =>
                    upsert.mutate({
                      alimento_id: it.alimento_id,
                      imprescindible: it.imprescindible,
                      en_stock: !it.en_stock,
                    })
                  }
                />
                <button
                  type="button"
                  onClick={() => quitar.mutate(it.alimento_id)}
                  aria-label={`Quitar ${it.alimento_nombre} de la despensa`}
                  className="shrink-0 rounded p-1 text-text-secondary hover:text-state-danger"
                >
                  <X size={14} aria-hidden />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </BentoCard>
  );
}

function ToggleImprescindible({
  activo,
  onToggle,
}: {
  activo: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={activo}
      aria-label={activo ? "Quitar imprescindible" : "Marcar imprescindible"}
      className={`rounded-pill px-2.5 py-1 text-[11px] font-semibold ${
        activo
          ? "bg-state-focus text-canvas"
          : "bg-canvas text-text-secondary"
      }`}
    >
      Imprescindible
    </button>
  );
}

function ToggleStock({
  enStock,
  onToggle,
}: {
  enStock: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={enStock}
      aria-label={enStock ? "Marcar sin stock" : "Marcar con stock"}
      className={`rounded-pill px-2.5 py-1 text-[11px] font-semibold ${
        enStock
          ? "bg-state-positive text-canvas"
          : "bg-state-warning text-canvas"
      }`}
    >
      {enStock ? "Stock" : "Sin stock"}
    </button>
  );
}