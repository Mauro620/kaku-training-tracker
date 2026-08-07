"use client";

import Link from "next/link";
import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { BentoCard } from "@/components/ui/bento-card";
import {
  useCerrarCiclo,
  useCiclos,
  useCrearCiclo,
  type Ciclo,
} from "@/lib/api/hooks";

type Props = { onCrearClick?: () => void };

/**
 * Pantalla de ciclos (Fase 4 R3a, ROADMAP §4).
 * Lista los ciclos del usuario, con un form destacado para crear uno
 * nuevo. Cada ciclo es un link al detalle (`/entreno/ciclos/[id]`) donde
 * se cargan semanas, composicion y cumplimiento.
 */
export function CiclosScreen(_: Props = {}) {
  const ciclos = useCiclos();
  const crear = useCrearCiclo();
  const cerrar = useCerrarCiclo();

  const [numero, setNumero] = useState(1);
  const [objetivo, setObjetivo] = useState("");
  const [fechaInicio, setFechaInicio] = useState(fechaHoy());
  const [semanas, setSemanas] = useState(4);

  return (
    <div className="flex flex-col gap-4 pb-32">
      <BentoCard>
        <header className="mb-4">
          <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
            Tus ciclos
          </p>
          <p className="mt-1 text-[13px] text-text-secondary">
            Planifica bloques de entrenamiento con objetivo, duracion y
            composicion semanal.
          </p>
        </header>

        {ciclos.isLoading ? (
          <div className="h-20" />
        ) : !ciclos.data || ciclos.data.length === 0 ? (
          <p className="text-[14px] text-text-secondary">Aun no hay ciclos.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {ciclos.data.map((c) => (
              <CicloFila
                key={c.id}
                ciclo={c}
                onCerrar={() => cerrar.mutate({ id: c.id })}
                cerrando={cerrar.isPending && cerrar.variables?.id === c.id}
              />
            ))}
          </div>
        )}
      </BentoCard>

      <BentoCard>
        <header className="mb-4">
          <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
            Nuevo ciclo
          </p>
        </header>

        <form
          onSubmit={async (e) => {
            e.preventDefault();
            await crear.mutateAsync({
              numero,
              objetivo,
              fecha_inicio: fechaInicio,
              semanas,
            });
            setObjetivo("");
          }}
          className="flex flex-col gap-4"
        >
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-widest text-text-secondary">
              Numero
            </span>
            <input
              type="number"
              min={1}
              value={numero}
              onChange={(e) =>
                setNumero(e.target.value === "" ? 0 : Number(e.target.value))
              }
              className="bg-surface-secondary rounded-pill px-4 py-2 text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-widest text-text-secondary">
              Objetivo
            </span>
            <input
              type="text"
              required
              minLength={1}
              value={objetivo}
              onChange={(e) => setObjetivo(e.target.value)}
              placeholder="ej. Pretemporada, fuerza maxima, descarga"
              className="bg-surface-secondary rounded-pill px-4 py-2 text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
            />
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1">
              <span className="text-[11px] uppercase tracking-widest text-text-secondary">
                Inicio
              </span>
              <input
                type="date"
                value={fechaInicio}
                onChange={(e) => setFechaInicio(e.target.value)}
                className="bg-surface-secondary rounded-pill px-4 py-2 text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] uppercase tracking-widest text-text-secondary">
                Semanas
              </span>
              <input
                type="number"
                min={1}
                value={semanas}
                onChange={(e) =>
                  setSemanas(e.target.value === "" ? 0 : Number(e.target.value))
                }
                className="bg-surface-secondary rounded-pill px-4 py-2 text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
              />
            </label>
          </div>

          <button
            type="submit"
            disabled={!objetivo || crear.isPending}
            className="mt-2 w-full bg-text-primary text-canvas rounded-pill py-3 text-[14px] font-semibold disabled:opacity-50"
          >
            {crear.isPending ? "Creando..." : "Crear ciclo"}
          </button>
        </form>
      </BentoCard>
    </div>
  );
}

function CicloFila({
  ciclo,
  onCerrar,
  cerrando,
}: {
  ciclo: Ciclo;
  onCerrar: () => void;
  cerrando: boolean;
}) {
  const cerrado = ciclo.estado === "cerrado";
  return (
    <div className="flex items-center justify-between rounded-bento border border-border-subtle bg-surface-secondary px-4 py-3">
      <Link
        href={`/entreno/ciclos/${ciclo.id}`}
        className="flex flex-1 items-center justify-between"
      >
        <div>
          <p className="text-[16px] font-semibold text-text-primary">
            #{ciclo.numero} · {ciclo.objetivo}
          </p>
          <p className="text-[11px] uppercase tracking-widest text-text-secondary">
            {ciclo.semanas} semana{ciclo.semanas === 1 ? "" : "s"} ·{" "}
            {ciclo.estado}
          </p>
        </div>
        <ChevronRight size={18} className="text-text-secondary" />
      </Link>
      {!cerrado && (
        <button
          type="button"
          onClick={onCerrar}
          disabled={cerrando}
          className="ml-3 rounded-pill bg-surface-primary px-4 py-1.5 text-[12px] font-medium text-text-primary disabled:opacity-50"
        >
          {cerrando ? "Cerrando..." : "Cerrar"}
        </button>
      )}
    </div>
  );
}

function fechaHoy(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}
