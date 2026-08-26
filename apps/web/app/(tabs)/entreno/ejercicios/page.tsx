import { BancoScreen } from "@/components/entreno/banco-screen";

/**
 * Ruta del banco de ejercicios.
 * Server component que renderiza el BancoScreen dentro del mismo shell
 * que la pantalla Entreno: max-w-3xl + px-5 + pt del safe-area + pb-32
 * para que el ultimo row no quede tapado por el bottom-nav.
 */
export default function EjerciciosPage() {
  return (
    <main className="mx-auto max-w-3xl px-5 pt-[calc(env(safe-area-inset-top)+2rem)]">
      <header className="mb-6">
        <h1 className="text-[28px] font-bold tracking-tight text-text-primary">Banco de ejercicios</h1>
      </header>
      <BancoScreen />
    </main>
  );
}
