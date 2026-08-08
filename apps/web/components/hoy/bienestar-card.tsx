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

type Borrador = {
  sueno_pobre: number;
  fatiga: number;
  dolor_muscular: number;
  estres: number;
};

const DEBOUNCE_MS = 800;

const ITEMS_HOOPER: Array<{
  clave: keyof Borrador;
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
 *
 * Cuatro sliders de Hooper (1-5). El cálculo del hooper lo hace la base.
 * Autoguardado con debounce, sin botón.
 *
 * A1 (review de UI): la tarjeta debe estar SIEMPRE lista para usar, no
 * esperar a que llegue data del server. Esto retrasa la linea base de
 * Hooper: cada dia sin este campo suma un dia de retardo a fase 8.
 *
 * Estrategia: los sliders renderizan desde el primer render con un
 * estado `borrador` que puede ser null (no se eligio nada) o un
 * objeto con los 4 valores. Si llega data del server, hidrata el
 * borrador. El autoguardado solo se dispara en el primer toque
 * (`tocado=true`); si el usuario nunca toca, no hay row en la DB.
 */
export function BienestarCard({ fecha }: Props) {
  const { data } = useBienestarDeHoy(fecha);
  const { mutate, isPending, isSuccess } = useUpsertBienestar(fecha);

  const [borrador, setBorrador] = useState<Borrador | null>(null);
  const [tocado, setTocado] = useState(false);

  useEffect(() => {
    if (data && !tocado && borrador === null) {
      setBorrador({
        sueno_pobre: data.sueno_pobre,
        fatiga: data.fatiga,
        dolor_muscular: data.dolor_muscular,
        estres: data.estres,
      });
    }
  }, [data, tocado, borrador]);

  useEffect(() => {
    if (!tocado || borrador === null) return;
    const id = setTimeout(() => mutate(borrador), DEBOUNCE_MS);
    return () => clearTimeout(id);
  }, [borrador, tocado, mutate]);

  const hooper = borrador
    ? borrador.sueno_pobre + borrador.fatiga + borrador.dolor_muscular + borrador.estres
    : (data?.hooper ?? null);

  return (
    <BentoCard>
      <header className="flex items-center justify-between mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Bienestar
        </p>
        <div className="flex items-center gap-2">
          {hooper !== null && (
            <span className="text-[11px] uppercase tracking-widest text-text-secondary">
              Hooper {hooper}
            </span>
          )}
          <span className="text-[11px] text-text-secondary">
            {isPending ? "Guardando…" : isSuccess || data ? "Guardado" : ""}
          </span>
        </div>
      </header>
      <p className="mb-4 text-[11px] text-text-secondary">
        1 bien · 5 mal. La direccion es contraintuitiva: mas alto es peor.
      </p>

      <div className="flex flex-col gap-4">
        {ITEMS_HOOPER.map(({ clave, etiqueta }) => (
          <div key={clave} className="flex flex-col gap-2">
            <span className="text-[13px] text-text-secondary">{etiqueta}</span>
            <PillSelectorGroup
              label={etiqueta}
              opciones={ESCALA.map((n) => ({ valor: n }))}
              valor={borrador ? borrador[clave] : null}
              onChange={(siguiente) => {
                setBorrador((b) => ({
                  sueno_pobre: b?.sueno_pobre ?? 3,
                  fatiga: b?.fatiga ?? 3,
                  dolor_muscular: b?.dolor_muscular ?? 3,
                  estres: b?.estres ?? 3,
                  [clave]: siguiente,
                }));
                setTocado(true);
              }}
            />
          </div>
        ))}
        {borrador === null && (
          <p className="text-[12px] text-text-secondary">
            Toca una pill para registrar. Promedio 3 es neutral.
          </p>
        )}
      </div>
    </BentoCard>
  );
}
