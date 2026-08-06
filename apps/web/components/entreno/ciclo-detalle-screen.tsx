"use client";

import { useState } from "react";
import { Minus, Plus } from "lucide-react";
import { BentoCard } from "@/components/ui/bento-card";
import {
  useCiclo,
  useComposicion,
  useCrearSemana,
  useCumplimiento,
  useReemplazarComposicion,
  useSemanas,
  useTiposSesion,
  type CicloSemana,
  type ComposicionItem,
} from "@/lib/api/hooks";

type Props = { cicloId: number };

/**
 * Pantalla de detalle de un ciclo (Fase 4 R3a).
 * Tres bloques: header del ciclo, lista de semanas con su composicion
 * objetivo y cumplimiento real, y un form para declarar la composicion
 * de la semana que elijas.
 *
 * Por defecto la semana activa es la que corresponde a la fecha de
 * registro (con corte a las 4am).
 */
export function CicloDetalleScreen({ cicloId }: Props) {
  const ciclo = useCiclo(cicloId);
  const semanas = useSemanas(cicloId);
  const fechaHoy = useFechaDeRegistro();

  const numeroPorFecha = ciclo.data
    ? calcularNumeroSemana(ciclo.data.fecha_inicio, fechaHoy, ciclo.data.semanas)
    : 1;
  const [semanaElegida, setSemanaElegida] = useState<number | null>(null);

  const semanasData = semanas.data ?? [];
  const semanaActiva =
    semanasData.find((s) => s.numero === (semanaElegida ?? numeroPorFecha)) ??
    semanasData[0] ??
    null;

  return (
    <div className="flex flex-col gap-4 pb-32">
      <BentoCard>
        <header>
          <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
            Ciclo #{ciclo.data?.numero ?? "..."}
          </p>
          <h2 className="mt-1 text-[24px] font-bold text-text-primary">
            {ciclo.data?.objetivo ?? "..."}
          </h2>
          <p className="mt-1 text-[13px] text-text-secondary">
            {ciclo.data
              ? `${ciclo.data.semanas} semanas · ${ciclo.data.estado}`
              : ""}
            {" · "}
            {ciclo.data?.fecha_inicio}
            {" → "}
            {ciclo.data?.fecha_fin_prevista}
          </p>
        </header>
      </BentoCard>

      <BentoCard>
        <header className="mb-4">
          <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
            Semanas
          </p>
        </header>

        {semanas.isLoading ? (
          <div className="h-20" />
        ) : semanasData.length === 0 ? (
          <CrearSemanaForm cicloId={cicloId} />
        ) : (
          <div className="flex flex-col gap-4">
            <SelectorSemana
              semanas={semanasData}
              activa={semanaActiva?.numero ?? 1}
              onElegir={setSemanaElegida}
            />
            {semanaActiva && (
              <SemanaBloque key={semanaActiva.id} semana={semanaActiva} />
            )}
            <CrearSemanaForm cicloId={cicloId} />
          </div>
        )}
      </BentoCard>
    </div>
  );
}

function SelectorSemana({
  semanas,
  activa,
  onElegir,
}: {
  semanas: CicloSemana[];
  activa: number;
  onElegir: (n: number) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {semanas.map((s) => (
        <button
          key={s.id}
          type="button"
          onClick={() => onElegir(s.numero)}
          aria-pressed={s.numero === activa}
          className={`min-h-[40px] px-4 rounded-pill text-[13px] ${
            s.numero === activa
              ? "bg-text-primary text-canvas"
              : "bg-surface-secondary text-text-secondary"
          }`}
        >
          S{s.numero} · {s.fase}
        </button>
      ))}
    </div>
  );
}

