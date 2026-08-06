"use client";

import { useState } from "react";
import { Minus, Plus, Trash2 } from "lucide-react";
import { BentoCard } from "@/components/ui/bento-card";
import {
  useCrearSesion,
  useEjercicios,
  useTiposSesion,
  type Ejercicio,
  type TipoSesion,
} from "@/lib/api/hooks";

type Props = { fecha: string };

type SerieBorrador = {
  // Identificador local para key de React. No se manda al backend.
  localId: number;
  ejercicio_id: number | null;
  series: number;
  reps: number;
  peso_kg: number | null;
  rpe: number | null;
  dolor_lumbar: boolean;
};

const SERIE_VACIA: Omit<SerieBorrador, "localId"> = {
  ejercicio_id: null,
  series: 4,
  reps: 8,
  peso_kg: null,
  rpe: null,
  dolor_lumbar: false,
};

function uid(): number {
  return Math.floor(Math.random() * 1e9);
}

/**
 * Form de sesion (Fase 4 R1, ROADMAP §4).
 * Un unico paso visible: tipo, duracion, RPE, nota, y N series editables.
 * El cliente genera `id` y `idempotency_key` (uuid v4) para que el backend
 * pueda detectar reintentos idempotentes (Fase 5 offline-first).
 */
export function SesionForm({ fecha }: Props) {
  const tipos = useTiposSesion();
  const ejercicios = useEjercicios();
  const crear = useCrearSesion(fecha);

  const [tipoSesionId, setTipoSesionId] = useState<number | null>(null);
  const [duracionMin, setDuracionMin] = useState<number>(60);
  const [rpe, setRpe] = useState<number>(7);
  const [nota, setNota] = useState("");
  const [series, setSeries] = useState<SerieBorrador[]>([]);

  const cargaEstimada = rpe * duracionMin;

  function agregarSerie() {
    setSeries((s) => [...s, { localId: uid(), ...SERIE_VACIA }]);
  }

  function eliminarSerie(localId: number) {
    setSeries((s) => s.filter((x) => x.localId !== localId));
  }

  function actualizarSerie(localId: number, cambio: Partial<SerieBorrador>) {
    setSeries((s) => s.map((x) => (x.localId === localId ? { ...x, ...cambio } : x)));
  }

  const puedeGuardar =
    tipoSesionId !== null &&
    series.length > 0 &&
    series.every((s) => s.ejercicio_id !== null);

  return (
    <BentoCard>
      <header className="mb-4 flex items-center justify-between">
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Nueva sesion
        </p>
        {series.length > 0 && (
          <span className="text-[11px] text-text-secondary">
            {series.length} serie{series.length === 1 ? "" : "s"}
          </span>
        )}
      </header>

      {/* Tipo de sesion */}
      <p className="mb-2 text-[13px] text-text-secondary">Tipo</p>
      <div className="flex flex-wrap gap-2">
        {tipos.data?.map((t: TipoSesion) => (
          <BotonTipo
            key={t.id}
            tipo={t}
            activo={tipoSesionId === t.id}
            onClick={() => setTipoSesionId(t.id)}
          />
        ))}
      </div>

      {/* Duracion, RPE, nota */}
      <div className="mt-5 grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-[11px] uppercase tracking-widest text-text-secondary">
            Duracion
          </span>
          <div className="flex items-center bg-surface-secondary rounded-pill">
            <button
              type="button"
              onClick={() => setDuracionMin((d) => Math.max(1, d - 5))}
              className="p-2 text-text-secondary"
              aria-label="Restar 5 minutos"
            >
              <Minus size={16} />
            </button>
            <input
              type="number"
              min={1}
              value={duracionMin}
              onChange={(e) => setDuracionMin(Math.max(1, Number(e.target.value)))}
              className="w-full bg-transparent text-center text-[16px] font-bold tabular text-text-primary outline-none"
            />
            <span className="px-2 text-[11px] text-text-secondary">min</span>
            <button
              type="button"
              onClick={() => setDuracionMin((d) => d + 5)}
              className="p-2 text-text-secondary"
              aria-label="Sumar 5 minutos"
            >
              <Plus size={16} />
            </button>
          </div>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-[11px] uppercase tracking-widest text-text-secondary">RPE</span>
          <input
            type="number"
            min={1}
            max={10}
            value={rpe}
            onChange={(e) => setRpe(Math.max(1, Math.min(10, Number(e.target.value))))}
            className="bg-surface-secondary rounded-pill px-4 py-2 text-center text-[16px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
      </div>

      <p className="mt-3 text-center text-[36px] font-bold leading-none tabular text-text-primary">
        {cargaEstimada}
        <span className="ml-2 text-base font-medium text-text-secondary">carga sRPE</span>
      </p>

      <label className="mt-4 flex flex-col gap-1">
        <span className="text-[11px] uppercase tracking-widest text-text-secondary">Nota</span>
        <input
          type="text"
          value={nota}
          onChange={(e) => setNota(e.target.value)}
          placeholder="opcional"
          className="bg-surface-secondary rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
        />
      </label>

      {/* Series */}
      <div className="mt-6 flex items-center justify-between">
        <p className="text-[13px] text-text-secondary">Series</p>
        <button
          type="button"
          onClick={agregarSerie}
          className="flex items-center gap-1 rounded-pill bg-surface-secondary px-4 py-1.5 text-[13px] font-medium text-text-primary"
        >
          <Plus size={14} /> Agregar
        </button>
      </div>

      <div className="mt-3 flex flex-col gap-2">
        {series.map((s, idx) => (
          <SerieBorradorCard
            key={s.localId}
            serie={s}
            orden={idx + 1}
            ejercicios={ejercicios.data ?? []}
            onChange={(c) => actualizarSerie(s.localId, c)}
            onEliminar={() => eliminarSerie(s.localId)}
          />
        ))}
      </div>

      <button
        type="button"
        disabled={!puedeGuardar || crear.isPending}
        onClick={async () => {
          if (!tipoSesionId) return;
          await crear.mutateAsync({
            // crypto.randomUUID requiere contexto seguro (https o localhost).
            // El dev server corre en localhost asi que funciona.
            id: crypto.randomUUID(),
            idempotency_key: crypto.randomUUID(),
            tipo_sesion_id: tipoSesionId,
            duracion_min: duracionMin,
            rpe,
            nota: nota || null,
            series: series.map((s, idx) => ({
              ejercicio_id: s.ejercicio_id!,
              orden: idx + 1,
              series: s.series,
              reps: s.reps,
              peso_kg: s.peso_kg,
              rpe: s.rpe,
              dolor_lumbar: s.dolor_lumbar,
            })),
          });
          // Reset del form
          setSeries([]);
          setNota("");
        }}
        className="mt-6 w-full bg-text-primary text-canvas rounded-pill py-3 text-[14px] font-semibold disabled:opacity-50"
      >
        {crear.isPending ? "Guardando..." : "Guardar sesion"}
      </button>
    </BentoCard>
  );
}

