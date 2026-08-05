"use client";

import { useEffect } from "react";
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

  useEffect(() => {
    if (!haySesion()) {
      router.replace("/login");
    }
  }, [router]);

  if (typeof window !== "undefined" && !haySesion()) {
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
