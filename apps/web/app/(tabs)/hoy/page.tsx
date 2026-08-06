"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { HoyScreen } from "@/components/hoy/hoy-screen";
import { haySesion } from "@/lib/auth";

/**
 * Página Hoy (ROADMAP §3).
 * Sin sesión redirige a /login. El guard corre en cliente porque el JWT
 * vive en localStorage (no hay cookie httpOnly todavía).
 */
export default function HoyPage() {
  const router = useRouter();
  const [autenticado, setAutenticado] = useState(false);

  useEffect(() => {
    if (!haySesion()) {
      router.replace("/login");
      return;
    }
    setAutenticado(true);
  }, [router]);

  // Nada dependiente de window/Date se renderiza en SSR: server y cliente
  // arrancan iguales (null), el contenido real llega recien en el efecto,
  // sin eso `new Date()...` desincroniza contra el reloj/timezone del server.
  if (!autenticado) {
    return null;
  }

  return (
    <main className="mx-auto max-w-3xl px-5 pt-8">
      <header className="mb-6">
        <h1 className="text-[28px] font-bold tracking-tight text-text-primary">Hoy</h1>
        <p className="mt-1 text-[13px] text-text-secondary">
          {new Date().toLocaleDateString("es-CO", {
            weekday: "long",
            day: "numeric",
            month: "long",
          })}
        </p>
      </header>
      <HoyScreen />
    </main>
  );
}
