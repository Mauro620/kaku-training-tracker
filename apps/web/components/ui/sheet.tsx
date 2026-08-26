import type { HTMLAttributes, ReactNode } from "react";
import { useEffect, useRef } from "react";
import { X } from "lucide-react";

type Props = HTMLAttributes<HTMLDivElement> & {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
};

/**
 * Sheet: panel deslizante desde abajo (DESIGN.md §3.2).
 * - Slide-up animation desde bottom
 * - Max 90vh de alto
 * - Bordes redondeados 20px (rounded-modal)
 * - Fondo bg-canvas (dark)
 * - Focus trap basico
 * - ESC cierra, click outside cierra
 */
export function Sheet({ open, onClose, title, children, className = "", ...rest }: Props) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  // Cierra con ESC
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  // Focus trap basico: enfoca el contenido al abrir
  useEffect(() => {
    if (open && contentRef.current) {
      contentRef.current.focus();
    }
  }, [open]);

  if (!open) return null;

  return (
    <>
      {/* Overlay con backdrop blur */}
      <div
        ref={overlayRef}
        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sheet panel */}
      <div
        ref={contentRef}
        tabIndex={-1}
        className={`fixed inset-x-0 bottom-0 z-50 max-h-[90vh] overflow-y-auto rounded-t-[20px] bg-surface-primary p-6 shadow-lg focus:outline-none ${className}`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? "sheet-title" : undefined}
        {...rest}
      >
        {/* Header con titulo y boton de cerrar */}
        {title && (
          <div className="mb-4 flex items-center justify-between">
            <h2 id="sheet-title" className="text-[18px] font-semibold text-text-primary">
              {title}
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full p-2 text-text-secondary hover:bg-surface-secondary hover:text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
              aria-label="Cerrar"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        )}

        {/* Contenido */}
        {children}
      </div>
    </>
  );
}
