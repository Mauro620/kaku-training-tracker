"use client";

import { useMemo } from "react";

import { BentoCard } from "@/components/ui/bento-card";
import {
  useBienestarDeHoy,
  useHabitos,
  useHabitosDeHoy,
  useHidratacionDeHoy,
  useSuenoDeHoy,
} from "@/lib/api/hooks";

type Props = { fecha: string };

type Segmento = "sueno" | "bienestar" | "hidratacion" | "habitos";

const ETIQUETA: Record<Segmento, string> = {
  sueno: "Sueño",
  bienestar: "Bienestar",
  hidratacion: "Hidratación",
  habitos: "Hábitos",
};

type EstadoSegmento = "cargando" | "completo" | "pendiente";

/**
 * Cierre del dia (H1 de la revision de UI).
 *
 * Reemplaza la tarjeta "Estado del dia" que mostraba un placeholder
 * sobre la fase 8. Funciona desde el dia uno: 4 segmentos, uno por
 * captura, color por estado. El objetivo es empujar la conducta:
 * "Falta bienestar" es accionable, "3 de 4" es un contador, no un
 * puntaje.
 *
 * Reglas por segmento:
 *   - "pendiente": no hay fila todavia (404 en el get correspondiente).
 *   - "completo": hay fila. Para Habitos, ademas, tiene que estar
 *     marcado >= 1 de los activos: el chequeo fino requiere el
 *     catalogo, que se pide via useHabitos. Conservador: marcamos
 *     completo cuando hay >= 1 marcado y el catalogo ya cargo.
 *   - "cargando": la query esta en vuelo.
 *
 * Sin numero sin contexto: el "3 de 4" esta acompanado del texto
 * "Falta bienestar" abajo. Cualquiera de los dos por separado es
 * incompleto.
 */
export function CierreDelDiaCard({ fecha }: Props) {
  const sueno = useSuenoDeHoy(fecha);
  const bienestar = useBienestarDeHoy(fecha);
  const hidratacion = useHidratacionDeHoy(fecha);
  const habitosCatalogo = useHabitos();
  const habitosDeHoy = useHabitosDeHoy(fecha);

  const segmentos = useMemo<Record<Segmento, EstadoSegmento>>(() => {
    const habitosMarcados =
      habitosDeHoy.data?.filter((r) => r.valor).length ?? 0;
    const habitosActivos =
      habitosCatalogo.data?.filter((h) => h.activo).length ?? 0;

    let habitos: EstadoSegmento;
    if (habitosCatalogo.isLoading || habitosDeHoy.isLoading) {
      habitos = "cargando";
    } else if (habitosActivos > 0 && habitosMarcados >= habitosActivos) {
      habitos = "completo";
    } else if (habitosActivos === 0) {
      // Sin habitos configurados: no hay nada que cerrar, no marcamos
      // como pendiente. Mejor un punto neutro gris.
      habitos = "cargando";
    } else {
      habitos = "pendiente";
    }

    return {
      sueno: sueno.isLoading
        ? "cargando"
        : sueno.error
          ? "pendiente"
          : sueno.data
            ? "completo"
            : "pendiente",
      bienestar: bienestar.isLoading
        ? "cargando"
        : bienestar.error
          ? "pendiente"
          : bienestar.data
            ? "completo"
            : "pendiente",
      hidratacion: hidratacion.isLoading
        ? "cargando"
        : hidratacion.error
          ? "pendiente"
          : hidratacion.data
            ? "completo"
            : "pendiente",
      habitos,
    };
  }, [
    sueno.isLoading,
    sueno.error,
    sueno.data,
    bienestar.isLoading,
    bienestar.error,
    bienestar.data,
    hidratacion.isLoading,
    hidratacion.error,
    hidratacion.data,
    habitosCatalogo.isLoading,
    habitosCatalogo.data,
    habitosDeHoy.isLoading,
    habitosDeHoy.data,
  ]);

  const completos = (Object.values(segmentos) as EstadoSegmento[]).filter(
    (s) => s === "completo",
  ).length;
  const total = Object.keys(segmentos).length;

  const pendientes = (Object.entries(segmentos) as [Segmento, EstadoSegmento][])
    .filter(([, s]) => s === "pendiente")
    .map(([k]) => ETIQUETA[k]);

  return (
    <BentoCard>
      <header className="flex items-baseline justify-between mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Cierre del dia
        </p>
        <p className="text-[24px] font-bold leading-none tabular text-text-primary">
          {completos}
          <span className="ml-1 text-sm font-medium text-text-secondary">
            de {total}
          </span>
        </p>
      </header>
      <div className="flex gap-2" role="list">
        {(Object.entries(segmentos) as [Segmento, EstadoSegmento][]).map(
          ([clave, estado]) => (
            <SegmentoDot key={clave} segmento={clave} estado={estado} />
          ),
        )}
      </div>
      {pendientes.length > 0 && (
        <p className="mt-4 text-[13px] text-text-secondary">
          {pendientes.length === 1
            ? `Falta ${(pendientes[0] ?? "").toLowerCase()}`
            : `Faltan ${pendientes.map((p) => p.toLowerCase()).join(" y ")}`}
        </p>
      )}
    </BentoCard>
  );
}

function SegmentoDot({
  segmento,
  estado,
}: {
  segmento: Segmento;
  estado: EstadoSegmento;
}) {
  const clasesBarra =
    estado === "completo"
      ? "bg-state-positive"
      : estado === "cargando"
        ? "bg-border-subtle"
        : "bg-transparent border border-border-subtle";
  const etiqueta =
    estado === "cargando"
      ? "Cargando"
      : estado === "completo"
        ? "Listo"
        : "Pendiente";
  return (
    <div
      role="listitem"
      className="flex-1 flex flex-col gap-2 rounded-lg bg-surface-secondary px-3 py-3"
      aria-label={`${ETIQUETA[segmento]}: ${etiqueta}`}
    >
      <span className="h-1.5 w-full rounded-full bg-canvas overflow-hidden">
        <span className={`block h-full ${clasesBarra}`} />
      </span>
      <span className="text-[11px] tracking-widest uppercase text-text-secondary">
        {ETIQUETA[segmento]}
      </span>
    </div>
  );
}
