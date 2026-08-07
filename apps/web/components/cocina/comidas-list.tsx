"use client";

import { Trash2 } from "lucide-react";

import { BentoCard } from "@/components/ui/bento-card";
import {
  useComidasDelDia,
  useEliminarComida,
} from "@/lib/api/hooks";

type Props = { fecha: string };

const ETIQUETA_MOMENTO: Record<string, string> = {
  desayuno: "Desayuno",
  media_manana: "Media manana",
  almuerzo: "Almuerzo",
  merienda: "Merienda",
  cena: "Cena",
};

/**
 * Comidas registradas hoy. Cada fila es una comida (con o sin receta).
 * El nombre de la receta, si la tiene, se resolveria en una segunda
 * iteracion (JOIN en el server). Para Fase 6 sin JOIN extra, mostramos
 * "Receta #N" si hay receta_id.
 */
export function ComidasList({ fecha }: Props) {
  const { data, isLoading } = useComidasDelDia(fecha);
  const eliminar = useEliminarComida(fecha);

  const comidas = data?.comidas ?? [];

  return (
    <BentoCard>
      <header className="flex items-center justify-between mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Comidas de hoy
        </p>
      </header>

      {isLoading ? (
        <div className="h-20" />
      ) : comidas.length === 0 ? (
        <p className="text-[13px] text-text-secondary">
          Aca vas a ver lo que registraste cuando termines de comer.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {comidas.map((c) => (
            <li
              key={c.id}
              className="flex items-center justify-between gap-3 rounded-lg bg-surface-secondary px-3 py-2"
            >
              <div className="flex flex-col">
                <span className="text-[13px] font-semibold text-text-primary">
                  {ETIQUETA_MOMENTO[c.momento] ?? c.momento}
                </span>
                <span className="text-[11px] text-text-secondary">
                  {c.receta_id
                    ? `Receta #${c.receta_id}`
                    : `${c.items.length} ${c.items.length === 1 ? "item" : "items"}`}
                  {c.nota ? ` · ${c.nota}` : ""}
                </span>
              </div>
              <button
                type="button"
                onClick={() => {
                  if (confirm(`Eliminar esta comida?`)) {
                    eliminar.mutate(c.id);
                  }
                }}
                disabled={eliminar.isPending}
                aria-label="Eliminar comida"
                className="shrink-0 rounded p-1 text-text-secondary hover:bg-canvas hover:text-state-danger disabled:opacity-50"
              >
                <Trash2 size={16} aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      )}
    </BentoCard>
  );
}