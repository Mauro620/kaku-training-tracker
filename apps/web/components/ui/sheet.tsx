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
 *
 * Side effect: al abrir bloquea el scroll del body (overflow-hidden) para
 * que el sheet no haga scroll-into-view ni que la pagina quede scrollable
 * detras del overlay. Se restaura al cerrar.
 *
 * Tambien fuerza scrollTop=0 al abrir para que el contenido siempre
 * aparezca desde el nombre del ejercicio, no desde el menu de acciones
 * al fondo. Cubrimos el caso del focus automatico (tabIndex=-1 + .focus())
 * y el caso de scrollIntoView disparado por React al insertar el nodo.
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

  // Bloquea scroll del body mientras el sheet esta abierto.
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  // Reset scroll al abrir SOLO si quedo cerca del final. Hay tres fuentes
  // que pueden dejar el scroll al fondo en algunos navegadores:
  // 1. React 19 + scrollIntoView automatico al montar el nodo.
  // 2. El focus automatico del sheet container (tabIndex=-1).
  // 3. El focus de un input interior (autoFocus).
  //
  // Si el scroll quedo al fondo (maximo), lo reseteamos al inicio durante
  // los primeros 200ms tras el open. Si el scroll es chico (porque el
  // usuario ya empezo a scrollear), no tocamos nada.
  useEffect(() => {
    if (!open) return;
    let raf = 0;
    const start = performance.now();
    const tick = () => {
      const el = contentRef.current;
      if (!el) return;
      if (performance.now() - start > 200) return;
      // Si el scroll esta cerca del fondo (>= 95% del maximo), es
      // automatico del navegador, no del usuario. Lo reseteamos.
      const max = el.scrollHeight - el.clientHeight;
      if (max > 0 && el.scrollTop >= max * 0.95) {
        el.scrollTop = 0;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
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
