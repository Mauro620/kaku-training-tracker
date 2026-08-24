"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { BentoCard } from "@/components/ui/bento-card";
import { CicloActivoCard } from "@/components/entreno/ciclo-activo-card";
import { PlanDeHoyCard } from "@/components/entreno/plan-de-hoy-card";
import { RestoDeLaSemana } from "@/components/entreno/resto-de-la-semana";
import { HistoricoSesiones } from "@/components/entreno/historico-sesiones";
import { SesionForm } from "@/components/entreno/sesion-form";
import { SesionDetalle } from "@/components/entreno/sesion-detalle";
import { MolestiaForm } from "@/components/entreno/molestia-form";
import { useFechaDeRegistro } from "@/lib/fecha";
import { diaDeLaSemana, useSemanaActual } from "@/lib/semana";
import {
  useMolestiasDeFecha,
  usePlanesDeFecha,
  useSesionesDeFecha,
  type SesionPlan,
} from "@/lib/api/hooks";

/**
 * Pantalla Entreno (Fase 4, ROADMAP §4).
 *
 * Orden: ciclo + progreso, plan de hoy, resto de la semana, historico,
 * molestias. La tarjeta de plan de hoy es la que manda: antes la pantalla
 * solo listaba sesiones REALES, asi que con el plan importado igual decia
 * "Aun no hay sesiones hoy".
 *
 * Cambiar una sesion de dia no necesita mecanismo propio: se elige otro plan
 * de la semana y se registra con la fecha de hoy. El backend deriva `movido`
 * comparando esa fecha contra `dia_sugerido`.
 */
export function EntrenoScreen() {
  const fecha = useFechaDeRegistro();
  const molestias = useMolestiasDeFecha(fecha);
  const planesDeHoy = usePlanesDeFecha(fecha);
  const sesionesDeHoy = useSesionesDeFecha(fecha);
  const semana = useSemanaActual(fecha);

  const [pedido, setPedido] = useState<{
    plan: SesionPlan | null;
    nonce: number;
  } | null>(null);
  const [sesionAbierta, setSesionAbierta] = useState<string | null>(null);
  const [molestiaAbierta, setMolestiaAbierta] = useState(false);

  const diaDeHoy = semana.ciclo ? diaDeLaSemana(semana.ciclo.fecha_inicio, fecha) : null;

  return (
    <div className="flex flex-col gap-4 pb-32">
      <CicloActivoCard fecha={fecha} />

      <PlanDeHoyCard
        planesDeHoy={planesDeHoy.data ?? []}
        sesionesDeHoy={sesionesDeHoy.data ?? []}
        planesDeLaSemana={semana.planes}
        onEmpezar={(plan) => setPedido({ plan, nonce: Date.now() })}
        onVerSesion={setSesionAbierta}
      />

      <RestoDeLaSemana planes={semana.planes} diaDeHoy={diaDeHoy} />

      <SesionForm fecha={fecha} planes={planesDeHoy.data ?? []} pedido={pedido} />

      <HistoricoSesiones onVerSesion={setSesionAbierta} />

      {/* Registrar una molestia pasa pocas veces; no justifica un tercio de
          la pantalla con 13 chips siempre visibles. */}
      {molestiaAbierta || (molestias.data?.length ?? 0) > 0 ? (
        <MolestiaForm fecha={fecha} existentes={molestias.data ?? []} />
      ) : (
        <BentoCard>
          <button
            type="button"
            onClick={() => setMolestiaAbierta(true)}
            className="flex w-full items-center gap-2 text-[13px] font-medium text-text-secondary"
          >
            <Plus size={16} />
            Molestia
          </button>
        </BentoCard>
      )}

      {sesionAbierta && (
        <SesionDetalle
          sesionId={sesionAbierta}
          onCerrar={() => setSesionAbierta(null)}
        />
      )}
    </div>
  );
}