// ---------- Sub-componentes ----------

function BotonTipo({
  tipo,
  activo,
  onClick,
}: {
  tipo: TipoSesion;
  activo: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={activo}
      className={`min-h-[40px] px-4 rounded-pill text-[13px] ${
        activo
          ? "bg-text-primary text-canvas"
          : "bg-surface-secondary text-text-secondary"
      }`}
    >
      {tipo.nombre}
    </button>
  );
}

function SerieBorradorCard({
  serie,
  orden,
  ejercicios,
  onChange,
  onEliminar,
}: {
  serie: SerieBorrador;
  orden: number;
  ejercicios: Ejercicio[];
  onChange: (c: Partial<SerieBorrador>) => void;
  onEliminar: () => void;
}) {
  return (
    <div className="rounded-bento border border-border-subtle bg-surface-secondary p-3">
      <div className="flex items-center justify-between">
        <p className="text-[11px] uppercase tracking-widest text-text-secondary">
          Serie {orden}
        </p>
        <button
          type="button"
          onClick={onEliminar}
          aria-label="Eliminar serie"
          className="p-1 text-text-secondary"
        >
          <Trash2 size={14} />
        </button>
      </div>

      <select
        value={serie.ejercicio_id ?? ""}
        onChange={(e) =>
          onChange({ ejercicio_id: e.target.value ? Number(e.target.value) : null })
        }
        className="mt-2 w-full bg-canvas rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
      >
        <option value="">Ejercicio…</option>
        {ejercicios.map((e) => (
          <option key={e.id} value={e.id}>
            {e.nombre}
          </option>
        ))}
      </select>

      <div className="mt-2 grid grid-cols-4 gap-2">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">Sets</span>
          <input
            type="number"
            min={1}
            value={serie.series}
            onChange={(e) => onChange({ series: Math.max(1, Number(e.target.value)) })}
            className="bg-canvas rounded-pill px-3 py-1.5 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">Reps</span>
          <input
            type="number"
            min={1}
            value={serie.reps}
            onChange={(e) => onChange({ reps: Math.max(1, Number(e.target.value)) })}
            className="bg-canvas rounded-pill px-3 py-1.5 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">Kg</span>
          <input
            type="number"
            min={0}
            step={0.5}
            value={serie.peso_kg ?? ""}
            onChange={(e) =>
              onChange({ peso_kg: e.target.value === "" ? null : Number(e.target.value) })
            }
            className="bg-canvas rounded-pill px-3 py-1.5 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">RPE</span>
          <input
            type="number"
            min={1}
            max={10}
            value={serie.rpe ?? ""}
            onChange={(e) =>
              onChange({ rpe: e.target.value === "" ? null : Number(e.target.value) })
            }
            className="bg-canvas rounded-pill px-3 py-1.5 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
      </div>
    </div>
  );
}
