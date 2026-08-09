"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { CicloDetalleScreen } from "@/components/entreno/ciclo-detalle-screen";
import { haySesion } from "@/lib/auth";

type Props = { cicloId: number };

export function CicloDetalleCliente({ cicloId }: Props) {
  const router = useRouter();
  const [autenticado, setAutenticado] = useState(false);

  useEffect(() => {
    if (!haySesion()) {
      router.replace("/login");
      return;
    }
    setAutenticado(true);
  }, [router]);

  if (!autenticado || !Number.isFinite(cicloId)) {
    return null;
  }

  return (
    <main className="mx-auto max-w-3xl px-5 pt-[calc(env(safe-area-inset-top)+2rem)]">
      <Link
        href="/entreno/ciclos"
        className="mb-4 flex items-center gap-1 text-[13px] text-text-secondary"
      >
        <ChevronLeft size={16} /> Ciclos
      </Link>
      <CicloDetalleScreen cicloId={cicloId} />
    </main>
  );
}
