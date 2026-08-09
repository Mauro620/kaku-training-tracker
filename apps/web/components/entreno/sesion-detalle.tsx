"use client";

import { useState } from "react";
import { ChevronLeft, Copy, Plus, Trash2 } from "lucide-react";
import { BentoCard } from "@/components/ui/bento-card";
import {
  BLOQUE_VACIO,
  bloqueInvalido,
  BloqueBorradorCard,
  uid,
  type BloqueBorrador,
} from "@/components/entreno/bloque-editor";
import {
  useActualizarSesion,
  useDuplicarSesion,
  useEjercicios,
  useEliminarSesion,
  useSesion,
  useTiposSesion,
  type BloqueBorradorPayload,
  type Sesion,
} from "@/lib/api/hooks";

type Props = { sesionId: string; onCerrar: () => void };

function bloquesABorrador(sesion: Sesion): BloqueBorrador[] {
  return sesion.bloques.map((b) => ({
    localId: uid(),
    ejercicio_id: b.ejercicio_id,
    series: b.series,
    reps: b.reps,
    distancia_m: b.distancia_m !== null ? Number(b.distancia_m) : null,
    duracion_s: b.duracion_s,
    calidad: b.calidad,
    peso_kg: b.peso_kg !== null ? Number(b.peso_kg) : null,
    rpe: b.rpe,
    dolor_lumbar: b.dolor_lumbar,
  }));
}

/**
 * Detalle/edicion de una sesion, en pantalla completa (mismo patron que
 * el detalle de ciclo). Editar cabecera + bloques via el mismo editor que
 * crear (bloque-editor.tsx). Eliminar con confirmacion. Duplicar: pide
 * fecha destino y crea una sesion nueva con los mismos bloques.
 */
export function SesionDetalle({ sesionId, onCerrar }: Props) {
  const consulta = useSesion(sesionId);

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-canvas">
      <div className="mx-auto max-w-3xl px-5 pt-[calc(env(safe-area-inset-top)+2rem)]">
        <button
          type="button"
          onClick={onCerrar}
          className="mb-4 flex items-center gap-1 text-[13px] text-text-secondary"
        >
          <ChevronLeft size={16} /> Volver
        </button>

        {consulta.isLoading && <div className="h-40" />}
        {consulta.data && (
          <SesionDetalleForm sesion={consulta.data} onCerrar={onCerrar} />
        )}
      </div>
    </div>
  );
}

