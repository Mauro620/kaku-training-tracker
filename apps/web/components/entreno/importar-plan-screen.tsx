"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, Clipboard, FileJson, Loader2 } from "lucide-react";
import { BentoCard } from "@/components/ui/bento-card";
import { ApiError } from "@/lib/api/client";
import {
  obtenerExportsLLM,
  useImportarPlanSemanal,
  type ImportacionResultado,
} from "@/lib/api/hooks";
import { copiarParaLLM, validarForma, type ErrorLocal } from "@/lib/importar-plan";

// Pantalla de importacion de plan semanal por JSON (Fase 4 R4 +
// llm-export-endpoints).
// Pasos en una sola vista:
//   0. (opcional) Copiar reglas + catalogo + ejemplo + perfil (+ resumen del ciclo si existe)
//      para pegarle a un LLM.
//   1. Pegar el JSON en un textarea
//   2. Validar la forma en el cliente (lo que se puede saber sin tocar BD)
//   3. Enviar al server; mostrar el resultado con advertencias y ejercicios
//      creados antes de volver al detalle del ciclo.
//
// Decisiones:
// - `validarForma`/`copiarParaLLM` viven en lib/importar-plan.ts (no aca):
//   apps/web no tiene jsdom/@testing-library/react y tsconfig usa
//   `jsx: "preserve"` (pensado para el compilador de Next), que vite/esbuild
//   rechaza al importar un .tsx directo en un test. Separando la logica pura
//   se puede testear sin agregar jsdom/RTL ni tocar vitest.config.ts.
// - Sin carga de archivo: el flujo natural es copy-paste desde un LLM o
//   desde el editor. Cero friccion.
// - Sin cola offline (lib/sync/outbox): la importacion es deliberada y
//   requiere server. Si falla por red, el usuario reintenta.

export function ImportarPlanScreen() {
  const router = useRouter();
  const importar = useImportarPlanSemanal();

  const [texto, setTexto] = useState("");
  const [errorLocal, setErrorLocal] = useState<ErrorLocal>(null);
  const [resultado, setResultado] = useState<ImportacionResultado | null>(null);
  const [copia, setCopia] = useState<"idle" | "copiando" | "ok" | "error">("idle");

  const { payload, error: errorValidacion } = validarForma(texto);

  async function copiarParaElLLM() {
    setCopia("copiando");
    const estado = await copiarParaLLM({
      obtenerExports: obtenerExportsLLM,
      clipboard: navigator.clipboard,
    });
    setCopia(estado);
    if (estado === "ok") {
      setTimeout(() => setCopia("idle"), 2000);
    }
  }

  async function enviar() {
    setErrorLocal(null);
    setResultado(null);
    if (!payload) {
      // El usuario alcanzo el boton: debe haber un error visible.
      setErrorLocal("Revisa el JSON: hay errores de forma.");
      return;
    }
    try {
      const r = await importar.mutateAsync(payload);
      setResultado(r);
    } catch (e) {
      setErrorLocal(e instanceof ApiError ? e.message : "No se pudo importar.");
    }
  }

  return (
    <div className="flex flex-col gap-4 pb-32">
      <BentoCard>
        <button
          type="button"
          onClick={copiarParaElLLM}
          disabled={copia === "copiando"}
          className="flex w-full items-center justify-center gap-2 rounded-pill bg-surface-secondary py-2.5 text-[13px] font-medium text-text-primary disabled:opacity-50"
        >
          {copia === "copiando" ? (
            <>
              <Loader2 size={14} className="animate-spin" /> Copiando...
            </>
          ) : (
            <>
              <Clipboard size={14} /> Copiar para el LLM
            </>
          )}
        </button>
        {copia === "ok" && (
          <p className="mt-2 flex items-center gap-2 text-[12px] text-state-positive">
            <CheckCircle2 size={14} /> Copiado al portapapeles.
          </p>
        )}
        {copia === "error" && (
          <p className="mt-2 flex items-center gap-2 text-[12px] text-state-danger">
            <AlertTriangle size={14} /> No se pudo copiar. Reintenta.
          </p>
        )}
      </BentoCard>

      <BentoCard>
        <label className="flex flex-col gap-2">
          <span className="text-[11px] font-normal uppercase tracking-widest text-text-secondary">
            JSON del plan
          </span>
          <textarea
            value={texto}
            onChange={(e) => {
              setTexto(e.target.value);
              setErrorLocal(null);
              setResultado(null);
            }}
            spellCheck={false}
            rows={14}
            placeholder='{"version": 2, "ciclo": { ... }, "semana": { ... }, "sesiones": [ ... ]}'
            className="resize-y rounded-bento border border-border-subtle bg-canvas p-3 font-mono text-[12px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>

        {(errorLocal || (texto.trim() && errorValidacion)) && (
          <div className="mt-3 flex items-start gap-2 rounded-pill bg-surface-secondary px-3 py-2 text-[12px] text-state-danger">
            <AlertTriangle size={14} className="mt-0.5 shrink-0" />
            <span>{errorLocal ?? errorValidacion}</span>
          </div>
        )}

        <div className="mt-3 flex gap-2">
          <button
            type="button"
            onClick={() => {
              setTexto("");
              setErrorLocal(null);
              setResultado(null);
            }}
            disabled={!texto || importar.isPending}
            className="flex-1 rounded-pill bg-surface-secondary py-2.5 text-[13px] font-medium text-text-primary disabled:opacity-50"
          >
            Limpiar
          </button>
          <button
            type="button"
            onClick={enviar}
            disabled={!payload || importar.isPending}
            className="flex flex-1 items-center justify-center gap-2 rounded-pill bg-text-primary py-2.5 text-[13px] font-semibold text-canvas disabled:opacity-50"
          >
            {importar.isPending ? (
              <>
                <Loader2 size={14} className="animate-spin" /> Importando...
              </>
            ) : (
              <>
                <FileJson size={14} /> Importar
              </>
            )}
          </button>
        </div>
      </BentoCard>

      {resultado && <ResultadoImportacion resultado={resultado} onIrACiclo={() =>
        router.push(`/entreno/ciclos/${resultado.ciclo_id}`)
      } />}
    </div>
  );
}

