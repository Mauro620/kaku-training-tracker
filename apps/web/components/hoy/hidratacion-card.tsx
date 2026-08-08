"use client";

import { useMemo } from "react";

import { BentoCard } from "@/components/ui/bento-card";
import {
  useHidratacionDeHoy,
  useParametro,
  useSumarHidratacion,
} from "@/lib/api/hooks";

type Props = { fecha: string };

const CANTIDADES_RAPIDAS_ML = [250, 500, 750] as const;
const OBJETIVO_DEFAULT_ML = 3000;

/**
 * Hidratación del dia (A2 de la revision de UI).
 *
 * No es un check booleano: se registra la cantidad (SPEC.md §2.4). Cada
 * tap SUMA al total, no lo reemplaza.
 *
 * Numero nunca solo: "2.5 L · 0.5 sobre objetivo · 3.0 L". Si el delta
 * es 0, va "en objetivo". Sin dato: "Sin registro · objetivo 3.0 L".
 *
 * El objetivo se lee de `parametro("hidratacion_objetivo_ml")` (default
 * 3000 = 4 termos de 750 ml). El usuario tiene rangos personales en
 * `usuario.agua_objetivo_ml_min/max`, pero el de la UI Hoy es global
 * para no alargar la tarjeta con un selector.
 */
export function HidratacionCard({ fecha }: Props) {
  const { data, isLoading } = useHidratacionDeHoy(fecha);
  const { data: paramObjetivo } = useParametro("hidratacion_objetivo_ml");
  const sumar = useSumarHidratacion(fecha);

  const objetivo = useMemo(() => {
    if (!paramObjetivo) return OBJETIVO_DEFAULT_ML;
    const n = Number(paramObjetivo.valor);
    return Number.isFinite(n) && n > 0 ? n : OBJETIVO_DEFAULT_ML;
  }, [paramObjetivo]);

  const ml = data?.ml_totales ?? 0;
  const litros = (ml / 1000).toFixed(2);
  const objetivoLitros = (objetivo / 1000).toFixed(1);

  // El delta solo se muestra cuando hay dato. Si no hay registro, "—"
  // en el numero grande y texto de contexto debajo.
  const tieneDato = data !== undefined;
  const banda = tieneDato ? clasificarBanda(ml, objetivo) : "vacio";
  const proporcion = tieneDato ? Math.min(ml / objetivo, 1) : 0;

  const colorBarra =
    banda === "ok"
      ? "bg-state-positive"
      : banda === "cerca"
        ? "bg-state-warning"
        : banda === "bajo"
          ? "bg-state-danger"
          : "bg-border-subtle";

  const contextoTexto = (() => {
    if (!tieneDato) {
      return `Sin registro · objetivo ${objetivoLitros} L`;
    }
    const delta = ml - objetivo;
    if (Math.abs(delta) < 1) return "en objetivo";
    if (delta > 0) {
      return `${(delta / 1000).toFixed(1)} L sobre objetivo · ${objetivoLitros} L`;
    }
    return `${(Math.abs(delta) / 1000).toFixed(1)} L bajo objetivo · ${objetivoLitros} L`;
  })();

  return (
    <BentoCard>
      <header className="flex items-center justify-between mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Hidratación
        </p>
        <span className="text-[11px] text-text-secondary">
          Objetivo {objetivoLitros} L
        </span>
      </header>

      {isLoading ? (
        <div className="h-20" />
      ) : (
        <>
          <div className="flex items-baseline gap-3">
            <p className="text-[48px] font-bold leading-none tabular text-text-primary">
              {tieneDato ? litros : "—"}
              <span className="ml-2 text-base font-medium text-text-secondary">
                L
              </span>
            </p>
            <p className="text-[13px] text-text-secondary">{contextoTexto}</p>
          </div>

          <div
            className="mt-3 h-1.5 w-full rounded-full bg-surface-secondary overflow-hidden"
            aria-label={`${tieneDato ? ml : 0} de ${objetivo} ml`}
          >
            <div
              className={`h-full ${colorBarra}`}
              style={{ width: `${(proporcion * 100).toFixed(1)}%` }}
            />
          </div>

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

function clasificarBanda(
  ml: number,
  objetivo: number,
): "ok" | "cerca" | "bajo" {
  if (ml >= objetivo) return "ok";
  if (ml >= objetivo - 500) return "cerca";
  return "bajo";
}
