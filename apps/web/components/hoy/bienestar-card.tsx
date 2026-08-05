"use client";

import { useEffect, useState } from "react";
import { BentoCard } from "@/components/ui/bento-card";
import { PillSelectorGroup } from "@/components/ui/pill-selector-group";
import {
  useBienestarDeHoy,
  useUpsertBienestar,
  type RegistroBienestar,
} from "@/lib/api/hooks";

type Props = { fecha: string };

const ITEMS_HOOPER: Array<{
  clave: keyof Pick<
    RegistroBienestar,
    "sueno_pobre" | "fatiga" | "dolor_muscular" | "estres"
  >;
  etiqueta: string;
}> = [
  { clave: "sueno_pobre", etiqueta: "Sueño pobre" },
  { clave: "fatiga", etiqueta: "Fatiga" },
  { clave: "dolor_muscular", etiqueta: "Dolor muscular" },
  { clave: "estres", etiqueta: "Estrés" },
];

// SPEC §2.1: 1 es bueno, 5 es malo. La pantalla refleja la dirección.
const ESCALA = [1, 2, 3, 4, 5] as const;

/**
 * Bienestar del día (DESIGN.md §2.1, SPEC.md §2.1, REGLAS_NEGOCIO §5).
 * Cuatro sliders de Hooper (1-5). El cálculo del hooper lo hace la base.
 * Sin modal: edición inline con pills.
 */
export function BienestarCard({ fecha }: Props) {
  const { data, isLoading } = useBienestarDeHoy(fecha);
  const mutacion = useUpsertBienestar(fecha);

  const [borrador, setBorrador] = useState<{
    sueno_pobre: number;
    fatiga: number;
    dolor_muscular: number;
    estres: number;
  } | null>(null);
  const [editando, setEditando] = useState(false);

  useEffect(() => {
    if (data && !editando && borrador === null) {
      setBorrador({
        sueno_pobre: data.sueno_pobre,
        fatiga: data.fatiga,
        dolor_muscular: data.dolor_muscular,
        estres: data.estres,
      });
    }
  }, [data, editando, borrador]);

  const pendiente =
    editando &&
    borrador !== null &&
    data !== undefined &&
    (borrador.sueno_pobre !== data.sueno_pobre ||
      borrador.fatiga !== data.fatiga ||
      borrador.dolor_muscular !== data.dolor_muscular ||
      borrador.estres !== data.estres);

  const hooper = borrador
    ? borrador.sueno_pobre + borrador.fatiga + borrador.dolor_muscular + borrador.estres
    : (data?.hooper ?? null);

  return (
    <BentoCard ancho="half">
      <header className="flex items-center justify-between mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Bienestar
        </p>
        {hooper !== null && (
          <span className="text-[11px] uppercase tracking-widest text-text-secondary">
            Hooper {hooper}
          </span>
        )}
      </header>

      {isLoading || borrador === null ? (
        <div className="h-32" />
      ) : (
        <div className="flex flex-col gap-4">
          {ITEMS_HOOPER.map(({ clave, etiqueta }) => (
            <div key={clave} className="flex flex-col gap-2">
              <span className="text-[13px] text-text-secondary">{etiqueta}</span>
              <PillSelectorGroup
                label={etiqueta}
                opciones={ESCALA.map((n) => ({ valor: n }))}
                valor={borrador[clave]}
                onChange={(siguiente) => {
                  setBorrador({ ...borrador, [clave]: siguiente });
                  setEditando(true);
                }}
              />
            </div>
          ))}

          {pendiente && (
            <button
              type="button"
              onClick={async () => {
                await mutacion.mutateAsync(borrador);
                setEditando(false);
              }}
              disabled={mutacion.isPending}
              className="mt-2 w-full bg-text-primary text-canvas rounded-pill py-3 text-[14px] font-semibold disabled:opacity-50"
            >
              {mutacion.isPending ? "Guardando..." : "Guardar bienestar"}
            </button>
          )}
        </div>
      )}
    </BentoCard>
  );
}
