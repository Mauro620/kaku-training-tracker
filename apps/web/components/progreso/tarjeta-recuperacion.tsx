"use client";

import { useProgresoRecuperacion } from "@/lib/api/hooks";
import { SEMAFORO, alturasRelativas, etiquetaFecha, formatoNumero } from "@/lib/progreso";
import { TarjetaPregunta } from "./tarjeta-pregunta";

const ALTO_BARRAS = 88;

/**
 * 3. ¿Te estás recuperando? Carga semanal (barras) con su ACWR y semáforo, y
 * el sueño promedio de la misma semana debajo. Un solo eje: la carga. El ACWR
 * y el sueño van como texto, no como una segunda escala.
 */
export function TarjetaRecuperacion() {
  const q = useProgresoRecuperacion();
  const semanas = q.data?.semanas ?? [];
  const alturas = alturasRelativas(semanas.map((s) => s.carga_semanal));
  const hayCarga = semanas.some((s) => s.carga_semanal > 0);

  return (
    <TarjetaPregunta
      numero={3}
      pregunta="¿Te estás recuperando?"
      conclusion={q.data?.conclusion ?? null}
      cargando={q.isLoading}
      error={q.isError}
    >
      {semanas.length > 0 && (
        <>
          <ol
            className="grid gap-1"
            style={{ gridTemplateColumns: `repeat(${semanas.length}, minmax(0, 1fr))` }}
          >
            {semanas.map((s, i) => {
              const sem = s.semaforo ? SEMAFORO[s.semaforo] : null;
              return (
                <li key={s.inicio} className="flex flex-col items-center gap-1.5">
                  <div className="flex w-full items-end justify-center" style={{ height: ALTO_BARRAS }}>
                    <div
                      title={`Semana del ${etiquetaFecha(s.inicio)}: carga ${s.carga_semanal} (RPE × min)`}
                      className="w-full max-w-[22px] rounded-t-[4px] bg-text-secondary"
                      style={{
                        height: Math.max(2, Math.round((alturas[i] ?? 0) * ALTO_BARRAS)),
                        opacity: s.en_curso ? 0.55 : 1,
                      }}
                    />
                  </div>
                  <span className="tabular text-[10px] text-text-secondary">{s.carga_semanal}</span>
                  <span
                    className="flex items-center gap-1 text-[11px] tabular text-text-primary"
                    title={sem ? `ACWR ${formatoNumero(s.acwr ?? 0, 2)}: ${sem.etiqueta} (${sem.rango})` : "Sin ACWR: menos de 28 días de historia"}
                  >
                    {sem ? (
                      <>
                        <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: sem.color }} />
                        {formatoNumero(s.acwr ?? 0, 2)}
                      </>
                    ) : (
                      <span className="text-text-secondary">—</span>
                    )}
                  </span>
                  <span className="tabular text-[11px] text-text-secondary">
                    {s.sueno_prom_h !== null ? `${formatoNumero(s.sueno_prom_h)} h` : "—"}
                  </span>
                  <span className="text-[10px] text-text-secondary">{etiquetaFecha(s.inicio)}</span>
                </li>
              );
            })}
          </ol>

          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 text-[10px] uppercase tracking-widest text-text-secondary">
            <dt>Barras</dt>
            <dd className="normal-case tracking-normal">Carga semanal (RPE × minutos)</dd>
            <dt>Punto</dt>
            <dd className="normal-case tracking-normal">ACWR al cierre de la semana</dd>
            <dt>Abajo</dt>
            <dd className="normal-case tracking-normal">
              Sueño promedio (objetivo {formatoNumero(q.data?.sueno_objetivo_h ?? 0)} h)
            </dd>
          </dl>

          <ul className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-text-secondary">
            {(Object.keys(SEMAFORO) as (keyof typeof SEMAFORO)[]).map((k) => (
              <li key={k} className="flex items-center gap-1.5">
                <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: SEMAFORO[k].color }} />
                {SEMAFORO[k].etiqueta} · {SEMAFORO[k].rango}
              </li>
            ))}
          </ul>
          {!hayCarga && (
            <p className="mt-3 text-[12px] text-text-secondary">Aún no hay sesiones registradas en estas semanas.</p>
          )}
        </>
      )}
      <p className="mt-4 text-[11px] leading-snug text-text-secondary">
        El ACWR es una heurística, no un diagnóstico: úsalo como una señal más, junto a cómo te sientes. Volver
        de un parón largo lo dispara aunque la carga sea razonable.
      </p>
    </TarjetaPregunta>
  );
}
