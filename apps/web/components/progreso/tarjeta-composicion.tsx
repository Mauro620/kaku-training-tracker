"use client";

import { useProgresoComposicion } from "@/lib/api/hooks";
import { escalarSerie, etiquetaFecha, formatoNumero, rutaLinea } from "@/lib/progreso";
import { TarjetaPregunta } from "./tarjeta-pregunta";

const ANCHO = 320;
const ALTO = 110;

/**
 * 4. ¿Vas hacia tu objetivo? Peso semanal (linea) y, aparte, la cintura. Dos
 * magnitudes distintas = dos graficos, nunca dos escalas en uno.
 */
export function TarjetaComposicion() {
  const q = useProgresoComposicion();
  const semanas = q.data?.semanas ?? [];
  const objetivo = q.data?.peso_objetivo_kg ?? null;

  const pesos = semanas.map((s) => s.peso_kg);
  // El objetivo entra al dominio para que la linea de referencia sea visible.
  const dominio: [number, number] | undefined =
    pesos.length > 0
      ? [Math.min(...pesos, ...(objetivo !== null ? [objetivo] : [])) - 0.5, Math.max(...pesos, ...(objetivo !== null ? [objetivo] : [])) + 0.5]
      : undefined;
  const puntos = escalarSerie(pesos, ANCHO, ALTO, 10, dominio);
  const yObjetivo = objetivo !== null && dominio ? escalarSerie([objetivo], ANCHO, ALTO, 10, dominio)[0]?.y : null;

  const cinturas = semanas.filter((s) => s.cintura_cm !== null);
  const puntosCintura = escalarSerie(
    cinturas.map((s) => s.cintura_cm as number),
    ANCHO,
    56,
    10,
  );

  return (
    <TarjetaPregunta
      numero={4}
      pregunta="¿Vas hacia tu objetivo de composición?"
      conclusion={q.data?.conclusion ?? null}
      cargando={q.isLoading}
      error={q.isError}
    >
      {semanas.length > 0 && (
        <>
          <p className="mb-1 text-[11px] uppercase tracking-widest text-text-secondary">Peso (kg)</p>
          <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} className="w-full" role="img" aria-label={`Peso semanal: ${semanas.map((s) => `${etiquetaFecha(s.fecha_medida)} ${formatoNumero(s.peso_kg)} kg`).join(", ")}`}>
            {yObjetivo != null && (
              <g>
                <line x1={10} x2={ANCHO - 10} y1={yObjetivo} y2={yObjetivo} stroke="#71717A" strokeWidth={1} strokeDasharray="4 4" />
                <text x={ANCHO - 10} y={yObjetivo - 4} textAnchor="end" fontSize={10} fill="#A1A1AA">
                  objetivo {formatoNumero(objetivo ?? 0)} kg
                </text>
              </g>
            )}
            <path d={rutaLinea(puntos)} fill="none" stroke="#A1A1AA" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
            {puntos.map((p, i) => (
              <circle key={i} cx={p.x} cy={p.y} r={i === puntos.length - 1 ? 5 : 4} fill={i === puntos.length - 1 ? "#FFFFFF" : "#A1A1AA"} stroke="#18181B" strokeWidth={2}>
                <title>{`${etiquetaFecha(semanas[i]!.fecha_medida)}: ${formatoNumero(semanas[i]!.peso_kg)} kg`}</title>
              </circle>
            ))}
            {/* Solo se rotulan el primero y el ultimo: no un numero por punto. */}
            {puntos.length > 0 && (
              <>
                <text x={puntos[0]!.x} y={puntos[0]!.y - 9} textAnchor="start" fontSize={11} fill="#FFFFFF">
                  {formatoNumero(pesos[0]!)}
                </text>
                {puntos.length > 1 && (
                  <text x={puntos[puntos.length - 1]!.x} y={puntos[puntos.length - 1]!.y - 9} textAnchor="end" fontSize={11} fill="#FFFFFF">
                    {formatoNumero(pesos[pesos.length - 1]!)}
                  </text>
                )}
              </>
            )}
          </svg>
          <div className="mt-1 flex justify-between text-[10px] text-text-secondary">
            <span>{etiquetaFecha(semanas[0]!.fecha_medida)}</span>
            <span>{etiquetaFecha(semanas[semanas.length - 1]!.fecha_medida)}</span>
          </div>

          {cinturas.length > 0 && (
            <div className="mt-5">
              <p className="mb-1 text-[11px] uppercase tracking-widest text-text-secondary">Cintura (cm)</p>
              <svg viewBox={`0 0 ${ANCHO} 56`} className="w-full" role="img" aria-label={`Cintura: ${cinturas.map((s) => `${etiquetaFecha(s.fecha_medida)} ${formatoNumero(s.cintura_cm as number)} cm`).join(", ")}`}>
                <path d={rutaLinea(puntosCintura)} fill="none" stroke="#A1A1AA" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                {puntosCintura.map((p, i) => (
                  <circle key={i} cx={p.x} cy={p.y} r={4} fill="#A1A1AA" stroke="#18181B" strokeWidth={2}>
                    <title>{`${etiquetaFecha(cinturas[i]!.fecha_medida)}: ${formatoNumero(cinturas[i]!.cintura_cm as number)} cm`}</title>
                  </circle>
                ))}
              </svg>
            </div>
          )}
        </>
      )}
      {q.data && objetivo === null && (
        <p className="mt-3 text-[11px] text-text-secondary">
          No hay un peso objetivo definido, así que no se muestra una línea de referencia.
        </p>
      )}
    </TarjetaPregunta>
  );
}
