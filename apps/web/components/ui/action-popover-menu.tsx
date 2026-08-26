import type { ReactNode } from "react";
import { useState, useRef, useEffect } from "react";
import { MoreVertical } from "lucide-react";

type MenuItem = {
  label: string;
  onClick: () => void;
  icon?: ReactNode;
  danger?: boolean;
};

type Props = {
  items: MenuItem[];
};

/**
 * ActionPopoverMenu: boton de tres puntos que abre un menu vertical (DESIGN.md §3.2).
 * - Trigger: icono MoreVertical (lucide)
 * - Menu: lista vertical con items opcionales con icono
 * - Fondo bg-canvas, borde border-subtle, rounded-modal (20px)
 * - Click outside / ESC cierra
 * - Opcion destructiva (danger: true) en text-state-danger
 */
export function ActionPopoverMenu({ items }: Props) {
  const [abierto, setAbierto] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Cierra con click outside
  useEffect(() => {
    if (!abierto) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setAbierto(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [abierto]);

  // Cierra con ESC
  useEffect(() => {
    if (!abierto) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setAbierto(false);
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [abierto]);

  return (
    <div ref={menuRef} className="relative">
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setAbierto(!abierto)}
        className="rounded-full p-2 text-text-secondary hover:bg-surface-secondary hover:text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
        aria-label="Mas opciones"
        aria-expanded={abierto}
      >
        <MoreVertical className="h-5 w-5" />
      </button>

      {/* Menu desplegable */}
      {abierto && (
        <div
          className="absolute right-0 top-full mt-1 min-w-[160px] rounded-[20px] border border-border-subtle bg-surface-primary p-2 shadow-lg focus:outline-none"
          role="menu"
          aria-orientation="vertical"
        >
          {items.map((item, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                item.onClick();
                setAbierto(false);
              }}
              className={`flex w-full items-center gap-2 rounded-[16px] px-3 py-2 text-[13px] font-medium transition hover:bg-surface-secondary ${
                item.danger
                  ? "text-state-danger hover:bg-state-danger/10"
                  : "text-text-primary"
              }`}
              role="menuitem"
            >
              {item.icon && <span className="flex h-5 w-5 items-center justify-center">{item.icon}</span>}
              <span>{item.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
