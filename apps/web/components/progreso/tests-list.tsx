"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { BentoCard } from "@/components/ui/bento-card";
import {
  useEliminarTest,
  useResultadoTest,
  useTestsDeFecha,
  useTiposTest,
  type TestFisico,
} from "@/lib/api/hooks";

export function TestsList({ fecha }: { fecha: string }) {
  const tests = useTestsDeFecha(fecha);
  const tipos = useTiposTest();

  if (tests.isLoading) {
    return (
      <BentoCard>
        <div className="h-16" />
      </BentoCard>
    );
  }

  if (!tests.data || tests.data.length === 0) {
    return null;
  }

  return (
    <BentoCard>
      <header className="mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Tests de hoy
        </p>
      </header>
      <ul className="flex flex-col gap-2">
        {tests.data.map((t) => (
          <TestRow
            key={t.id}
            test={t}
            fecha={fecha}
            tipoNombre={tipos.data?.find((ti) => ti.id === t.tipo_test_id)?.nombre ?? "test"}
          />
        ))}
      </ul>
    </BentoCard>
  );
}

function TestRow({
  test,
  fecha,
  tipoNombre,
}: {
  test: TestFisico;
  fecha: string;
  tipoNombre: string;
}) {
  const [abierto, setAbierto] = useState(false);
  const resultado = useResultadoTest(abierto ? test.id : null);
  const eliminar = useEliminarTest(fecha);

  return (
    <li className="rounded-bento bg-canvas px-4 py-3 text-[13px]">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setAbierto((v) => !v)}
          className="flex-1 text-left font-medium capitalize text-text-primary"
        >
          {tipoNombre}
          <span className="ml-2 text-text-secondary">
            {test.intentos.length} intento{test.intentos.length === 1 ? "" : "s"}
          </span>
        </button>
        <button
          type="button"
          onClick={() => eliminar.mutate(test.id)}
          aria-label="Eliminar test"
          className="p-1 text-text-secondary"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {abierto && (
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-text-secondary">
          {resultado.data && (
            <>
              <span>Mejor: {resultado.data.mejor}</span>
              <span>Media: {resultado.data.media}</span>
              {resultado.data.pct_decremento !== null && (
                <span>Decremento: {resultado.data.pct_decremento}%</span>
              )}
              {resultado.data.pct_cambio !== null && (
                <span
                  className={
                    Number(resultado.data.pct_cambio) >= 0
                      ? "text-state-positive"
                      : "text-state-danger"
                  }
                >
                  Cambio: {Number(resultado.data.pct_cambio) > 0 ? "+" : ""}
                  {resultado.data.pct_cambio}%
                </span>
              )}
            </>
          )}
        </div>
      )}
    </li>
  );
}
