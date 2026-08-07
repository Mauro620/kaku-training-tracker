"use client";

import { RegistrarTestCard } from "@/components/progreso/registrar-test-card";
import { TestsList } from "@/components/progreso/tests-list";
import { MedidaCard } from "@/components/progreso/medida-card";
import { PartidoCard } from "@/components/progreso/partido-card";
import { useFechaDeRegistro } from "@/lib/fecha";

/**
 * Pantalla Progreso (Fase 7, ROADMAP §7): captura de test fisico con
 * cronometro por intento, medida corporal y ficha de partido. El
 * dashboard de metricas (mart_progreso_tests, graficos) es Fase 8.
 */
export function ProgresoScreen() {
  const fecha = useFechaDeRegistro();

  return (
    <div className="flex flex-col gap-4 pb-32">
      <RegistrarTestCard fecha={fecha} />
      <TestsList fecha={fecha} />
      <MedidaCard fecha={fecha} />
      <PartidoCard fecha={fecha} />
    </div>
  );
}
