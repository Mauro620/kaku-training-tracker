"use client";

import { BibliotecaRecetas } from "@/components/cocina/biblioteca-recetas";
import { ComidasList } from "@/components/cocina/comidas-list";
import { DespensaCard } from "@/components/cocina/despensa";
import { MacrosCard } from "@/components/cocina/macros-card";
import { RegistrarComida } from "@/components/cocina/registrar-comida";
import { useFechaDeRegistro } from "@/lib/fecha";

/**
 * Pantalla Cocina (Fase 6, ROADMAP §6).
 *
 * Composicion vertical: macros del dia arriba, comidas registradas,
 * formulario de registro, biblioteca de recetas, despensa.
 * La lista de mercado vive dentro de la card de despensa para que
 * un solo viaje HTTP traiga los dos pedidos relacionados.
 */
export function CocinaScreen() {
  const fecha = useFechaDeRegistro();
  return (
    <div className="flex flex-col gap-4 pb-32">
      <MacrosCard fecha={fecha} />
      <ComidasList fecha={fecha} />
      <RegistrarComida fecha={fecha} />
      <BibliotecaRecetas />
      <DespensaCard />
    </div>
  );
}