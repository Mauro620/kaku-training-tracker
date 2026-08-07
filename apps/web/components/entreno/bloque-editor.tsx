"use client";

import { useState } from "react";
import { Copy, Plus, Search, Trash2 } from "lucide-react";
import {
  useCrearEjercicio,
  type Ejercicio,
  type TipoMedicion,
} from "@/lib/api/hooks";

// Editor de bloque compartido entre crear sesion (SesionForm) y editar
// sesion (SesionDetalle): mismo modelo de borrador, misma UI. Que campos
// pide cada bloque lo decide el tipo_medicion del ejercicio elegido
// (REGLAS_NEGOCIO §15), no el tipo de sesion.

export type BloqueBorrador = {
  // Identificador local para key de React. No se manda al backend.
  localId: number;
  ejercicio_id: number | null;
  series: number | null;
  reps: number | null;
  distancia_m: number | null;
  duracion_s: number | null;
  calidad: number | null;
  peso_kg: number | null;
  rpe: number | null;
  dolor_lumbar: boolean;
};

export const BLOQUE_VACIO: Omit<BloqueBorrador, "localId"> = {
  ejercicio_id: null,
  series: null,
  reps: null,
  distancia_m: null,
  duracion_s: null,
  calidad: null,
  peso_kg: null,
  rpe: null,
  dolor_lumbar: false,
};

export function uid(): number {
  return Math.floor(Math.random() * 1e9);
}

const NOMBRE_MEDICION: Record<TipoMedicion, string> = {
  carga: "Carga (series/reps/kg)",
  distancia: "Distancia (reps/metros)",
  tiempo: "Tiempo (segundos)",
  tecnica: "Tecnica (reps o segundos + calidad)",
};

export function bloqueInvalido(b: BloqueBorrador): boolean {
  if (b.ejercicio_id === null) return true;
  const numValido = (v: number | null, min: number) =>
    v === null || (Number.isFinite(v) && v > min);
  if (!numValido(b.series, 0)) return true;
  if (!numValido(b.reps, 0)) return true;
  if (!numValido(b.distancia_m, 0)) return true;
  if (!numValido(b.duracion_s, 0)) return true;
  if (b.calidad !== null && (!Number.isFinite(b.calidad) || b.calidad < 1 || b.calidad > 5)) {
    return true;
  }
  if (b.peso_kg !== null && (!Number.isFinite(b.peso_kg) || b.peso_kg < 0)) return true;
  if (b.rpe !== null && (!Number.isFinite(b.rpe) || b.rpe < 1 || b.rpe > 10)) return true;
  return false;
}

export function BloqueBorradorCard({
  bloque,
  orden,
  ejercicios,
  onChange,
  onEliminar,
  onDuplicar,
}: {
  bloque: BloqueBorrador;
  orden: number;
  ejercicios: Ejercicio[];
  onChange: (c: Partial<BloqueBorrador>) => void;
  onEliminar: () => void;
  onDuplicar: () => void;
}) {
  const ejercicio = ejercicios.find((e) => e.id === bloque.ejercicio_id) ?? null;

  return (
    <div className="rounded-bento border border-border-subtle bg-surface-secondary p-3">
      <div className="flex items-center justify-between">
        <p className="text-[11px] uppercase tracking-widest text-text-secondary">
          Bloque {orden}
        </p>
        <div className="flex items-center gap-1">
          {bloque.ejercicio_id !== null && (
            <button
              type="button"
              onClick={onDuplicar}
              aria-label="Duplicar bloque"
              className="p-1 text-text-secondary"
            >
              <Copy size={14} />
            </button>
          )}
          <button
            type="button"
            onClick={onEliminar}
            aria-label="Eliminar bloque"
            className="p-1 text-text-secondary"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <div className="mt-2">
        <EjercicioPicker
          ejercicioId={bloque.ejercicio_id}
          ejercicios={ejercicios}
          onElegir={(id) => onChange({ ejercicio_id: id })}
        />
      </div>

      {ejercicio && (
        <>
          <CamposBloque bloque={bloque} tipoMedicion={ejercicio.tipo_medicion} onChange={onChange} />

          <label className="mt-2 flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={bloque.dolor_lumbar}
              onChange={(e) => onChange({ dolor_lumbar: e.target.checked })}
              className="h-4 w-4 accent-text-primary"
            />
            <span className="text-[12px] text-text-secondary">Dolor lumbar</span>
          </label>
        </>
      )}
    </div>
  );
}

