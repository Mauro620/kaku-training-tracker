"use client";

import { BentoCard } from "@/components/ui/bento-card";
import {
  useHidratacionDeHoy,
  useSumarHidratacion,
  useUsuarioActual,
} from "@/lib/api/hooks";

type Props = { fecha: string };

const CANTIDADES_RAPIDAS_ML = [250, 500, 750] as const;

/**
 * Hidratación del día. No es un check booleano: se registra la cantidad
 * (SPEC.md §2.4). Cada tap SUMA al total, no lo reemplaza.
 */
export function HidratacionCard({ fecha }: Props) {
  const { data, isLoading } = useHidratacionDeHoy(fecha);
  const { data: usuario } = useUsuarioActual();
  const sumar = useSumarHidratacion(fecha);

  const ml = data?.ml_totales ?? 0;
  const litros = (ml / 1000).toFixed(2);

  const meta =
    usuario?.agua_objetivo_ml_min != null && usuario.agua_objetivo_ml_max != null
      ? `${(usuario.agua_objetivo_ml_min / 1000).toFixed(1)}–${(usuario.agua_objetivo_ml_max / 1000).toFixed(1)} L`
      : null;

  return (
    <BentoCard>
      <header className="flex items-center justify-between mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Hidratación
        </p>
        {meta && (
          <span className="text-[11px] text-text-secondary">Meta {meta}</span>
        )}
      </header>

      {isLoading ? (
        <div className="h-20" />
      ) : (
        <>
          <p className="text-[48px] font-bold leading-none tabular text-text-primary">
            {litros}
            <span className="ml-2 text-base font-medium text-text-secondary">L</span>
          </p>

          <div className="mt-5 flex gap-2">
            {CANTIDADES_RAPIDAS_ML.map((cantidad) => (
              <button
                key={cantidad}
                type="button"
                onClick={() => sumar.mutate({ cantidad_ml: cantidad })}
                disabled={sumar.isPending}
                className="flex-1 bg-surface-secondary rounded-pill py-3 text-[13px] font-semibold text-text-primary disabled:opacity-50"
              >
                +{cantidad} ml
              </button>
            ))}
          </div>
        </>
      )}
    </BentoCard>
  );
}
