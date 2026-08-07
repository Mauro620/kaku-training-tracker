"use client";

import { Apple, Beef, Wheat, Droplet } from "lucide-react";

import { BentoCard } from "@/components/ui/bento-card";
import { MetricDisplay } from "@/components/ui/metric-display";
import {
  useComidasDelDia,
  type MacroTotal,
} from "@/lib/api/hooks";

type Props = { fecha: string };

/**
 * Macros del dia (Fase 6, REGLAS_NEGOCIO §12).
 * Vienen del server en `GET /comidas?fecha=X`: el server ya sumo los
 * macros de cada comida (las que tienen receta resuelven sus ingredientes
 * via `receta_item`, las improvisadas usan sus `comida_item`).
 *
 * El server cuantiza a 2 decimales (ver `services/nutricion/calculo.py`),
 * asi que recibimos strings con precision estable y la UI no tiene que
 * formatear.
 */
export function MacrosCard({ fecha }: Props) {
  const { data, isLoading } = useComidasDelDia(fecha);

  const totales: MacroTotal = data?.macros_del_dia ?? {
    kcal: "0",
    proteina: "0",
    carbo: "0",
    grasa: "0",
    fibra: "0",
  };

  const comidas = data?.comidas.length ?? 0;

  return (
    <BentoCard>
      <header className="flex items-center justify-between mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Macros del dia
        </p>
        <span className="text-[11px] text-text-secondary">
          {comidas} {comidas === 1 ? "comida" : "comidas"}
        </span>
      </header>

      {isLoading ? (
        <div className="h-32" />
      ) : (
        <>
          <MetricDisplay
            etiqueta="Energia"
            valor={totales.kcal}
            unidad="kcal"
            etiquetaPos="arriba"
          />

          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            <MacroMini
              icono={Beef}
              etiqueta="Proteina"
              valor={totales.proteina}
              unidad="g"
            />
            <MacroMini
              icono={Wheat}
              etiqueta="Carbo"
              valor={totales.carbo}
              unidad="g"
            />
            <MacroMini
              icono={Droplet}
              etiqueta="Grasa"
              valor={totales.grasa}
              unidad="g"
            />
            <MacroMini
              icono={Apple}
              etiqueta="Fibra"
              valor={totales.fibra}
              unidad="g"
            />
          </div>
        </>
      )}
    </BentoCard>
  );
}

function MacroMini({
  icono: Icono,
  etiqueta,
  valor,
  unidad,
}: {
  icono: typeof Apple;
  etiqueta: string;
  valor: string;
  unidad: string;
}) {
  // Tachamos el icono con un color tenue para no sobrecargar la card.
  return (
    <div className="flex flex-col gap-1">
      <span className="flex items-center gap-1.5 text-[11px] tracking-widest uppercase text-text-secondary">
        <Icono size={14} aria-hidden />
        {etiqueta}
      </span>
      <span className="text-[24px] font-bold leading-none tabular text-text-primary">
        {valor}
        <span className="ml-1 text-sm font-medium text-text-secondary">{unidad}</span>
      </span>
    </div>
  );
}