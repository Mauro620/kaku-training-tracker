type Props = { titulo: string; fase: number };

/**
 * Placeholder para pestañas que aún no se construyeron (Fase 4/6/8).
 * El link sigue presente en el bottom nav, pero la pantalla muestra
 * honestamente que la funcionalidad no está lista todavía.
 */
export function TabPlaceholder({ titulo, fase }: Props) {
  return (
    <main className="mx-auto max-w-3xl px-5 pt-8">
      <header className="mb-6">
        <h1 className="text-[28px] font-bold tracking-tight text-text-primary">{titulo}</h1>
      </header>
      <div className="bg-surface-primary border border-border-subtle rounded-bento p-6">
        <p className="text-[14px] text-text-secondary">
          Disponible en fase {fase}.
        </p>
      </div>
    </main>
  );
}