function CampoNumero({
  etiqueta,
  valor,
  min,
  max,
  step,
  onChange,
}: {
  etiqueta: string;
  valor: number | null;
  min?: number;
  max?: number;
  step?: number;
  onChange: (v: number | null) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-widest text-text-secondary">
        {etiqueta}
      </span>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={valor ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
        className="bg-canvas rounded-pill px-3 py-1.5 text-center text-[14px] font-bold tabular text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
      />
    </label>
  );
}

function CamposBloque({
  bloque,
  tipoMedicion,
  onChange,
}: {
  bloque: BloqueBorrador;
  tipoMedicion: TipoMedicion;
  onChange: (c: Partial<BloqueBorrador>) => void;
}) {
  return (
    <div className="mt-2 grid grid-cols-4 gap-2">
      {tipoMedicion === "carga" && (
        <>
          <CampoNumero
            etiqueta="Sets"
            valor={bloque.series}
            min={1}
            onChange={(v) => onChange({ series: v })}
          />
          <CampoNumero
            etiqueta="Reps"
            valor={bloque.reps}
            min={1}
            onChange={(v) => onChange({ reps: v })}
          />
          <CampoNumero
            etiqueta="Kg"
            valor={bloque.peso_kg}
            min={0}
            step={0.5}
            onChange={(v) => onChange({ peso_kg: v })}
          />
        </>
      )}
      {tipoMedicion === "distancia" && (
        <>
          <CampoNumero
            etiqueta="Reps"
            valor={bloque.reps}
            min={1}
            onChange={(v) => onChange({ reps: v })}
          />
          <CampoNumero
            etiqueta="Metros"
            valor={bloque.distancia_m}
            min={0}
            step={0.5}
            onChange={(v) => onChange({ distancia_m: v })}
          />
        </>
      )}
      {tipoMedicion === "tiempo" && (
        <CampoNumero
          etiqueta="Segundos"
          valor={bloque.duracion_s}
          min={1}
          onChange={(v) => onChange({ duracion_s: v })}
        />
      )}
      {tipoMedicion === "tecnica" && (
        <>
          <CampoNumero
            etiqueta="Reps"
            valor={bloque.reps}
            min={1}
            onChange={(v) => onChange({ reps: v })}
          />
          <CampoNumero
            etiqueta="Segundos"
            valor={bloque.duracion_s}
            min={1}
            onChange={(v) => onChange({ duracion_s: v })}
          />
          <CampoNumero
            etiqueta="Calidad"
            valor={bloque.calidad}
            min={1}
            max={5}
            onChange={(v) => onChange({ calidad: v })}
          />
        </>
      )}
      <CampoNumero
        etiqueta="RPE"
        valor={bloque.rpe}
        min={1}
        max={10}
        onChange={(v) => onChange({ rpe: v })}
      />
    </div>
  );
}

// Buscador de ejercicio con creacion inline: escribir filtra el catalogo,
// y si no matchea nada ofrece crear uno nuevo ahi mismo (nombre + tipo de
// medicion), sin salir del form de la sesion.
export function EjercicioPicker({
  ejercicioId,
  ejercicios,
  onElegir,
}: {
  ejercicioId: number | null;
  ejercicios: Ejercicio[];
  onElegir: (id: number) => void;
}) {
  const [abierto, setAbierto] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const [tipoNuevo, setTipoNuevo] = useState<TipoMedicion>("carga");
  const crear = useCrearEjercicio();

  const elegido = ejercicios.find((e) => e.id === ejercicioId) ?? null;
  const termino = busqueda.trim().toLowerCase();
  const coincidencias = (
    termino ? ejercicios.filter((e) => e.nombre.toLowerCase().includes(termino)) : ejercicios
  ).slice(0, 8);
  const sinMatchExacto =
    termino.length > 1 && !ejercicios.some((e) => e.nombre.toLowerCase() === termino);

  if (!abierto) {
    return (
      <button
        type="button"
        onClick={() => {
          setAbierto(true);
          setBusqueda("");
        }}
        className="flex min-h-[40px] w-full items-center justify-between rounded-pill bg-canvas px-4 text-[14px] text-text-primary"
      >
        {elegido?.nombre ?? "Elegir ejercicio…"}
        <Search size={14} className="text-text-secondary" />
      </button>
    );
  }

  return (
    <div className="rounded-bento border border-border-subtle bg-canvas p-2">
      <input
        autoFocus
        type="text"
        value={busqueda}
        onChange={(e) => setBusqueda(e.target.value)}
        placeholder="Buscar ejercicio…"
        className="w-full bg-surface-secondary rounded-pill px-4 py-2 text-[14px] text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-state-focus"
      />

      <ul className="mt-2 flex max-h-48 flex-col gap-0.5 overflow-y-auto">
        {coincidencias.map((e) => (
          <li key={e.id}>
            <button
              type="button"
              onClick={() => {
                onElegir(e.id);
                setAbierto(false);
              }}
              className="flex w-full items-center justify-between rounded-pill px-3 py-2 text-left text-[13px] text-text-primary hover:bg-surface-secondary"
            >
              {e.nombre}
              <span className="text-[10px] uppercase tracking-widest text-text-secondary">
                {e.tipo_medicion}
              </span>
            </button>
          </li>
        ))}
        {coincidencias.length === 0 && (
          <li className="px-3 py-2 text-[13px] text-text-secondary">Sin resultados.</li>
        )}
      </ul>

      {sinMatchExacto && (
        <div className="mt-2 flex flex-col gap-2 border-t border-border-subtle pt-2">
          <select
            value={tipoNuevo}
            onChange={(e) => setTipoNuevo(e.target.value as TipoMedicion)}
            className="w-full bg-surface-secondary rounded-pill px-4 py-2 text-[13px] text-text-primary outline-none"
          >
            {(Object.keys(NOMBRE_MEDICION) as TipoMedicion[]).map((tm) => (
              <option key={tm} value={tm}>
                {NOMBRE_MEDICION[tm]}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={crear.isPending}
            onClick={async () => {
              const nuevo = await crear.mutateAsync({
                nombre: busqueda.trim(),
                tipo_medicion: tipoNuevo,
              });
              onElegir(nuevo.id);
              setAbierto(false);
            }}
            className="flex items-center justify-center gap-1 rounded-pill bg-text-primary px-4 py-2 text-[13px] font-semibold text-canvas disabled:opacity-50"
          >
            <Plus size={14} />
            {crear.isPending ? "Creando…" : `Crear "${busqueda.trim()}"`}
          </button>
        </div>
      )}
    </div>
  );
}
