"use client";

import { SesionForm } from "@/components/entreno/sesion-form";
import { SesionesList } from "@/components/entreno/sesiones-list";
import { MolestiaForm } from "@/components/entreno/molestia-form";
import { useFechaDeRegistro } from "@/lib/fecha";
import { useMolestiasDeFecha, usePlanesDeFecha } from "@/lib/api/hooks";

/**
 * Pantalla Entreno (Fase 4, ROADMAP §4).
 * Composicion: lista de sesiones del dia arriba, form de captura + form
 * de molestia. Los planes de hoy (ciclo R2) se resuelven una vez acá y se
 * pasan a ambos: el form los usa para sugerir/linkear, la lista para
 * mostrar el delta contra lo real.
 */
export function EntrenoScreen() {
  const fecha = useFechaDeRegistro();
  const molestias = useMolestiasDeFecha(fecha);
  const planes = usePlanesDeFecha(fecha);

  return (
    <div className="flex flex-col gap-4 pb-32">
      <SesionesList fecha={fecha} planes={planes.data ?? []} />
      <SesionForm fecha={fecha} planes={planes.data ?? []} />
      <MolestiaForm fecha={fecha} existentes={molestias.data ?? []} />
    </div>
  );
}
