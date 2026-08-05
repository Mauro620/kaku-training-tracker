type Props = {
  /** Etiqueta corta arriba o abajo (DESIGN.md §3.1: subtexto en gris tenue). */
  etiqueta: string;
  /** Valor principal. Si es number, se renderiza en tipografía gigante bold. */
  valor: string | number;
  /** Unidad alineada a la baseline ("h", "kg", "min"). */
  unidad?: string;
  /** Posición de la etiqueta. Default "abajo". */
  etiquetaPos?: "arriba" | "abajo";
};

export function MetricDisplay({ etiqueta, valor, unidad, etiquetaPos = "abajo" }: Props) {
  const numero = (
    <span className="text-[36px] font-bold leading-none tabular text-text-primary">
      {valor}
      {unidad && (
        <span className="ml-1 text-sm font-medium text-text-secondary">{unidad}</span>
      )}
    </span>
  );

  const label = (
    <span className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
      {etiqueta}
    </span>
  );

  return (
    <div className="flex flex-col gap-1">
      {etiquetaPos === "arriba" && label}
      {numero}
      {etiquetaPos === "abajo" && label}
    </div>
  );
}