function ResultadoImportacion({
  resultado,
  onIrACiclo,
}: {
  resultado: ImportacionResultado;
  onIrACiclo: () => void;
}) {
  const total =
    resultado.sesiones_creadas +
    resultado.sesiones_reemplazadas +
    resultado.sesiones_omitidas;
  return (
    <BentoCard>
      <div className="mb-3 flex items-start gap-2">
        <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-state-positive" />
        <div className="flex-1">
          <p className="text-[15px] font-semibold text-text-primary">
            Importacion completa
          </p>
          <p className="mt-0.5 text-[12px] text-text-secondary">
            {total === 0
              ? "Nada que cambiar."
              : `${resultado.sesiones_creadas} creadas · ${resultado.sesiones_reemplazadas} reemplazadas · ${resultado.sesiones_omitidas} omitidas`}
          </p>
          <p className="mt-1 text-[11px] uppercase tracking-widest text-text-secondary">
            Cubre del {formatearFecha(resultado.ciclo_semana_inicio)}
            {" al "}
            {formatearFecha(resultado.ciclo_semana_fin)}
          </p>
        </div>
      </div>

      {resultado.ejercicios_creados.length > 0 && (
        <div className="mt-3">
          <p className="text-[11px] uppercase tracking-widest text-text-secondary">
            Ejercicios nuevos
          </p>
          <ul className="mt-1 flex flex-wrap gap-1">
            {resultado.ejercicios_creados.map((e) => (
              <li
                key={e}
                className="rounded-pill bg-surface-secondary px-3 py-1 text-[12px] text-text-primary"
              >
                {e}
              </li>
            ))}
          </ul>
        </div>
      )}

      {resultado.advertencias.length > 0 && (
        <div className="mt-3">
          <p className="text-[11px] uppercase tracking-widest text-text-secondary">
            Advertencias
          </p>
          <ul className="mt-1 flex flex-col gap-1">
            {resultado.advertencias.map((a, i) => (
              <li
                key={i}
                className="flex items-start gap-2 rounded-pill bg-canvas px-3 py-1.5 text-[12px] text-state-warning"
              >
                <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                <span>{a}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        type="button"
        onClick={onIrACiclo}
        className="mt-4 w-full rounded-pill bg-canvas py-2.5 text-[13px] font-semibold text-text-primary"
      >
        Ir al ciclo
      </button>
    </BentoCard>
  );
}

// Formato corto, locale-aware. El backend manda YYYY-MM-DD; parseamos como
// local-date (no UTC) para no correr el dia por la zona horaria.
function formatearFecha(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  const fecha = new Date(y, m - 1, d);
  return fecha.toLocaleDateString("es-CO", {
    day: "numeric",
    month: "short",
  });
}
