import { PerfilScreen } from "@/components/ajustes/perfil-screen";

/**
 * Perfil del atleta: lo que el planificador (y el LLM, via el export
 * `perfil`) necesita saber de la persona para armar la semana.
 */
export default function PerfilPage() {
  return (
    <main className="mx-auto max-w-3xl px-5 pt-[calc(env(safe-area-inset-top)+2rem)] pb-24">
      <header className="mb-6">
        <h1 className="text-[28px] font-bold tracking-tight text-text-primary">Perfil del atleta</h1>
        <p className="mt-1 text-[13px] text-text-secondary">
          Posición, rol, objetivos y disponibilidad semanal. Se exporta al LLM para planear.
        </p>
      </header>
      <PerfilScreen />
    </main>
  );
}
