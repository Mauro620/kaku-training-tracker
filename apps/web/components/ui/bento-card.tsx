import type { HTMLAttributes, ReactNode } from "react";

type Props = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  /** Full width (100%) o half (50%). Default full. */
  ancho?: "full" | "half";
};

/**
 * Contenedor base del design system (DESIGN.md §3.1).
 * Fondo surface-primary, borde sutil 1px, esquinas 24px.
 * Sin sombras de proyección: la profundidad se logra solo por color.
 */
export function BentoCard({ children, ancho = "full", className = "", ...rest }: Props) {
  const clasesAncho = ancho === "full" ? "w-full" : "w-full md:w-1/2";
  return (
    <div
      className={`bg-surface-primary border border-border-subtle rounded-bento p-6 ${clasesAncho} ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}
