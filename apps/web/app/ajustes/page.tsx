import { AjustesScreen } from "@/components/ajustes/ajustes-screen";

/**
 * Pantalla Ajustes (D1-D4 de la revision de UI).
 * Aqui vive el CRUD de habitos (catalogo del usuario).
 * Otras secciones se anadiran en fases futuras.
 */
export default function AjustesPage() {
  return (
    <main className="mx-auto max-w-3xl px-5 pt-[calc(env(safe-area-inset-top)+2rem)] pb-24">
      <header className="mb-6">
        <h1 className="text-[28px] font-bold tracking-tight text-text-primary">
          Ajustes
        </h1>
        <p className="mt-1 text-[13px] text-text-secondary">
          Personaliza tus habitos. Lo que desactives no se borra: queda
          archivado y vuelve a aparecer aqui si lo reactivas.
        </p>
      </header>
      <AjustesScreen />
    </main>
  );
}
