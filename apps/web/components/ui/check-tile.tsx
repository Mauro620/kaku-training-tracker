import { Check } from "lucide-react";

type Props = {
  nombre: string;
  checked: boolean;
  /** Estado de la mutation: deshabilita el tile mientras sincroniza. */
  sincronizando?: boolean;
  onToggle: () => void;
};

/**
 * Casilla de verificación rápida para hábitos (DESIGN.md §3.2).
 * Checkbox circular a la izquierda, nombre, fondo surface-secondary.
 * Sin animaciones decorativas: el check aparece instantáneo cuando el
 * estado del servidor cambia. El área tocable es toda la fila (44px+).
 */
export function CheckTile({ nombre, checked, sincronizando, onToggle }: Props) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={sincronizando}
      aria-pressed={checked}
      className="flex items-center gap-4 w-full min-h-[56px] bg-surface-secondary rounded-pill px-5 py-3 text-left disabled:opacity-60"
    >
      <span
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border ${
          checked ? "border-text-primary bg-text-primary text-canvas" : "border-border-subtle"
        }`}
      >
        {checked && <Check size={16} strokeWidth={3} aria-hidden />}
      </span>
      <span
        className={`flex-1 text-[15px] font-medium ${checked ? "text-text-primary" : "text-text-secondary"}`}
      >
        {nombre}
      </span>
    </button>
  );
}
