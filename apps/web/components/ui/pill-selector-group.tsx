type Opcion<T> = { valor: T; etiqueta?: string };

type Props<T extends string | number> = {
  opciones: ReadonlyArray<Opcion<T>>;
  valor: T;
  onChange: (siguiente: T) => void;
  /** Etiqueta accesible del grupo, ej. "Calidad de sueño". */
  label: string;
};

/**
 * Selector horizontal de píldoras (DESIGN.md §3.2 PillSelectorGroup).
 * Inactiva: fondo surface-secondary, texto secundario. Activa: fondo blanco,
 * texto negro bold. Toca una pill para elegirla.
 */
export function PillSelectorGroup<T extends string | number>({
  opciones,
  valor,
  onChange,
  label,
}: Props<T>) {
  return (
    <div role="radiogroup" aria-label={label} className="flex gap-2 flex-wrap">
      {opciones.map((opcion) => {
        const activa = opcion.valor === valor;
        return (
          <button
            key={String(opcion.valor)}
            type="button"
            role="radio"
            aria-checked={activa}
            onClick={() => onChange(opcion.valor)}
            className={`min-h-[40px] min-w-[40px] px-4 rounded-pill text-[14px] font-bold ${
              activa
                ? "bg-text-primary text-canvas"
                : "bg-surface-secondary text-text-secondary"
            }`}
          >
            {opcion.etiqueta ?? String(opcion.valor)}
          </button>
        );
      })}
    </div>
  );
}
