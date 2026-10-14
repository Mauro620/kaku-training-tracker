"use client";

import { useProgresoCumplimiento } from "@/lib/api/hooks";
import { ESTADOS_PLAN, etiquetaFecha, formatoNumero } from "@/lib/progreso";
import { TarjetaPregunta } from "./tarjeta-pregunta";

/** 1. ¿Cumpliste el plan? Una barra al 100 % por semana, repartida por estado. */
export function TarjetaCumplimiento() {
  const q = useProgresoCumplimiento();
  const semanas = q.data?.semanas.filter((s) => s.planeadas > 0) ?? [];

  return (
    <TarjetaPregunta
      numero={1}
      pregunta="¿Cumpliste el plan?"
      conclusion={q.data?.conclusion ?? null}
      cargando={q.isLoading}
      error={q.isError}
    >
      {semanas.length === 0 ? (
        <p className="text-[12px] text-text-secondary">
          Importa un plan semanal para ver el cumplimiento.
        </p>
      ) : (
        <>
          <ul className="flex flex-col gap-3">
            {semanas.map((s) => (
              <li key={s.numero}>
                <div className="mb-1 flex items-baseline justify-between text-[12px]">
                  <span className="text-text-primary">
                    Semana {s.numero}
                    <span className="ml-2 text-text-secondary">{etiquetaFecha(s.inicio)}</span>
                  </span>
                  <span className="tabular text-text-secondary">
                    {s.cumplido + s.movido} de {s.planeadas}
                  </span>
                </div>
                <div
                  className="flex h-3 w-full gap-[2px]"
                  role="img"
                  aria-label={`Semana ${s.numero}: ${s.cumplido} cumplidas, ${s.movido} movidas, ${s.descartado} descartadas, ${s.pendiente} pendientes de ${s.planeadas}`}
                >
                  {ESTADOS_PLAN.map((e) => {
                    const n = s[e.clave];
                    const pct = s[`pct_${e.clave}` as const];
                    if (n === 0 || pct === null) return null;
                    return (
                      <div
                        key={e.clave}
                        title={`${e.etiqueta}: ${n} (${formatoNumero(pct)} %)`}
                        style={{
                          flexGrow: n,
                          backgroundColor: e.color,
                          border: e.clave === "pendiente" ? "1px solid #71717A" : undefined,
                        }}
                        className="min-w-[6px] rounded-[4px]"
                      />
                    );
                  })}
                </div>
              </li>
            ))}
          </ul>
          <ul className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-text-secondary">
            {ESTADOS_PLAN.map((e) => (
              <li key={e.clave} className="flex items-center gap-1.5">
                <span
                  aria-hidden
                  className="inline-block h-2.5 w-2.5 rounded-[3px]"
                  style={{
                    backgroundColor: e.color,
                    border: e.clave === "pendiente" ? "1px solid #71717A" : undefined,
                  }}
                />
                {e.etiqueta}
              </li>
            ))}
          </ul>
        </>
      )}
    </TarjetaPregunta>
  );
}