function SemanaBloque({ semana }: { semana: CicloSemana }) {
  const composicion = useComposicion(semana.id);
  const cumplimiento = useCumplimiento(semana.id);

  return (
    <div className="flex flex-col gap-4 rounded-bento border border-border-subtle bg-surface-secondary p-4">
      <div>
        <p className="text-[16px] font-semibold text-text-primary">
          Semana {semana.numero} · {semana.fase}
        </p>
        <p className="text-[11px] uppercase tracking-widest text-text-secondary">
          {semana.rpe_objetivo_min !== null && semana.rpe_objetivo_max !== null
            ? `RPE ${semana.rpe_objetivo_min}-${semana.rpe_objetivo_max}`
            : "RPE libre"}
          {semana.volumen_pct !== 100 && ` · volumen ${semana.volumen_pct}%`}
        </p>
      </div>

      <CumplimientoBloque
        items={cumplimiento.data ?? []}
        cargando={cumplimiento.isLoading}
      />

      <ComposicionForm semanaId={semana.id} actuales={composicion.data ?? []} />
    </div>
  );
}

function CumplimientoBloque({
  items,
  cargando,
}: {
  items: import("@/lib/api/hooks").CumplimientoItem[];
  cargando: boolean;
}) {
  if (cargando) {
    return <div className="h-12" />;
  }
  if (items.length === 0) {
    return (
      <p className="text-[13px] text-text-secondary">
        Aun no hay composicion declarada para esta semana.
      </p>
    );
  }
  return (
    <div>
      <p className="mb-2 text-[11px] uppercase tracking-widest text-text-secondary">
        Cumplimiento
      </p>
      <ul className="flex flex-col gap-1">
        {items.map((it) => (
          <li
            key={it.tipo_sesion_id}
            className="flex items-center justify-between text-[13px]"
          >
            <span className="text-text-primary">{it.tipo_sesion_nombre}</span>
            <span
              className={`tabular ${
                it.cumplido ? "text-state-positive" : "text-text-secondary"
              }`}
            >
              {it.hecho} / {it.objetivo}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ComposicionForm({
  semanaId,
  actuales,
}: {
  semanaId: number;
  actuales: ComposicionItem[];
}) {
  const tipos = useTiposSesion();
  const reemplazar = useReemplazarComposicion(semanaId);

  const [items, setItems] = useState<ComposicionItem[]>(actuales);

  // Sincroniza cuando el server trae composicion y el form esta vacio.
  // OJO: setState durante render es un anti-patron, pero aca es seguro
  // porque la condicion es estable (actuales.length > 0 && items.length === 0)
  // y no produce renders en loop. Si los items del server vienen en otro
  // orden la proxima vez, el form los va a tomar igual.
  if (
    actuales.length > 0 &&
    items.length === 0 &&
    !reemplazar.isPending
  ) {
    setItems(actuales);
  }

  function agregar() {
    const primero = tipos.data?.[0];
    if (!primero) return;
    setItems((arr) => [
      ...arr,
      { tipo_sesion_id: primero.id, cantidad_objetivo: 1 },
    ]);
  }

  function eliminar(idx: number) {
    setItems((arr) => arr.filter((_, i) => i !== idx));
  }

  function actualizar(idx: number, cambio: Partial<ComposicionItem>) {
    setItems((arr) =>
      arr.map((it, i) => (i === idx ? { ...it, ...cambio } : it)),
    );
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <p className="text-[11px] uppercase tracking-widest text-text-secondary">
          Composicion objetivo
        </p>
        <button
          type="button"
          onClick={agregar}
          disabled={!tipos.data || tipos.data.length === 0}
          className="flex items-center gap-1 rounded-pill bg-canvas px-4 py-1.5 text-[13px] font-medium text-text-primary disabled:opacity-50"
        >
          <Plus size={14} /> Agregar
        </button>
      </div>

      <div className="flex flex-col gap-2">
        {items.map((it, idx) => (
          <div
            key={`${it.tipo_sesion_id}-${idx}`}
            className="flex items-center gap-2"
          >
            <select
              value={it.tipo_sesion_id}
              onChange={(e) =>
                actualizar(idx, { tipo_sesion_id: Number(e.target.value) })
              }
              className="flex-1 bg-canvas rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
            >
              {tipos.data?.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nombre}
                </option>
              ))}
            </select>
            <input
              type="number"
              min={1}
              value={it.cantidad_objetivo}
              onChange={(e) =>
                actualizar(idx, {
                  cantidad_objetivo: Math.max(1, Number(e.target.value)),
                })
              }
              className="w-16 bg-canvas rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
            />
            <button
              type="button"
              onClick={() => eliminar(idx)}
              aria-label="Eliminar"
              className="p-2 text-text-secondary"
            >
              <Minus size={14} />
            </button>
          </div>
        ))}
      </div>

      <button
        type="button"
        disabled={items.length === 0 || reemplazar.isPending}
        onClick={async () => {
          await reemplazar.mutateAsync(items);
        }}
        className="mt-4 w-full bg-text-primary text-canvas rounded-pill py-3 text-[14px] font-semibold disabled:opacity-50"
      >
        {reemplazar.isPending ? "Guardando..." : "Guardar composicion"}
      </button>
    </div>
  );
}

function CrearSemanaForm({ cicloId }: { cicloId: number }) {
  const crear = useCrearSemana(cicloId);
  const [numero, setNumero] = useState(1);
  const [fase, setFase] = useState<"readaptacion" | "carga" | "descarga">("carga");
  const [rpeMin, setRpeMin] = useState<number | null>(null);
  const [rpeMax, setRpeMax] = useState<number | null>(null);
  const [volumen, setVolumen] = useState(100);

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        await crear.mutateAsync({
          numero,
          fase,
          rpe_objetivo_min: rpeMin,
          rpe_objetivo_max: rpeMax,
          volumen_pct: volumen,
        });
      }}
      className="flex flex-col gap-3"
    >
      <p className="text-[11px] uppercase tracking-widest text-text-secondary">
        Nueva semana
      </p>
      <div className="grid grid-cols-2 gap-2">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            Numero
          </span>
          <input
            type="number"
            min={1}
            value={numero}
            onChange={(e) => setNumero(Math.max(1, Number(e.target.value)))}
            className="bg-canvas rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            Fase
          </span>
          <select
            value={fase}
            onChange={(e) =>
              setFase(e.target.value as "readaptacion" | "carga" | "descarga")
            }
            className="bg-canvas rounded-pill px-3 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          >
            <option value="readaptacion">Readaptacion</option>
            <option value="carga">Carga</option>
            <option value="descarga">Descarga</option>
          </select>
        </label>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            RPE min
          </span>
          <input
            type="number"
            min={1}
            max={10}
            value={rpeMin ?? ""}
            onChange={(e) =>
              setRpeMin(e.target.value === "" ? null : Number(e.target.value))
            }
            className="bg-canvas rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            RPE max
          </span>
          <input
            type="number"
            min={1}
            max={10}
            value={rpeMax ?? ""}
            onChange={(e) =>
              setRpeMax(e.target.value === "" ? null : Number(e.target.value))
            }
            className="bg-canvas rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-widest text-text-secondary">
            Volumen %
          </span>
          <input
            type="number"
            min={1}
            value={volumen}
            onChange={(e) => setVolumen(Math.max(1, Number(e.target.value)))}
            className="bg-canvas rounded-pill px-3 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>
      </div>
      <button
        type="submit"
        disabled={crear.isPending}
        className="rounded-pill bg-canvas py-2 text-[14px] font-semibold text-text-primary disabled:opacity-50"
      >
        {crear.isPending ? "Creando..." : "Crear semana"}
      </button>
    </form>
  );
}

// ---------- Helpers ----------

function useFechaDeRegistro(): string {
  // Mismo corte que lib/fecha.ts pero copiado para evitar el ciclo de
  // hooks (este archivo ya importa sus tipos de ahi).
  const d = new Date();
  if (d.getHours() < 4) d.setDate(d.getDate() - 1);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function calcularNumeroSemana(
  fechaInicio: string,
  fechaActual: string,
  totalSemanas: number,
): number {
  const inicio = new Date(fechaInicio).getTime();
  const actual = new Date(fechaActual).getTime();
  const diffDias = Math.floor((actual - inicio) / (1000 * 60 * 60 * 24));
  if (diffDias < 0) return 1;
  const n = Math.floor(diffDias / 7) + 1;
  return Math.min(n, totalSemanas);
}
