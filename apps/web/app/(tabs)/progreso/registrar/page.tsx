"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { RegistrarScreen } from "@/components/progreso/registrar-screen";
import { haySesion } from "@/lib/auth";

/** Captura de tests, medida corporal y partidos. Mismo guard que las demas. */
export default function RegistrarProgresoPage() {
  const router = useRouter();
  const [autenticado, setAutenticado] = useState(false);

  useEffect(() => {
    if (!haySesion()) {
      router.replace("/login");
      return;
    }
    setAutenticado(true);
  }, [router]);

  if (!autenticado) return null;

  return (
    <main className="mx-auto max-w-3xl px-5 pt-[calc(env(safe-area-inset-top)+2rem)]">
      <header className="mb-6">
        <Link href="/progreso" className="text-[12px] text-text-secondary">
          ‹ Progreso
        </Link>
        <h1 className="mt-1 text-[28px] font-bold tracking-tight text-text-primary">Registrar</h1>
        <p className="mt-1 text-[13px] text-text-secondary">
          Tests físicos, medida corporal y fichas de partido.
        </p>
      </header>
      <RegistrarScreen />
    </main>
  );
}
