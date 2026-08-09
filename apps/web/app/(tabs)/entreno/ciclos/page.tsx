"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CiclosScreen } from "@/components/entreno/ciclos-screen";
import { haySesion } from "@/lib/auth";

export default function CiclosPage() {
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
        <h1 className="text-[28px] font-bold tracking-tight text-text-primary">Ciclos</h1>
        <p className="mt-1 text-[13px] text-text-secondary">
          Planifica bloques de entrenamiento.
        </p>
      </header>
      <CiclosScreen />
    </main>
  );
}
