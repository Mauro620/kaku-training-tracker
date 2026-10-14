"use client";

import { RegistrarTestCard } from "@/components/progreso/registrar-test-card";
import { TestsList } from "@/components/progreso/tests-list";
import { MedidaCard } from "@/components/progreso/medida-card";
import { PartidoCard } from "@/components/progreso/partido-card";
import { useFechaDeRegistro } from "@/lib/fecha";

/**
 * Captura de Progreso (antes la pantalla principal): test fisico con
 * cronometro por intento, medida corporal y ficha de partido.
 */
export function RegistrarScreen() {
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
