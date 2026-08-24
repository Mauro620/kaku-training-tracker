"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { ImportarPlanScreen } from "@/components/entreno/importar-plan-screen";
import { haySesion } from "@/lib/auth";

/**
 * Server component shim. Next 15 resuelve el param de la ruta padre
 * (/entreno) sin parametros dinamicos propios: por consistencia con el
 * resto del grupo (tabs) se mantiene el patron cliente+server split que
 * usa CicloDetallePage, aunque aca no haya [id].
 *
 * El server component existe para que la pagina sea estaticamente
 * generable y para que el guard de sesion corra del lado del cliente
 * sin desincronizar el server render con el reloj del usuario.
 */
export default function ImportarPlanPage() {
  return <ImportarPlanCliente />;
}

function ImportarPlanCliente() {
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
      <Link
        href="/entreno/ciclos"
        className="mb-4 flex items-center gap-1 text-[13px] text-text-secondary"
      >
        <ChevronLeft size={16} /> Ciclos
      </Link>
      <h1 className="mb-1 text-[24px] font-bold tracking-tight text-text-primary">
        Importar plan semanal
      </h1>
      <p className="mb-6 text-[13px] text-text-secondary">
        Pegá el JSON generado por vos o por un LLM a partir de
        <span className="ml-1 font-mono text-text-primary">
          docs/feature_1_session_plan_json/PLAN_IMPORT.md
        </span>
        . Reimportar la misma semana reemplaza los planes pendientes.
      </p>
      <ImportarPlanScreen />
    </main>
  );
}
