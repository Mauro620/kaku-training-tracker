import type { ReactNode } from "react";
import { BentoCard } from "@/components/ui/bento-card";

type Props = {
  numero: number;
  pregunta: string;
  /** La respuesta en una frase; null mientras carga. */
  conclusion: string | null;
  cargando?: boolean;
  error?: boolean;
  children?: ReactNode;
};

/**
 * Tarjeta de Progreso: una pregunta, su respuesta en una frase, y el grafico
 * como evidencia. La frase va primero: si solo se lee eso, ya se sabe.
 */
export function TarjetaPregunta({ numero, pregunta, conclusion, cargando, error, children }: Props) {
  return (
    <BentoCard aria-labelledby={`pregunta-${numero}`}>
      <p
        id={`pregunta-${numero}`}
        className="text-[11px] font-normal uppercase tracking-widest text-text-secondary"
      >
        {numero}. {pregunta}
      </p>
      {cargando ? (
        <div className="mt-3 h-24 animate-pulse rounded-xl bg-surface-secondary" />
      ) : error ? (
        <p className="mt-3 text-[13px] text-state-danger">No se pudo cargar esta tarjeta.</p>
      ) : (
        <>
          <p className="mt-3 text-[17px] font-semibold leading-snug text-text-primary">{conclusion}</p>
          <div className="mt-4">{children}</div>
        </>
      )}
    </BentoCard>
  );
}
