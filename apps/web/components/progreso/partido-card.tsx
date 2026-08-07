"use client";

import { useState } from "react";
import { BentoCard } from "@/components/ui/bento-card";
import {
  usePartidos,
  useRegistrarPartido,
  useSesionesDeFecha,
  useTiposSesion,
} from "@/lib/api/hooks";

export function PartidoCard({ fecha }: { fecha: string }) {
  const tiposSesion = useTiposSesion();
  const sesiones = useSesionesDeFecha(fecha);
  const partidos = usePartidos();
  const registrar = useRegistrarPartido();

  const [sesionId, setSesionId] = useState<string | null>(null);
  const [rival, setRival] = useState("");
  const [minutosJugados, setMinutosJugados] = useState(90);
  const [goles, setGoles] = useState(0);
  const [asistencias, setAsistencias] = useState(0);

  const tipoPartidoId = tiposSesion.data?.find((t) => t.codigo === "partido")?.id;
  const idsConFicha = new Set(partidos.data?.map((p) => p.sesion_id));
  const candidatas =
    sesiones.data?.filter(
      (s) => s.tipo_sesion_id === tipoPartidoId && !idsConFicha.has(s.id),
    ) ?? [];

  if (tipoPartidoId === undefined) {
    return null;
  }

  return (
    <BentoCard>
      <header className="mb-4">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Ficha de partido
        </p>
      </header>

      {candidatas.length === 0 ? (
        <p className="text-[13px] text-text-secondary">
          No hay sesiones de tipo partido hoy sin ficha completar. Crea primero
          la sesion en Entreno.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-[10px] uppercase tracking-widest text-text-secondary">
              Sesion
            </span>
            <select
              value={sesionId ?? candidatas[0]?.id ?? ""}
              onChange={(e) => setSesionId(e.target.value)}
              className="bg-surface-secondary rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
            >
              {candidatas.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.fecha} · {s.duracion_min} min
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-[10px] uppercase tracking-widest text-text-secondary">
              Rival (opcional)
            </span>
            <input
              type="text"
              value={rival}
              onChange={(e) => setRival(e.target.value)}
              className="bg-surface-secondary rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
            />
          </label>

          <div className="grid grid-cols-3 gap-2">
            <label className="flex flex-col gap-1">
              <span className="text-[10px] uppercase tracking-widest text-text-secondary">
                Minutos
              </span>
              <input
                type="number"
                min={0}
                value={minutosJugados}
                onChange={(e) => setMinutosJugados(Number(e.target.value))}
                className="bg-surface-secondary rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10px] uppercase tracking-widest text-text-secondary">
                Goles
              </span>
              <input
                type="number"
                min={0}
                value={goles}
                onChange={(e) => setGoles(Number(e.target.value))}
                className="bg-surface-secondary rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10px] uppercase tracking-widest text-text-secondary">
                Asistencias
              </span>
              <input
                type="number"
                min={0}
                value={asistencias}
                onChange={(e) => setAsistencias(Number(e.target.value))}
                className="bg-surface-secondary rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
              />
            </label>
          </div>

          <button
            type="button"
            disabled={registrar.isPending}
            onClick={async () => {
              const id = sesionId ?? candidatas[0]?.id;
              if (!id) return;
              await registrar.mutateAsync({
                sesion_id: id,
                rival: rival.trim() || null,
                minutos_jugados: minutosJugados,
                goles,
                asistencias,
              });
              setRival("");
              setMinutosJugados(90);
              setGoles(0);
              setAsistencias(0);
              setSesionId(null);
            }}
            className="mt-1 w-full bg-text-primary text-canvas rounded-pill py-3 text-[14px] font-semibold disabled:opacity-50"
          >
            {registrar.isPending ? "Guardando..." : "Guardar ficha"}
          </button>
        </div>
      )}

      {partidos.data && partidos.data.length > 0 && (
        <ul className="mt-4 flex flex-col gap-2 border-t border-border-subtle pt-4">
          {partidos.data.slice(0, 5).map((p) => (
            <li
              key={p.id}
              className="flex items-center justify-between rounded-bento bg-canvas px-4 py-2 text-[13px]"
            >
              <span className="text-text-primary">{p.rival ?? "Partido"}</span>
              <span className="tabular text-text-secondary">
                {p.goles}G · {p.asistencias}A · {p.minutos_jugados}&apos;
              </span>
            </li>
          ))}
        </ul>
      )}
    </BentoCard>
  );
}
