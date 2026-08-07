"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ProgresoScreen } from "@/components/progreso/progreso-screen";
import { haySesion } from "@/lib/auth";

/**
 * Pagina Progreso (Fase 7, ROADMAP §7).
 * Mismo guard que las otras paginas (tabs): sin sesion redirige a /login.
 */
export default function ProgresoPage() {
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
    <main className="mx-auto max-w-3xl px-5 pt-8">
      <header className="mb-6">
        <h1 className="text-[28px] font-bold tracking-tight text-text-primary">Progreso</h1>
        <p className="mt-1 text-[13px] text-text-secondary">
          Tests fisicos, medida corporal y fichas de partido.
        </p>
      </header>
      <ProgresoScreen />
    </main>
  );
}
