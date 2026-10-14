"use client";

import { useProgresoRendimiento, type MejorMarca, type PruebaTendencia } from "@/lib/api/hooks";
import { escalarSerie, etiquetaFecha, formatoNumero, rutaLinea } from "@/lib/progreso";
import { TarjetaPregunta } from "./tarjeta-pregunta";

const ANCHO = 120;
const ALTO = 36;

function Sparkline({ prueba }: { prueba: PruebaTendencia }) {
  const puntos = escalarSerie(
    prueba.puntos.map((p) => p.mejor),
    ANCHO,
    ALTO,
  );
  return (
    <svg
      width={ANCHO}
      height={ALTO}
      viewBox={`0 0 ${ANCHO} ${ALTO}`}
      role="img"
      aria-label={`Tendencia de ${prueba.nombre}: ${prueba.puntos.map((p) => `${etiquetaFecha(p.fecha)} ${formatoNumero(p.mejor, 2)}`).join(", ")}`}
    >
      <path d={rutaLinea(puntos)} fill="none" stroke="#A1A1AA" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
      {puntos.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r={i === puntos.length - 1 ? 4 : 3}
          fill={i === puntos.length - 1 ? "#FFFFFF" : "#A1A1AA"}
          stroke="#18181B"
          strokeWidth={2}
        >
          <title>{`${etiquetaFecha(prueba.puntos[i]!.fecha)}: ${formatoNumero(prueba.puntos[i]!.mejor, 2)} ${prueba.unidad}`}</title>
        </circle>
      ))}
    </svg>
  );
}

function CambioPct({ prueba }: { prueba: PruebaTendencia }) {
  const pct = prueba.puntos[prueba.puntos.length - 1]?.pct_cambio_vs_base ?? null;
  if (pct === null) return <span className="text-[11px] text-text-secondary">base</span>;
  const mejora = pct > 0;
  return (
    <span
      className={`text-[12px] font-medium tabular ${mejora ? "text-state-positive" : pct < 0 ? "text-state-danger" : "text-text-secondary"}`}
    >
      {mejora ? "▲" : pct < 0 ? "▼" : "•"} {pct > 0 ? "+" : ""}
      {formatoNumero(pct)} %
    </span>
  );
}

function textoMarca(m: MejorMarca): string {
  if (m.tipo_medicion === "carga") {
    const rm = m.rm_estimado_kg !== null ? ` · 1RM est. ${formatoNumero(m.rm_estimado_kg)} kg` : "";
    return `${formatoNumero(m.peso_max_kg ?? 0)} kg máx${rm}`;
  }
  if (m.tipo_medicion === "tiempo") return `${m.duracion_max_s} s`;
  if (m.tipo_medicion === "distancia") return `${formatoNumero(m.distancia_max_m ?? 0)} m`;
  return `calidad ${m.calidad_max}/5`;
}

/** 2. ¿Estás rindiendo mejor? Tendencia por prueba y mejor marca por ejercicio. */
export function TarjetaRendimiento() {
  const q = useProgresoRendimiento();
  const pruebas = q.data?.pruebas ?? [];
  const marcas = q.data?.marcas ?? [];

  return (
    <TarjetaPregunta
      numero={2}
      pregunta="¿Estás rindiendo mejor?"
      conclusion={q.data?.conclusion ?? null}
      cargando={q.isLoading}
      error={q.isError}
    >
      {pruebas.length > 0 && (
        <ul className="flex flex-col gap-3">
          {pruebas.map((p) => (
            <li key={p.codigo} className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-[13px] text-text-primary">{p.nombre}</p>
                <p className="tabular text-[12px] text-text-secondary">
                  {formatoNumero(p.puntos[p.puntos.length - 1]?.mejor ?? 0, 2)} {p.unidad}
                  <span className="ml-2">
                    <CambioPct prueba={p} />
                  </span>
                </p>
              </div>
              <Sparkline prueba={p} />
            </li>
          ))}
        </ul>
      )}

      {marcas.length > 0 && (
        <div className={pruebas.length > 0 ? "mt-5 border-t border-border-subtle pt-4" : ""}>
          <p className="mb-2 text-[11px] uppercase tracking-widest text-text-secondary">
            Mejor marca por ejercicio
          </p>
          <ul className="flex flex-col gap-2">
            {marcas.map((m) => (
              <li key={m.ejercicio_id} className="flex items-baseline justify-between gap-3 text-[13px]">
                <span className="min-w-0 text-text-primary">{m.ejercicio}</span>
                <span className="shrink-0 tabular text-text-secondary">{textoMarca(m)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </TarjetaPregunta>
  );
}
