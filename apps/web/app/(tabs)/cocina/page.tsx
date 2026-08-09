"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CocinaScreen } from "@/components/cocina/cocina-screen";
import { haySesion } from "@/lib/auth";

/**
 * Pagina Cocina (Fase 6, ROADMAP §6).
 * Mismo guard que las otras paginas (tabs): sin sesion redirige a /login.
 */
export default function CocinaPage() {
  const router = useRouter();
  const [autenticado, setAutenticado] = useState(false);

  useEffect(() => {
    if (!haySesion()) {
      router.replace("/login");
      return;
    }
    setAutenticado(true);
  }, [router]);

  if (!autenticado) {
    return null;
  }

  return (
    <main className="mx-auto max-w-3xl px-5 pt-[calc(env(safe-area-inset-top)+2rem)]">
      <header className="mb-6">
        <h1 className="text-[28px] font-bold tracking-tight text-text-primary">Cocina</h1>
        <p className="mt-1 text-[13px] text-text-secondary">
          Registra lo que comes y mira los macros del dia.
        </p>
      </header>
      <CocinaScreen />
    </main>
  );
}