function SesionDetalleForm({ sesion, onCerrar }: { sesion: Sesion; onCerrar: () => void }) {
  const tipos = useTiposSesion();
  const ejercicios = useEjercicios();
  const actualizar = useActualizarSesion(sesion.id);
  const eliminar = useEliminarSesion();
  const duplicar = useDuplicarSesion();

  const [fecha, setFecha] = useState(sesion.fecha);
  const [tipoSesionId, setTipoSesionId] = useState(sesion.tipo_sesion_id);
  const [duracionMin, setDuracionMin] = useState(sesion.duracion_min);
  const [rpe, setRpe] = useState(sesion.rpe);
  const [nota, setNota] = useState(sesion.nota ?? "");
  const [bloques, setBloques] = useState<BloqueBorrador[]>(() => bloquesABorrador(sesion));

  const [confirmandoEliminar, setConfirmandoEliminar] = useState(false);
  const [duplicando, setDuplicando] = useState(false);
  const [fechaDuplicado, setFechaDuplicado] = useState(sesion.fecha);

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

  function armarBloquesPayload(): BloqueBorradorPayload[] {
    return bloques.map((b, idx) => ({
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
  }

  const puedeGuardar = !bloques.some(bloqueInvalido);

  return (
    <div className="flex flex-col gap-4 pb-32">
      <BentoCard>
        <header className="mb-4 flex items-center justify-between">
          <p className="text-[11px] font-normal tracking-widest uppercase text-text-secondary">
            Editar sesion
          </p>
          <p className="text-[20px] font-bold tabular text-text-primary">{sesion.carga_srpe}</p>
        </header>

        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-widest text-text-secondary">
              Fecha
            </span>
            <input
              type="date"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              className="bg-surface-secondary rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-widest text-text-secondary">
              Tipo
            </span>
            <select
              value={tipoSesionId}
              onChange={(e) => setTipoSesionId(Number(e.target.value))}
              className="bg-surface-secondary rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
            >
              {tipos.data?.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nombre}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-widest text-text-secondary">
              Duracion (min)
            </span>
            <input
              type="number"
              min={1}
              value={duracionMin}
              onChange={(e) =>
                setDuracionMin(e.target.value === "" ? 0 : Number(e.target.value))
              }
              className="bg-surface-secondary rounded-pill px-4 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-widest text-text-secondary">RPE</span>
            <input
              type="number"
              min={1}
              max={10}
              value={rpe}
              onChange={(e) => setRpe(Number(e.target.value))}
              className="bg-surface-secondary rounded-pill px-4 py-2 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
            />
          </label>
        </div>

        <label className="mt-3 flex flex-col gap-1">
          <span className="text-[11px] uppercase tracking-widest text-text-secondary">Nota</span>
          <input
            type="text"
            value={nota}
            onChange={(e) => setNota(e.target.value)}
            placeholder="opcional"
            className="bg-surface-secondary rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
          />
        </label>

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
          disabled={!puedeGuardar || actualizar.isPending}
          onClick={async () => {
            await actualizar.mutateAsync({
              fecha,
              tipo_sesion_id: tipoSesionId,
              duracion_min: duracionMin,
              rpe,
              nota: nota || null,
              bloques: armarBloquesPayload(),
            });
            onCerrar();
          }}
          className="mt-6 w-full bg-text-primary text-canvas rounded-pill py-3 text-[14px] font-semibold disabled:opacity-50"
        >
          {actualizar.isPending ? "Guardando..." : "Guardar cambios"}
        </button>
      </BentoCard>

      <BentoCard>
        {duplicando ? (
          <div className="flex flex-col gap-3">
            <p className="text-[13px] text-text-secondary">Duplicar a que fecha?</p>
            <input
              type="date"
              value={fechaDuplicado}
              onChange={(e) => setFechaDuplicado(e.target.value)}
              className="bg-surface-secondary rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setDuplicando(false)}
                className="flex-1 rounded-pill bg-surface-secondary py-2.5 text-[13px] font-medium text-text-primary"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={!puedeGuardar || duplicar.isPending}
                onClick={async () => {
                  await duplicar.mutateAsync({
                    id: crypto.randomUUID(),
                    idempotency_key: crypto.randomUUID(),
                    fecha: fechaDuplicado,
                    tipo_sesion_id: tipoSesionId,
                    duracion_min: duracionMin,
                    rpe,
                    nota: nota || null,
                    bloques: armarBloquesPayload(),
                  });
                  setDuplicando(false);
                  onCerrar();
                }}
                className="flex-1 rounded-pill bg-text-primary py-2.5 text-[13px] font-semibold text-canvas disabled:opacity-50"
              >
                {duplicar.isPending ? "Creando..." : "Crear copia"}
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setDuplicando(true)}
            className="flex w-full items-center justify-center gap-2 rounded-pill bg-surface-secondary py-2.5 text-[13px] font-medium text-text-primary"
          >
            <Copy size={14} /> Duplicar sesion
          </button>
        )}
      </BentoCard>

      <BentoCard>
        {confirmandoEliminar ? (
          <div className="flex flex-col gap-3">
            <p className="text-[13px] text-text-secondary">
              Eliminar esta sesion y sus bloques? No se puede deshacer.
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setConfirmandoEliminar(false)}
                className="flex-1 rounded-pill bg-surface-secondary py-2.5 text-[13px] font-medium text-text-primary"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={eliminar.isPending}
                onClick={async () => {
                  await eliminar.mutateAsync(sesion.id);
                  onCerrar();
                }}
                className="flex-1 rounded-pill bg-state-danger py-2.5 text-[13px] font-semibold text-canvas disabled:opacity-50"
              >
                {eliminar.isPending ? "Eliminando..." : "Eliminar"}
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setConfirmandoEliminar(true)}
            className="flex w-full items-center justify-center gap-2 rounded-pill bg-surface-secondary py-2.5 text-[13px] font-medium text-state-danger"
          >
            <Trash2 size={14} /> Eliminar sesion
          </button>
        )}
      </BentoCard>
    </div>
  );
}
