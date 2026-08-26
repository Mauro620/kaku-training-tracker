import type { ReactNode } from "react";

type Props = {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
};

/**
 * EmptyState: estado vacio diseñado (DESIGN.md §3.1).
 * - Icono opcional centrado
 * - Titulo centrado
 * - Descripcion opcional en text-text-secondary
 * - Accion opcional como botón pill
 */
export function EmptyState({ icon, title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8">
      {icon && (
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-surface-secondary text-text-secondary">
          {icon}
        </div>
      )}

      <div className="text-center">
        <h3 className="text-[16px] font-semibold text-text-primary">{title}</h3>
        {description && (
          <p className="mt-1 text-[13px] text-text-secondary">{description}</p>
        )}
      </div>

      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="mt-2 rounded-full bg-accent px-6 py-2.5 text-[14px] font-semibold text-bg transition hover:bg-accent/90 focus:outline-none focus:ring-2 focus:ring-accent"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
