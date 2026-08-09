"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Minus, Plus } from "lucide-react";
import { BentoCard } from "@/components/ui/bento-card";
import {
  BLOQUE_VACIO,
  bloqueInvalido,
  BloqueBorradorCard,
  uid,
  type BloqueBorrador,
} from "@/components/entreno/bloque-editor";
import {
  useCrearSesion,
  useEjercicios,
  useSesionesDeFecha,
  useTiposSesion,
  type BloqueBorradorPayload,
  type SesionPlan,
  type TipoSesion,
} from "@/lib/api/hooks";

type Props = { fecha: string; planes: SesionPlan[] };

/**
 * Form de sesion (Fase 4, ROADMAP §4).
 * Un unico paso visible: tipo, duracion, RPE, nota, y N bloques editables
 * (editor compartido con SesionDetalle, ver bloque-editor.tsx).
 * El cliente genera `id` y `idempotency_key` (uuid v4) para que el backend
 * pueda detectar reintentos idempotentes (Fase 5 offline-first).
 */
export function SesionForm({ fecha, planes }: Props) {
  const tipos = useTiposSesion();
  const ejercicios = useEjercicios();
  const sesionesDeHoy = useSesionesDeFecha(fecha);
  const crear = useCrearSesion(fecha);

  const [expandido, setExpandido] = useState(false);
  const [tipoSesionId, setTipoSesionId] = useState<number | null>(null);
  const [tipoExpandido, setTipoExpandido] = useState(false);
  const [duracionMin, setDuracionMin] = useState<number>(60);
  const [rpe, setRpe] = useState<number>(7);
  const [nota, setNota] = useState("");
  const [bloques, setBloques] = useState<BloqueBorrador[]>([]);

  const tipoSeleccionado = tipos.data?.find((t) => t.id === tipoSesionId) ?? null;

  // Un plan ya cumplido (tiene una sesion real que lo referencia) no se
  // vuelve a ofrecer: linkearlo dos veces confundiria el delta.
  const idsPlanesCumplidos = new Set(
    (sesionesDeHoy.data ?? [])
      .map((s) => s.sesion_plan_id)
      .filter((id): id is number => id !== null),
  );
  const planesPendientes = planes.filter((p) => !idsPlanesCumplidos.has(p.id));
  const planVinculado =
    planesPendientes.find((p) => p.tipo_sesion_id === tipoSesionId) ?? null;

  const cargaEstimada = rpe * duracionMin;

  function agregarBloque() {
    setBloques((s) => [...s, { localId: uid(), ...BLOQUE_VACIO }]);
  }

  function duplicarBloque(localId: number) {
    setBloques((s) => {
      const original = s.find((b) => b.localId === localId);
      if (!original) return s;
      return [...s, { ...original, localId: uid() }];
    });
  }

  function eliminarBloque(localId: number) {
    setBloques((s) => s.filter((x) => x.localId !== localId));
  }

  function actualizarBloque(localId: number, cambio: Partial<BloqueBorrador>) {
    setBloques((s) => s.map((x) => (x.localId === localId ? { ...x, ...cambio } : x)));
  }

  function elegirTipo(id: number) {
    setTipoSesionId(id);
    setTipoExpandido(false);
  }

  const puedeGuardar = tipoSesionId !== null && !bloques.some(bloqueInvalido);

  return (
    <BentoCard>
      <button
        type="button"
        onClick={() => setExpandido((v) => !v)}
        className="flex w-full items-center justify-between"
      >
        <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
          Nueva sesion
        </p>
        <span className="flex items-center gap-2">
          {bloques.length > 0 && (
            <span className="text-[11px] text-text-secondary">
              {bloques.length} bloque{bloques.length === 1 ? "" : "s"}
            </span>
          )}
          {expandido ? (
            <ChevronUp size={16} className="text-text-secondary" />
          ) : (
            <ChevronDown size={16} className="text-text-secondary" />
          )}
        </span>
      </button>

      {expandido && (
        <div className="mt-4">

      {/* Plan de hoy: solo antes de elegir tipo, para no competir con el
          selector una vez que ya se sabe que se esta registrando. */}
      {!tipoSesionId && planesPendientes.length > 0 && (
        <div className="mb-4 flex flex-col gap-2">
          <p className="text-[11px] uppercase tracking-widest text-text-secondary">
            Plan de hoy
          </p>
          {planesPendientes.map((p) => {
            const nombre = tipos.data?.find((t) => t.id === p.tipo_sesion_id)?.nombre;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => elegirTipo(p.tipo_sesion_id)}
                className="flex items-center justify-between rounded-bento border border-border-subtle bg-surface-secondary px-4 py-2.5 text-left"
              >
                <span className="text-[14px] font-medium text-text-primary">
                  {nombre ?? "Sesion"}
                </span>
                <span className="text-[12px] text-text-secondary">
                  {[
                    p.rpe_objetivo && `RPE ${p.rpe_objetivo}`,
                    p.duracion_min_est && `${p.duracion_min_est} min`,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Tipo de sesion: colapsado muestra solo el elegido, se expande al tocar. */}
      <p className="mb-2 text-[13px] text-text-secondary">Tipo</p>
      {tipoExpandido ? (
        <div className="flex flex-wrap gap-2">
          {tipos.data?.map((t: TipoSesion) => (
            <BotonTipo
              key={t.id}
              tipo={t}
              activo={tipoSesionId === t.id}
              onClick={() => elegirTipo(t.id)}
            />
          ))}
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setTipoExpandido(true)}
          className="flex min-h-[40px] w-full items-center justify-between rounded-pill bg-surface-secondary px-4 text-[13px] text-text-primary"
        >
          {tipoSeleccionado?.nombre ?? "Elegir tipo…"}
          <ChevronDown size={16} className="text-text-secondary" />
        </button>
      )}
      {planVinculado && (
        <p className="mt-1.5 text-[11px] text-text-secondary">
          Vinculada al plan de hoy
          {planVinculado.rpe_objetivo ? ` · RPE objetivo ${planVinculado.rpe_objetivo}` : ""}
          {planVinculado.duracion_min_est ? ` · ${planVinculado.duracion_min_est} min` : ""}
        </p>
      )}

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
              // Sin clamp en el onChange: clamp en el onChange pisa el valor
              // mientras el usuario esta editando. El min/max del HTML ya
              // limita el browser, y el backend valida si pasa.
              onChange={(e) =>
                setDuracionMin(e.target.value === "" ? 0 : Number(e.target.value))
              }
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
            onChange={(e) => setRpe(Number(e.target.value))}
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

      {/* Bloques: cualquier tipo de sesion puede tenerlos. Que campos pide
          cada uno lo decide el tipo_medicion del ejercicio elegido. */}
      <div className="mt-6 flex items-center justify-between">
        <p className="text-[13px] text-text-secondary">Bloques</p>
        <button
          type="button"
          onClick={agregarBloque}
          className="flex items-center gap-1 rounded-pill bg-surface-secondary px-4 py-1.5 text-[13px] font-medium text-text-primary"
        >
          <Plus size={14} /> Agregar
        </button>
      </div>

      <div className="mt-3 flex flex-col gap-2">
        {bloques.map((b, idx) => (
          <BloqueBorradorCard
            key={b.localId}
            bloque={b}
            orden={idx + 1}
            ejercicios={ejercicios.data ?? []}
            onChange={(c) => actualizarBloque(b.localId, c)}
            onEliminar={() => eliminarBloque(b.localId)}
            onDuplicar={() => duplicarBloque(b.localId)}
          />
        ))}
      </div>

      <button
        type="button"
        disabled={!puedeGuardar || crear.isPending}
        onClick={async () => {
          if (!tipoSesionId) return;
          const bloquesPayload: BloqueBorradorPayload[] = bloques.map((b, idx) => ({
            ejercicio_id: b.ejercicio_id!,
            orden: idx,
            series: b.series,
            reps: b.reps,
            distancia_m: b.distancia_m,
            duracion_s: b.duracion_s,
            calidad: b.calidad,
            peso_kg: b.peso_kg,
            rpe: b.rpe,
            dolor_lumbar: b.dolor_lumbar,
          }));
          await crear.mutateAsync({
            // crypto.randomUUID requiere contexto seguro (https o localhost).
            // El dev server corre en localhost asi que funciona.
            id: crypto.randomUUID(),
            idempotency_key: crypto.randomUUID(),
            sesion_plan_id: planVinculado?.id ?? null,
            tipo_sesion_id: tipoSesionId,
            duracion_min: duracionMin,
            rpe,
            nota: nota || null,
            bloques: bloquesPayload,
          });
          // Reset del form y colapsa: la tarea esta hecha, no hace falta
          // seguir ocupando la pantalla.
          setBloques([]);
          setNota("");
          setExpandido(false);
        }}
        className="mt-6 w-full bg-text-primary text-canvas rounded-pill py-3 text-[14px] font-semibold disabled:opacity-50"
      >
        {crear.isPending ? "Guardando..." : "Guardar sesion"}
      </button>
        </div>
      )}
    </BentoCard>
  );
}

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
