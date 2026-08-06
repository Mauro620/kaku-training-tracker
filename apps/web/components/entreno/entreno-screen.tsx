"use client";

import { SesionForm } from "@/components/entreno/sesion-form";
import { SesionesList } from "@/components/entreno/sesiones-list";
import { MolestiaForm } from "@/components/entreno/molestia-form";
import { useFechaDeRegistro } from "@/lib/fecha";
import { useMolestiasDeFecha } from "@/lib/api/hooks";

/**
 * Pantalla Entreno (Fase 4 R1, ROADMAP §4).
 * Composicion: lista de sesiones del dia arriba, form de captura + form
 * de molestia. Sin plan todavia (rebanada 2 de Fase 4).
 */
export function EntrenoScreen() {
  const fecha = useFechaDeRegistro();
  const molestias = useMolestiasDeFecha(fecha);

  return (
    <div className="flex flex-col gap-4 pb-32">
      <SesionesList fecha={fecha} />
      <SesionForm fecha={fecha} />
      <MolestiaForm fecha={fecha} existentes={molestias.data ?? []} />
    </div>
  );
}
