"use client";

import { useMemo } from "react";

import { BentoCard } from "@/components/ui/bento-card";
import {
  useCierreSemana,
  type CierreDia,
} from "@/lib/api/hooks";

type Props = { desde: string; hasta: string };

const ETIQUETAS_DIM = [
  "Sueno >= objetivo",
  "Sesion registrada",
  "Hidratacion en objetivo",
  "Habitos completos",
  "Bienestar registrado",
] as const;

const ETIQUETAS_DIA = ["L", "M", "X", "J", "V", "S", "D"] as const;

type EstadoCelda = "cumple" | "no" | "sin_dato" | "hoy" | "futuro";

const COLORES: Record<EstadoCelda, string> = {
  cumple: "bg-state-positive",
  no: "bg-state-danger",
  sin_dato: "bg-border-subtle",
  hoy: "bg-text-primary",
  futuro: "bg-transparent",
};

export function CierreSemanalCard({ desde, hasta }: Props) {
  const { data, isLoading } = useCierreSemana(desde, hasta);

  const diasOrdenados = useMemo(() => {
    if (!data) return [];
    return [...data.dias].sort((a, b) => a.fecha.localeCompare(b.fecha));
  }, [data]);

  const hoy = hoyISO();

  const estadosPorDia: ("cumple" | "no" | "sin_dato")[][] = useMemo(() => {
    return diasOrdenados.map((d) => [
      estadoSueno(d),
      estadoSesion(d),
      estadoHidratacion(d),
      estadoHabitos(d),
      estadoBienestar(d),
    ]);
  }, [diasOrdenados]);

  const conteosPorFila = useMemo(() => {
    return ETIQUETAS_DIM.map((_, filaIdx) => {
      let cumple = 0;
      let total = 0;
      for (const estados of estadosPorDia) {
        const e = estados[filaIdx];
        if (e === "cumple") cumple += 1;
        if (e !== "sin_dato") total += 1;
      }
      return { cumple, total };
    });
  }, [estadosPorDia]);

  return (
    <BentoCard>
      <header className="flex items-center justify-between mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Esta semana
        </p>
      </header>

      {isLoading ? (
        <div className="h-32" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr>
                <th className="w-[40%] py-2 text-[11px] tracking-widest uppercase text-text-secondary font-normal">
                  Dimension
                </th>
                {ETIQUETAS_DIA.map((d) => (
                  <th
                    key={d}
                    className="w-[8%] py-2 text-[11px] tracking-widest uppercase text-text-secondary font-normal text-center"
                  >
                    {d}
                  </th>
                ))}
                <th className="w-[12%] py-2 text-[11px] tracking-widest uppercase text-text-secondary font-normal text-right">
                  Conteo
                </th>
              </tr>
            </thead>
            <tbody>
              {ETIQUETAS_DIM.map((etiqueta, filaIdx) => {
                const conteo = conteosPorFila[filaIdx] ?? { cumple: 0, total: 0 };
                return (
                  <tr key={etiqueta}>
                    <td className="py-2 text-[12px] text-text-secondary">
                      {etiqueta}
                    </td>
                    {diasOrdenados.map((d, colIdx) => {
                      const cell = estadosPorDia[colIdx]?.[filaIdx];
                      const estado: EstadoCelda = cell
                        ? clasificarCelda(cell, d.fecha, hoy)
                        : "sin_dato";
                      return (
                        <td key={d.fecha} className="py-2 text-center">
                          <div
                            className="mx-auto h-3 w-3 rounded-full"
                            data-color={estado}
                            title={`${etiqueta} ${d.fecha}: ${estado}`}
                            aria-label={`${etiqueta} ${d.fecha}: ${estado}`}
                          >
                            <span
                              className={`block h-full w-full rounded-full ${COLORES[estado]}`}
                            />
                          </div>
                        </td>
                      );
                    })}
                    <td className="py-2 text-right text-[12px] tabular text-text-primary">
                      {conteo.cumple}/{conteo.total}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </BentoCard>
  );
}

function estadoSueno(d: CierreDia): "cumple" | "no" | "sin_dato" {
  if (d.sueno.horas === null) return "sin_dato";
  const h = Number(d.sueno.horas);
  const objetivo = Number(d.sueno.objetivo_h);
  return h >= objetivo ? "cumple" : "no";
}

function estadoSesion(d: CierreDia): "cumple" | "no" {
  return d.sesion.registrada ? "cumple" : "no";
}

function estadoHidratacion(d: CierreDia): "cumple" | "no" | "sin_dato" {
  if (d.hidratacion.ml_totales === null) return "sin_dato";
  return d.hidratacion.ml_totales >= d.hidratacion.objetivo_ml
    ? "cumple"
    : "no";
}

function estadoHabitos(d: CierreDia): "cumple" | "no" | "sin_dato" {
  if (d.habitos.activos === 0) return "sin_dato";
  if (d.habitos.marcados === 0) return "sin_dato";
  return d.habitos.marcados >= d.habitos.activos ? "cumple" : "no";
}

function estadoBienestar(d: CierreDia): "cumple" | "no" {
  return d.bienestar.registrado ? "cumple" : "no";
}

function clasificarCelda(
  estado: "cumple" | "no" | "sin_dato",
  fecha: string,
  hoy: string,
): EstadoCelda {
  if (fecha > hoy) return "futuro";
  if (fecha === hoy) return "hoy";
  return estado;
}

function hoyISO(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}
